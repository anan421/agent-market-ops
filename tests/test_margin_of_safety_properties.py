"""Hypothesis properties for pipeline.margin_of_safety_demo (formal check).

Promises grounded in normal_profit / too_hard / fair_value_band / verdict / cash_quality:
1. haircut outside (0, 1] → ValueError; in-range → min(ttm, last_q*4*haircut).
2. too_hard: non-positive annualised quarter or TTM → True; ratio > MAX_SWING → True;
   ratio ≤ MAX_SWING with both positive → False.
3. fair_value_band: invalid PE (not 0 < lo ≤ hi) → Chinese ValueError; shares ≤ 0 → 「股本」;
   when valued, lo ≤ hi and equals eps × pe with eps = normal_profit / shares.
4. verdict gates: price ≤ 0 → 「价格」; shares ≤ 0 → 「股本」; unknown market → 「未知市场」;
   no-cashflow market → 「没有现金流」.
5. too_hard pile: call == "too hard pile", band/premium/cash_quality are None, note matches NOTES.
6. valued call partition: price ≤ lo and cash_quality ≥ 0.5 → "margin of safety";
   else price ≤ hi → "fair, no margin"; else → "expensive" (cash_quality rounded matches).
"""
from __future__ import annotations

import math

import pytest
from hypothesis import assume, given, settings, strategies as st

import markets
from pipeline.margin_of_safety_demo import (
    MAX_SWING,
    NOTES,
    PE_BANDS,
    Company,
    cash_quality,
    fair_value_band,
    normal_profit,
    too_hard,
    verdict,
)

# Markets that pass _market() (known + has_cashflow + PE_BANDS entry).
CASHFLOW_PE_MARKETS = sorted(
    m
    for m in PE_BANDS
    if m in markets.available() and markets.load(m).get("has_cashflow")
)
NO_CASHFLOW_MARKETS = sorted(
    m for m in markets.available() if not markets.load(m).get("has_cashflow")
)
assert CASHFLOW_PE_MARKETS, "expected PE_BANDS cashflow markets"
assert NO_CASHFLOW_MARKETS, "expected no-cashflow markets for gate tests"

finite_pos = st.floats(min_value=1e-3, max_value=1e4, allow_nan=False, allow_infinity=False)
finite_nonneg = st.floats(min_value=0.0, max_value=1e4, allow_nan=False, allow_infinity=False)
# Profits large enough that annualised quarter / TTM ratios stay numerically stable.
profit_pos = st.floats(min_value=0.1, max_value=500.0, allow_nan=False, allow_infinity=False)
shares_pos = st.floats(min_value=0.1, max_value=1e5, allow_nan=False, allow_infinity=False)
price_pos = st.floats(min_value=1e-3, max_value=1e5, allow_nan=False, allow_infinity=False)
haircut_ok = st.floats(min_value=1e-6, max_value=1.0, allow_nan=False, allow_infinity=False)
haircut_bad = st.one_of(
    st.just(0.0),
    st.floats(min_value=-10.0, max_value=0.0, allow_nan=False, allow_infinity=False),
    st.floats(min_value=1.0 + 1e-6, max_value=10.0, allow_nan=False, allow_infinity=False),
)
pe_ok = st.floats(min_value=1e-3, max_value=80.0, allow_nan=False, allow_infinity=False)

cashflow_markets = st.sampled_from(CASHFLOW_PE_MARKETS)
no_cashflow_markets = st.sampled_from(NO_CASHFLOW_MARKETS)
unknown_markets = st.one_of(
    st.sampled_from(["CN_A", "nasdaq", "", "../demo", "DEMO", "btc", "A股", "crypto_x"]),
    st.text(
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
        min_size=1,
        max_size=12,
    ).filter(lambda s: s not in set(markets.available())),
)


def _company(
    *,
    price: float,
    shares: float,
    last_q: float,
    ttm: float,
    ocf: float,
    market: str = "demo",
    name: str = "H",
) -> Company:
    return Company(
        name=name,
        price=price,
        shares=shares,
        last_q_profit=last_q,
        ttm_profit=ttm,
        ocf_ttm=ocf,
        market=market,
    )


