"""Hypothesis properties for pipeline.x_signal_demo (formal check).

Promises grounded in text_weight / is_low_effort / has_new_content /
is_first_hand / is_bystander_original / keyword_hit / map_tickers /
filter_market / summarize / render / MARKETS:
1. text_weight = #latin + CJK_WEIGHT * #CJK (emoji/punct contribute 0).
2. is_low_effort iff text_weight < min_chars.
3. has_new_content only for type in {original, quote} and not low-effort.
4. is_first_hand iff has_new_content and is_primary_source is True.
5. is_bystander_original iff type==original and has_new_content and
   is_primary_source is not True; never co-true with is_first_hand.
6. keyword_hit: English uses \\b word boundary; CJK keywords use substring.
7. map_tickers returns sorted tickers whose words hit the text.
8. filter_market / summarize(unknown market) → ValueError.
9. summarize: snr = round(fh/total, 3) or 0.0; consensus_noise =
   total>0 and snr < threshold and total_engagement >= high_engagement;
   counters add only for mapped tickers.
10. render always includes NOTICE; empty summary → 「这个市场没有示例标的」.
11. MARKETS == markets.available().
"""
from __future__ import annotations

import math
import re

import pytest
from hypothesis import given, settings, strategies as st

import markets
from pipeline.x_signal_demo import (
    CJK_WEIGHT,
    DEFAULT_HIGH_ENGAGEMENT,
    DEFAULT_MIN_CHARS,
    DEFAULT_SNR_THRESHOLD,
    MARKETS,
    NOTICE,
    VALID_TYPES,
    filter_market,
    has_new_content,
    is_bystander_original,
    is_first_hand,
    is_low_effort,
    keyword_hit,
    map_tickers,
    render,
    summarize,
    text_weight,
)

KNOWN_MARKETS = list(markets.available())
assert KNOWN_MARKETS
assert tuple(KNOWN_MARKETS) == MARKETS

