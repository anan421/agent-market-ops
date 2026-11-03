"""Hypothesis properties for pipeline.reconcile_demo (formal check).

Promises grounded in sample_summary / render_html:
1. sample_summary is a cash-day zero-diff scaffold (pnl 0, trades 0, hit 0/0).
2. render_html matches the summary: date, headline, accounts, trades, disclaimer.
3. Hit-rate line matches correct/judgable (or n/a when missing); note is escaped.
4. User-controlled strings are HTML-escaped (no raw <script> / bare & injection).
"""
from __future__ import annotations

import html
import re

from hypothesis import given, settings, strategies as st

from pipeline.reconcile_demo import DISCLAIMER, render_html, sample_summary

# YYYY-MM-DD-shaped dates (renderer does not parse calendar validity).
dates = st.from_regex(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", fullmatch=True)

# Finite floats that format cleanly with :+0.2f (exclude nan/inf).
pnls = st.floats(
    min_value=-1e6,
    max_value=1e6,
    allow_nan=False,
    allow_infinity=False,
)

# Short unicode text including HTML metacharacters.
texty = st.text(
    alphabet=st.characters(
        whitelist_categories=("L", "N", "P", "Z"),
        whitelist_characters="<>&\"'/今天不做",
    ),
    min_size=0,
    max_size=40,
)

accounts = st.lists(
    st.fixed_dictionaries(
        {
            "name": texty,
            "pnl_pct": pnls,
            "status": texty,
        }
    ),
    min_size=0,
    max_size=5,
)

hit_rates = st.one_of(
    st.none(),
    st.just({}),
    st.fixed_dictionaries(
        {
            "correct": st.integers(min_value=0, max_value=10_000),
            "judgable": st.integers(min_value=0, max_value=10_000),
            "note": texty,
        }
    ),
)

summaries = st.fixed_dictionaries(
    {
        "date": dates,
        "headline": texty,
        "accounts": accounts,
        "trades": st.integers(min_value=0, max_value=10_000),
        "hit_rate": hit_rates,
        "disclaimer": texty,
        "synthetic": st.booleans(),
    }
)

meta = st.sampled_from(["<", ">", "&", '"', "'"])
chunk = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters=" _-"),
    min_size=0,
    max_size=8,
)
# Always embed at least one HTML metacharacter (no filter health-check).
nasty = st.builds(lambda a, m, b: a + m + b, chunk, meta, chunk)


@given(date=dates)
@settings(max_examples=200, deadline=None)
def test_sample_summary_date_and_cash_day_zero_diff(date: str) -> None:
    """Cash-day scaffold: date matches; every account pnl diff from flat is 0; trades 0."""
    s = sample_summary(date)
    assert s["date"] == date
    assert date in s["headline"]
    assert s["trades"] == 0
    assert s["synthetic"] is True
    assert s["disclaimer"] == DISCLAIMER
    assert {a["name"] for a in s["accounts"]} == {"signal", "view"}
    for a in s["accounts"]:
        assert a["pnl_pct"] == 0.0
        assert "今天不做" in a["status"]
    hr = s["hit_rate"]
    assert hr["correct"] == 0
    assert hr["judgable"] == 0
    # zero-diff between the two paper accounts
    assert s["accounts"][0]["pnl_pct"] == s["accounts"][1]["pnl_pct"] == 0.0


@given(summary=summaries)
@settings(max_examples=300, deadline=None)
def test_render_html_matches_summary_fields(summary: dict) -> None:
    """Rendered HTML must match summary fields the demo actually prints."""
    doc = render_html(summary)
    assert f"<title>Reconcile {html.escape(summary['date'])}</title>" in doc
    assert html.escape(summary["headline"]) in doc
    assert f"trades: {summary['trades']}" in doc
    assert html.escape(summary["disclaimer"]) in doc
    for a in summary["accounts"]:
        assert f"<td>{html.escape(a['name'])}</td>" in doc
        assert f"<td>{a['pnl_pct']:+.2f}%</td>" in doc
        assert f"<td>{html.escape(a['status'])}</td>" in doc


@given(summary=summaries)
@settings(max_examples=300, deadline=None)
def test_hit_rate_line_matches_or_na(summary: dict) -> None:
    """Hit-rate line is correct/judgable from the dict, or n/a when absent/empty."""
    doc = render_html(summary)
    hr = summary.get("hit_rate") or {}
    if hr:
        expected = f"{hr.get('correct', 0)}/{hr.get('judgable', 0)}"
        assert expected in doc
        assert html.escape(str(hr.get("note", ""))) in doc
        assert "Hit-rate (demo): <strong>n/a</strong>" not in doc
    else:
        assert "Hit-rate (demo): <strong>n/a</strong>" in doc


@given(name=nasty, status=nasty, headline=nasty, note=nasty, disclaimer=nasty)
@settings(max_examples=150, deadline=None)
def test_render_escapes_user_strings(
    name: str, status: str, headline: str, note: str, disclaimer: str
) -> None:
    """Match must use escaped forms; raw markup metacharacters must not pass through."""
    summary = {
        "date": "2026-11-03",
        "headline": headline,
        "accounts": [{"name": name, "pnl_pct": 0.0, "status": status}],
        "trades": 0,
        "hit_rate": {"correct": 1, "judgable": 2, "note": note},
        "disclaimer": disclaimer,
        "synthetic": True,
    }
    doc = render_html(summary)
    assert html.escape(name) in doc
    assert html.escape(status) in doc
    assert html.escape(headline) in doc
    assert html.escape(note) in doc
    assert html.escape(disclaimer) in doc
    # Raw unescaped name must not appear as an HTML tag opener when name looks like a tag.
    if re.search(r"<[a-zA-Z!?/]", name):
        assert name not in doc


@given(date=dates)
@settings(max_examples=100, deadline=None)
def test_sample_then_render_roundtrip_markers(date: str) -> None:
    """sample_summary -> render_html keeps cash-day markers and disclaimer."""
    doc = render_html(sample_summary(date))
    assert f"Reconcile {date}" in doc
    assert f"Paper reconcile {date}" in doc
    assert "今天不做" in doc
    assert "Demo data only. Not investment advice" in doc
    assert "trades: 0" in doc
    assert "0/0" in doc
    assert "+0.00%" in doc