@given(
    last_q=profit_pos,
    ttm=profit_pos,
    shares=shares_pos,
    haircut=haircut_ok,
    ocf=finite_nonneg,
)
@settings(max_examples=300, deadline=None)
def test_normal_profit_is_min_of_ttm_and_haircut_annualised(
    last_q: float, ttm: float, shares: float, haircut: float, ocf: float
) -> None:
    c = _company(price=1.0, shares=shares, last_q=last_q, ttm=ttm, ocf=ocf)
    expected = min(ttm, last_q * 4 * haircut)
    assert normal_profit(c, haircut) == pytest.approx(expected)


@given(
    last_q=profit_pos,
    ttm=profit_pos,
    shares=shares_pos,
    haircut=haircut_bad,
    ocf=finite_nonneg,
)
@settings(max_examples=200, deadline=None)
def test_normal_profit_rejects_haircut_outside_unit_interval(
    last_q: float, ttm: float, shares: float, haircut: float, ocf: float
) -> None:
    c = _company(price=1.0, shares=shares, last_q=last_q, ttm=ttm, ocf=ocf)
    with pytest.raises(ValueError, match="haircut"):
        normal_profit(c, haircut)


@given(
    last_q=st.floats(min_value=-500.0, max_value=0.0, allow_nan=False, allow_infinity=False),
    ttm=st.floats(min_value=-500.0, max_value=500.0, allow_nan=False, allow_infinity=False),
    shares=shares_pos,
    ocf=finite_nonneg,
)
@settings(max_examples=200, deadline=None)
def test_too_hard_when_annualised_quarter_nonpositive(
    last_q: float, ttm: float, shares: float, ocf: float
) -> None:
    c = _company(price=1.0, shares=shares, last_q=last_q, ttm=ttm, ocf=ocf)
    assert too_hard(c) is True


@given(
    last_q=profit_pos,
    ttm=st.floats(min_value=-500.0, max_value=0.0, allow_nan=False, allow_infinity=False),
    shares=shares_pos,
    ocf=finite_nonneg,
)
@settings(max_examples=200, deadline=None)
def test_too_hard_when_ttm_nonpositive(
    last_q: float, ttm: float, shares: float, ocf: float
) -> None:
    c = _company(price=1.0, shares=shares, last_q=last_q, ttm=ttm, ocf=ocf)
    assert too_hard(c) is True


@given(
    base=profit_pos,
    factor=st.floats(
        min_value=MAX_SWING + 1e-6,
        max_value=MAX_SWING * 8,
        allow_nan=False,
        allow_infinity=False,
    ),
    direction=st.booleans(),
    shares=shares_pos,
    ocf=finite_nonneg,
)
@settings(max_examples=250, deadline=None)
def test_too_hard_when_swing_exceeds_max(
    base: float, factor: float, direction: bool, shares: float, ocf: float
) -> None:
    """max(a,t)/min(a,t) > MAX_SWING → too hard (both directions)."""
    if direction:
        annualised, ttm = base * factor, base
        last_q = annualised / 4
    else:
        annualised, ttm = base, base * factor
        last_q = annualised / 4
    c = _company(price=1.0, shares=shares, last_q=last_q, ttm=ttm, ocf=ocf)
    a, t = c.last_q_profit * 4, c.ttm_profit
    assume(a > 0 and t > 0)
    assume(max(a, t) / min(a, t) > MAX_SWING)
    assert too_hard(c) is True


@given(
    base=profit_pos,
    factor=st.floats(
        min_value=1.0,
        max_value=MAX_SWING,
        allow_nan=False,
        allow_infinity=False,
    ),
    direction=st.booleans(),
    shares=shares_pos,
    ocf=finite_nonneg,
)
@settings(max_examples=250, deadline=None)
def test_not_too_hard_when_swing_at_most_max(
    base: float, factor: float, direction: bool, shares: float, ocf: float
) -> None:
    if direction:
        annualised, ttm = base * factor, base
        last_q = annualised / 4
    else:
        annualised, ttm = base, base * factor
        last_q = annualised / 4
    c = _company(price=1.0, shares=shares, last_q=last_q, ttm=ttm, ocf=ocf)
    a, t = c.last_q_profit * 4, c.ttm_profit
    assume(a > 0 and t > 0)
    assume(max(a, t) / min(a, t) <= MAX_SWING)
    assert too_hard(c) is False