latin_chars = st.sampled_from(list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"))
cjk_chars = st.sampled_from(list("链上电池火箭发射充电工厂跨链利好项目活跃地址产量翻倍"))
junk_chars = st.sampled_from(list("🔥🚀!?.…，。、 \t\n"))

post_types = st.sampled_from(sorted(VALID_TYPES))
min_chars_vals = st.integers(min_value=1, max_value=40)
likes_vals = st.integers(min_value=0, max_value=5000)


@st.composite
def composed_text(draw):
    """Build text with known latin / CJK / junk counts (no filtering)."""
    n_lat = draw(st.integers(min_value=0, max_value=20))
    n_cjk = draw(st.integers(min_value=0, max_value=12))
    n_junk = draw(st.integers(min_value=0, max_value=8))
    parts = (
        [draw(latin_chars) for _ in range(n_lat)]
        + [draw(cjk_chars) for _ in range(n_cjk)]
        + [draw(junk_chars) for _ in range(n_junk)]
    )
    # Shuffle by drawing a permutation of indices via sorted keys.
    order = draw(st.permutations(range(len(parts)))) if parts else []
    text = "".join(parts[i] for i in order)
    return text, n_lat, n_cjk


@st.composite
def post_dict(draw, force_type=None, force_primary=None, min_weight=None, max_weight=None):
    """Construct a post whose weight / type / primary are under control."""
    ptype = force_type if force_type is not None else draw(post_types)
    if force_primary is None:
        primary = draw(st.booleans())
    else:
        primary = force_primary

    if min_weight is None and max_weight is None:
        text, _, _ = draw(composed_text())
    else:
        # Construct by latin count so weight == n_lat (no CJK / junk).
        lo = 0 if min_weight is None else max(0, int(min_weight))
        hi = 40 if max_weight is None else max(lo, int(max_weight))
        n_lat = draw(st.integers(min_value=lo, max_value=hi))
        text = "".join(draw(latin_chars) for _ in range(n_lat))

    return {
        "id": f"p{draw(st.integers(min_value=0, max_value=10_000))}",
        "author": f"demo_user_{draw(st.integers(min_value=1, max_value=99))}",
        "type": ptype,
        "text": text,
        "ts": "2026-01-05T10:00:00Z",
        "likes": draw(likes_vals),
        "is_primary_source": primary,
    }


@given(data=composed_text())
@settings(max_examples=300, deadline=None)
def test_text_weight_counts_latin_and_cjk(data) -> None:
    text, n_lat, n_cjk = data
    assert text_weight(text) == n_lat + CJK_WEIGHT * n_cjk
    assert CJK_WEIGHT == 3


@given(text=st.sampled_from(["", "🔥🔥", "!!!", "🚀", "….…", "  \t"]))
@settings(max_examples=20, deadline=None)
def test_text_weight_junk_only_is_zero(text: str) -> None:
    assert text_weight(text) == 0


@given(data=composed_text(), min_chars=min_chars_vals)
@settings(max_examples=250, deadline=None)
def test_is_low_effort_matches_weight_gate(data, min_chars: int) -> None:
    text, n_lat, n_cjk = data
    w = n_lat + CJK_WEIGHT * n_cjk
    assert is_low_effort(text, min_chars) is (w < min_chars)
    assert is_low_effort(text, min_chars) is (text_weight(text) < min_chars)


@given(data=st.data(), min_chars=min_chars_vals)
@settings(max_examples=200, deadline=None)
def test_has_new_content_only_original_or_quote(data, min_chars: int) -> None:
    # Enough weight to clear the low-effort gate.
    post = data.draw(post_dict(min_weight=min_chars, max_weight=min_chars + 20))
    expected = post["type"] in ("original", "quote") and not is_low_effort(
        post["text"], min_chars
    )
    assert has_new_content(post, min_chars) is expected


@given(data=st.data(), min_chars=min_chars_vals)
@settings(max_examples=200, deadline=None)
def test_has_new_content_false_when_low_effort(data, min_chars: int) -> None:
    # Weight strictly below min_chars → never has_new_content.
    hi = max(0, min_chars - 1)
    post = data.draw(post_dict(min_weight=0, max_weight=hi))
    assert is_low_effort(post["text"], min_chars)
    assert has_new_content(post, min_chars) is False


@given(data=st.data(), min_chars=min_chars_vals)
@settings(max_examples=250, deadline=None)
def test_first_hand_requires_primary_true(data, min_chars: int) -> None:
    post = data.draw(
        post_dict(
            force_type=data.draw(st.sampled_from(["original", "quote"])),
            force_primary=True,
            min_weight=min_chars,
            max_weight=min_chars + 20,
        )
    )
    assert is_first_hand(post, min_chars) is True
    assert is_bystander_original(post, min_chars) is False

    post_false = dict(post)
    post_false["is_primary_source"] = False
    assert is_first_hand(post_false, min_chars) is False


@given(data=st.data(), min_chars=min_chars_vals)
@settings(max_examples=200, deadline=None)
def test_bystander_original_partition(data, min_chars: int) -> None:
    post = data.draw(
        post_dict(
            force_type="original",
            force_primary=False,
            min_weight=min_chars,
            max_weight=min_chars + 20,
        )
    )
    assert is_bystander_original(post, min_chars) is True
    assert is_first_hand(post, min_chars) is False


@given(data=st.data(), min_chars=min_chars_vals)
@settings(max_examples=250, deadline=None)
def test_first_hand_and_bystander_mutually_exclusive(data, min_chars: int) -> None:
    post = data.draw(post_dict())
    fh = is_first_hand(post, min_chars)
    by = is_bystander_original(post, min_chars)
    assert not (fh and by)
    # Reply / repost never first-hand or bystander-original.
    if post["type"] in ("reply", "repost"):
        assert fh is False and by is False


@given(
    keyword=st.sampled_from(["rocket", "launch", "battery", "chain", "orbit"]),
    suffix=st.sampled_from(["", "!", ".", "?", " flew", " news"]),
)
@settings(max_examples=100, deadline=None)
def test_keyword_hit_english_word_boundary(keyword: str, suffix: str) -> None:
    text = f"the {keyword}{suffix}".lower()
    assert keyword_hit(keyword, text) is True
    # Prefix extension must NOT match (rocketry ↛ rocket).
    assert keyword_hit(keyword, f"{keyword}ry club".lower()) is False


@given(
    keyword=st.sampled_from(["电池", "火箭", "链上", "跨链", "充电"]),
    prefix=st.sampled_from(["", "固态", "新", "示例"]),
    suffix=st.sampled_from(["", "产线", "项目", "翻倍"]),
)
@settings(max_examples=100, deadline=None)
def test_keyword_hit_cjk_substring(keyword: str, prefix: str, suffix: str) -> None:
    text = f"{prefix}{keyword}{suffix}"
    assert keyword_hit(keyword, text) is True
    assert keyword_hit(keyword, "无关文本abc") is False


@given(data=st.data())
@settings(max_examples=150, deadline=None)
def test_map_tickers_sorted_unique_hits(data) -> None:
    # Two DEMO tickers with disjoint English keywords.
    kw = {
        "DEMO-X": {"market": "us", "words": ["rocket", "launch"]},
        "DEMO-Y": {"market": "cn_a", "words": ["battery", "factory"]},
    }
    which = data.draw(st.sampled_from(["x", "y", "both", "none"]))
    if which == "x":
        text = "the rocket launch window"
        assert map_tickers(text, kw) == ["DEMO-X"]
    elif which == "y":
        text = "battery factory output"
        assert map_tickers(text, kw) == ["DEMO-Y"]
    elif which == "both":
        text = "rocket and battery factory"
        assert map_tickers(text, kw) == ["DEMO-X", "DEMO-Y"]
    else:
        text = "nothing related here"
        assert map_tickers(text, kw) == []


@given(market=st.sampled_from(["NASDAQ", "A股", "CN_A", "btc", "", "crypto_x", "US"]))
@settings(max_examples=40, deadline=None)
def test_filter_market_unknown_raises(market: str) -> None:
    kw = {"DEMO-X": {"market": "us", "words": ["rocket"]}}
    with pytest.raises(ValueError):
        filter_market(kw, market)
    with pytest.raises(ValueError):
        summarize([], kw, market=market)


@given(market=st.sampled_from(KNOWN_MARKETS))
@settings(max_examples=40, deadline=None)
def test_filter_market_keeps_only_matching(market: str) -> None:
    kw = {
        "DEMO-X": {"market": "us", "words": ["rocket"]},
        "DEMO-Y": {"market": "cn_a", "words": ["battery"]},
        "DEMO-Z": {"market": "crypto", "words": ["chain"]},
    }
    out = filter_market(kw, market)
    assert all(v["market"] == market for v in out.values())
    assert set(out) == {t for t, v in kw.items() if v["market"] == market}


@given(data=st.data())
@settings(max_examples=120, deadline=None)
def test_summarize_snr_and_consensus_noise(data) -> None:
    snr_threshold = data.draw(
        st.floats(min_value=0.05, max_value=0.9, allow_nan=False, allow_infinity=False)
    )
    high_engagement = data.draw(st.integers(min_value=10, max_value=2000))
    n_posts = data.draw(st.integers(min_value=0, max_value=12))
    posts = [data.draw(post_dict()) for _ in range(n_posts)]
    # Ensure every post mentions the ticker so mapping is deterministic.
    for p in posts:
        p["text"] = (p["text"] + " rocket").strip()
    kw = {"DEMO-X": {"market": "us", "words": ["rocket"]}}

    out = summarize(
        posts,
        kw,
        min_chars=DEFAULT_MIN_CHARS,
        snr_threshold=snr_threshold,
        high_engagement=high_engagement,
    )
    r = out["DEMO-X"]
    assert r["total_posts"] == n_posts
    assert r["total_engagement"] == sum(int(p["likes"]) for p in posts)
    fh = sum(1 for p in posts if is_first_hand(p, DEFAULT_MIN_CHARS))
    by = sum(1 for p in posts if is_bystander_original(p, DEFAULT_MIN_CHARS))
    assert r["first_hand_posts"] == fh
    assert r["bystander_original"] == by
    assert r["engagement"] == sum(
        int(p["likes"]) for p in posts if is_first_hand(p, DEFAULT_MIN_CHARS)
    )
    if n_posts == 0:
        assert r["snr"] == 0.0
        assert r["consensus_noise"] is False
    else:
        assert r["snr"] == round(fh / n_posts, 3)
        expected_noise = (
            r["snr"] < snr_threshold and r["total_engagement"] >= high_engagement
        )
        assert r["consensus_noise"] is expected_noise


@given(data=st.data())
@settings(max_examples=80, deadline=None)
def test_render_always_carries_notice(data) -> None:
    empty = data.draw(st.booleans())
    if empty:
        text = render({})
        assert NOTICE in text
        assert "这个市场没有示例标的" in text
    else:
        kw = {"DEMO-X": {"market": "us", "words": ["rocket"]}}
        posts = [
            {
                "type": "original",
                "text": "rocket launch window confirmed today",
                "likes": 10,
                "is_primary_source": True,
            }
        ]
        text = render(summarize(posts, kw))
        assert NOTICE in text
        assert "信号：DEMO-X" in text


def test_markets_tuple_matches_package() -> None:
    assert MARKETS == tuple(markets.available())
    assert DEFAULT_MIN_CHARS == 10
    assert DEFAULT_SNR_THRESHOLD == 0.4
    assert DEFAULT_HIGH_ENGAGEMENT == 500
    assert math.isfinite(CJK_WEIGHT) and CJK_WEIGHT == 3
