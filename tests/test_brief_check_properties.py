"""Hypothesis properties for cash-day vs nonempty picks (formal check).

Property: any brief with balanced fences, an action containing 「今天不做」,
and a nonempty ```picks data row must be rejected by check_brief_text with a
message that mentions 「今天不做」.
"""
from __future__ import annotations

from hypothesis import given, settings, strategies as st

from pipeline.brief_check_demo import check_brief_text, is_no_trade_day, picks_nonempty


SAFE_LINE = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters=" _-|:./"),
    min_size=1,
    max_size=40,
).filter(lambda s: "```" not in s and "今天不做" not in s)


def _action_block(body: str) -> str:
    return f"```action\n{body}\n```\n"


def _picks_block(rows: list[str]) -> str:
    return "```picks\n" + "\n".join(rows) + "\n```\n"


@given(
    extra_actions=st.lists(
        SAFE_LINE.map(lambda s: f"观察: {s}"),
        max_size=2,
    ),
    pick_rows=st.lists(SAFE_LINE, min_size=1, max_size=3),
    preface=st.lists(SAFE_LINE, max_size=2),
)
@settings(max_examples=200, deadline=None)
def test_cash_day_with_nonempty_picks_always_rejected(extra_actions, pick_rows, preface):
    parts = [f"# {p}" for p in preface]
    parts.append(_action_block("动作: 今天不做"))
    for body in extra_actions:
        parts.append(_action_block(body))
    parts.append(_picks_block(pick_rows))
    text = "\n".join(parts)
    assert is_no_trade_day(text)
    assert picks_nonempty(text)
    ok, msg = check_brief_text(text)
    assert ok is False
    assert "今天不做" in msg


@given(
    note=SAFE_LINE,
    preface=st.lists(SAFE_LINE, max_size=2),
)
@settings(max_examples=100, deadline=None)
def test_cash_day_without_picks_accepted(note, preface):
    parts = [f"# {p}" for p in preface]
    parts.append(_action_block(f"动作: 今天不做\n理由: {note}"))
    text = "\n".join(parts)
    ok, msg = check_brief_text(text)
    assert ok is True
    assert msg == "OK"


@given(pick_rows=st.lists(SAFE_LINE, min_size=1, max_size=3))
@settings(max_examples=50, deadline=None)
def test_comment_only_picks_do_not_count_as_nonempty(pick_rows):
    # If every "row" is a # comment, picks_nonempty is False — cash day may pass.
    comments = [f"# {r}" for r in pick_rows]
    text = _action_block("动作: 今天不做") + _picks_block(comments)
    assert is_no_trade_day(text)
    assert picks_nonempty(text) is False
    ok, msg = check_brief_text(text)
    assert ok is True
    assert msg == "OK"