@given(
    base=profit_pos,
    factor=st.floats(min_value=1.0, max_value=MAX_SWING, allow_nan=False, allow_infinity=False),
    direction=st.booleans(),
    shares=shares_pos,
    ocf=finite_nonneg,
    pe_low=pe_ok,
    pe_high=pe_ok,
    market=cashflow_markets,
    haircut=haircut_ok,
)
@settings(max_examples=250, deadline=None)
def test_fair_value_band_ordered_and_matches_eps_times_pe(
    base: float,
    factor: float,
    direction: bool,
    shares: float,
    ocf: float,
    pe_low: float,
    pe_high: float,
    market: str,
    haircut: float,
) -> None:
    assume(pe_low <= pe_high)
    if direction:
        annualised, ttm = base * factor, base
    else:
        annualised, ttm = base, base * factor
    last_q = annualised / 4
    c = _company(price=1.0, shares=shares, last_q=last_q, ttm=ttm, ocf=ocf, market=market)
    assert not too_hard(c)
    lo, hi = fair_value_band(c, pe_low=pe_low, pe_high=pe_high, haircut=haircut)
    eps = normal_profit(c, haircut) / shares
    assert lo <= hi
    assert lo == pytest.approx(eps * pe_low)
    assert hi == pytest.approx(eps * pe_high)


@given(
    last_q=profit_pos,
    ttm=profit_pos,
    shares=shares_pos,
    ocf=finite_nonneg,
    pe_low=pe_ok,
    pe_high=pe_ok,
    market=cashflow_markets,
)
@settings(max_examples=150, deadline=None)
def test_fair_value_band_rejects_inverted_or_nonpositive_pe(
    last_q: float,
    ttm: float,
    shares: float,
    ocf: float,
    pe_low: float,
    pe_high: float,
    market: str,
) -> None:
    assume(not (0 < pe_low <= pe_high))
    c = _company(price=1.0, shares=shares, last_q=last_q, ttm=ttm, ocf=ocf, market=market)
    with pytest.raises(ValueError, match="PE 区间"):
        fair_value_band(c, pe_low=pe_low, pe_high=pe_high)


@given(
    last_q=profit_pos,
    ttm=profit_pos,
    shares=st.floats(min_value=-100.0, max_value=0.0, allow_nan=False, allow_infinity=False),
    ocf=finite_nonneg,
    market=cashflow_markets,
)
@settings(max_examples=150, deadline=None)
def test_fair_value_band_rejects_nonpositive_shares(
    last_q: float, ttm: float, shares: float, ocf: float, market: str
) -> None:
    c = _company(price=1.0, shares=shares, last_q=last_q, ttm=ttm, ocf=ocf, market=market)
    with pytest.raises(ValueError, match="股本"):
        fair_value_band(c)


@given(
    price=st.floats(min_value=-100.0, max_value=0.0, allow_nan=False, allow_infinity=False),
    shares=shares_pos,
    last_q=profit_pos,
    ttm=profit_pos,
    ocf=finite_nonneg,
    market=cashflow_markets,
)
@settings(max_examples=150, deadline=None)
def test_verdict_rejects_nonpositive_price(
    price: float, shares: float, last_q: float, ttm: float, ocf: float, market: str
) -> None:
    c = _company(price=price, shares=shares, last_q=last_q, ttm=ttm, ocf=ocf, market=market)
    with pytest.raises(ValueError, match="价格"):
        verdict(c)


@given(
    price=price_pos,
    shares=st.floats(min_value=-100.0, max_value=0.0, allow_nan=False, allow_infinity=False),
    last_q=st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    ttm=st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    ocf=finite_nonneg,
    market=cashflow_markets,
)
@settings(max_examples=150, deadline=None)
def test_verdict_rejects_nonpositive_shares(
    price: float, shares: float, last_q: float, ttm: float, ocf: float, market: str
) -> None:
    c = _company(price=price, shares=shares, last_q=last_q, ttm=ttm, ocf=ocf, market=market)
    with pytest.raises(ValueError, match="股本"):
        verdict(c)


@given(
    price=price_pos,
    shares=shares_pos,
    last_q=profit_pos,
    ttm=profit_pos,
    ocf=finite_nonneg,
    market=unknown_markets,
)
@settings(max_examples=100, deadline=None)
def test_verdict_unknown_market_raises_chinese(
    price: float, shares: float, last_q: float, ttm: float, ocf: float, market: str
) -> None:
    c = _company(price=price, shares=shares, last_q=last_q, ttm=ttm, ocf=ocf, market=market)
    with pytest.raises(ValueError, match="未知市场"):
        verdict(c)


@given(
    price=price_pos,
    shares=shares_pos,
    last_q=profit_pos,
    ttm=profit_pos,
    ocf=finite_nonneg,
    market=no_cashflow_markets,
)
@settings(max_examples=100, deadline=None)
def test_verdict_no_cashflow_market_raises_chinese(
    price: float, shares: float, last_q: float, ttm: float, ocf: float, market: str
) -> None:
    c = _company(price=price, shares=shares, last_q=last_q, ttm=ttm, ocf=ocf, market=market)
    with pytest.raises(ValueError, match="没有现金流"):
        verdict(c)


@given(
    price=price_pos,
    shares=shares_pos,
    last_q=st.floats(min_value=-200.0, max_value=0.0, allow_nan=False, allow_infinity=False),
    ttm=st.floats(min_value=-200.0, max_value=200.0, allow_nan=False, allow_infinity=False),
    ocf=finite_nonneg,
    market=cashflow_markets,
)
@settings(max_examples=200, deadline=None)
def test_verdict_too_hard_clears_band_and_uses_note(
    price: float, shares: float, last_q: float, ttm: float, ocf: float, market: str
) -> None:
    c = _company(price=price, shares=shares, last_q=last_q, ttm=ttm, ocf=ocf, market=market)
    assume(too_hard(c))
    r = verdict(c)
    assert r["call"] == "too hard pile"
    assert r["band"] is None
    assert r["premium_to_band_top"] is None
    assert r["cash_quality"] is None
    assert r["note"] == NOTES["too hard pile"]
    assert r["currency"] == markets.load(market)["currency"]


@given(
    # Keep swing ≤ MAX_SWING so the company is valued.
    base=profit_pos,
    factor=st.floats(min_value=1.0, max_value=MAX_SWING, allow_nan=False, allow_infinity=False),
    direction=st.booleans(),
    shares=shares_pos,
    # ocf relative to ttm drives the 0.5 cash-quality gate.
    ocf_ratio=st.floats(min_value=0.0, max_value=2.0, allow_nan=False, allow_infinity=False),
    price_factor=st.floats(min_value=0.05, max_value=5.0, allow_nan=False, allow_infinity=False),
    market=cashflow_markets,
)
@settings(max_examples=300, deadline=None)
def test_verdict_call_partition_matches_price_and_cash_quality(
    base: float,
    factor: float,
    direction: bool,
    shares: float,
    ocf_ratio: float,
    price_factor: float,
    market: str,
) -> None:
    if direction:
        annualised, ttm = base * factor, base
    else:
        annualised, ttm = base, base * factor
    last_q = annualised / 4
    ocf = ttm * ocf_ratio
    # Price scaled off band mid so we hit all three call buckets.
    c0 = _company(price=1.0, shares=shares, last_q=last_q, ttm=ttm, ocf=ocf, market=market)
    assume(not too_hard(c0))
    lo, hi = fair_value_band(c0)
    assume(hi > 0 and math.isfinite(hi) and math.isfinite(lo))
    mid = (lo + hi) / 2 if hi > lo else hi
    assume(mid > 0)
    price = mid * price_factor
    assume(price > 0)
    c = _company(price=price, shares=shares, last_q=last_q, ttm=ttm, ocf=ocf, market=market)
    r = verdict(c)
    q = cash_quality(c)
    assert r["call"] in NOTES
    assert r["note"] == NOTES[r["call"]]
    assert r["band"] == (round(lo, 2), round(hi, 2))
    assert r["cash_quality"] == round(q, 2)
    assert r["premium_to_band_top"] == round(price / hi - 1, 3)
    if price <= lo and q >= 0.5:
        assert r["call"] == "margin of safety"
    elif price <= hi:
        assert r["call"] == "fair, no margin"
    else:
        assert r["call"] == "expensive"


@given(
    ttm=st.floats(min_value=-1e4, max_value=1e4, allow_nan=False, allow_infinity=False),
    ocf=st.floats(min_value=-1e4, max_value=1e4, allow_nan=False, allow_infinity=False),
    shares=shares_pos,
    last_q=profit_pos,
)
@settings(max_examples=200, deadline=None)
def test_cash_quality_is_ocf_over_ttm_or_nan(
    ttm: float, ocf: float, shares: float, last_q: float
) -> None:
    c = _company(price=1.0, shares=shares, last_q=last_q, ttm=ttm, ocf=ocf)
    q = cash_quality(c)
    if ttm:
        assert q == pytest.approx(ocf / ttm)
    else:
        assert math.isnan(q)
