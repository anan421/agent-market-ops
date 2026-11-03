"""Hypothesis properties for pipeline.dsr_demo (formal check).

Promises grounded in deflated_sharpe / sr0_annual / ppy_for / gate constants:
1. deflated_sharpe always returns a float in [0, 1].
2. Degenerate series (n < 3 or zero sample std) → DSR == 0.0.
3. sr0_annual(n_trials < 2, …) == 0.0; for n_trials >= 2 the value is finite,
   non-negative, and non-decreasing in n_trials (fixed variance).
4. ppy_for(unknown) raises ValueError whose message contains 「未知市场」;
   known markets return an int > 1 matching markets.load.
5. run_demo with n_obs < MIN_N_OBS never marks any strategy passed
   (gate uses MIN_N_OBS and DSR_MIN as documented in the module).
"""
from __future__ import annotations

import math

import pytest

np = pytest.importorskip("numpy")

from hypothesis import assume, given, settings, strategies as st

from pipeline.dsr_demo import (
    DSR_MIN,
    MIN_N_OBS,
    V_FLOOR,
    deflated_sharpe,
    ppy_for,
    run_demo,
    sr0_annual,
)

import markets

# Finite returns; keep magnitude modest so mean/std stay numerically stable.
returns_elem = st.floats(
    min_value=-0.05,
    max_value=0.05,
    allow_nan=False,
    allow_infinity=False,
)
returns_series = st.lists(returns_elem, min_size=0, max_size=120)
ppys = st.integers(min_value=2, max_value=400)
sr0_anns = st.floats(
    min_value=0.0,
    max_value=5.0,
    allow_nan=False,
    allow_infinity=False,
)
variances = st.floats(
    min_value=0.0,
    max_value=4.0,
    allow_nan=False,
    allow_infinity=False,
)
n_trials_small = st.integers(min_value=0, max_value=1)
n_trials_ok = st.integers(min_value=2, max_value=500)
known_markets = st.sampled_from(sorted(markets.available()))
# Unknown / hostile market ids (must not collide with real configs).
unknown_markets = st.one_of(
    st.sampled_from(["CN_A", "nasdaq", "", "../demo", "DEMO", "btc", "A股"]),
    st.text(
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
        min_size=1,
        max_size=12,
    ).filter(lambda s: s not in set(markets.available())),
)


@given(returns=returns_series, ppy=ppys, sr0_ann=sr0_anns)
@settings(max_examples=300, deadline=None)
def test_deflated_sharpe_in_unit_interval(
    returns: list[float], ppy: int, sr0_ann: float
) -> None:
    dsr = deflated_sharpe(returns, ppy, sr0_ann)
    assert isinstance(dsr, float)
    assert 0.0 <= dsr <= 1.0
    assert math.isfinite(dsr)


@given(
    n=st.integers(min_value=0, max_value=2),
    fill=returns_elem,
    ppy=ppys,
    sr0_ann=sr0_anns,
)
@settings(max_examples=200, deadline=None)
def test_deflated_sharpe_short_series_is_zero(
    n: int, fill: float, ppy: int, sr0_ann: float
) -> None:
    """API gate: n < 3 → 0.0 (independent of MIN_N_OBS, which gates run_demo)."""
    assert deflated_sharpe([fill] * n, ppy, sr0_ann) == 0.0


# Exact binary floats so np.std(ddof=1) is truly 0 (API uses `== 0`, not ≈0).
exact_fills = st.sampled_from([0.0, 1.0, -1.0, 0.5, -0.5, 2.0, -2.0])


@given(
    n=st.integers(min_value=3, max_value=80),
    fill=exact_fills,
    ppy=ppys,
    sr0_ann=sr0_anns,
)
@settings(max_examples=200, deadline=None)
def test_deflated_sharpe_zero_std_is_zero(
    n: int, fill: float, ppy: int, sr0_ann: float
) -> None:
    """Constant exact-float series → sample std 0 → DSR 0.0 (matches `std == 0` gate)."""
    series = [fill] * n
    assert float(np.asarray(series, dtype=float).std(ddof=1)) == 0.0
    assert deflated_sharpe(series, ppy, sr0_ann) == 0.0


@given(n_trials=n_trials_small, variance=variances)
@settings(max_examples=200, deadline=None)
def test_sr0_annual_zero_when_fewer_than_two_trials(
    n_trials: int, variance: float
) -> None:
    assert sr0_annual(n_trials, variance) == 0.0


@given(n_trials=n_trials_ok, variance=variances)
@settings(max_examples=300, deadline=None)
def test_sr0_annual_finite_nonneg_for_n_ge_two(
    n_trials: int, variance: float
) -> None:
    s0 = sr0_annual(n_trials, variance)
    assert math.isfinite(s0)
    assert s0 >= 0.0
    # V_FLOOR is applied inside: variance below floor must match floor case.
    if variance < V_FLOOR:
        assert s0 == sr0_annual(n_trials, V_FLOOR)


@given(
    n_a=st.integers(min_value=2, max_value=200),
    n_b=st.integers(min_value=2, max_value=200),
    variance=st.floats(min_value=V_FLOOR, max_value=4.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=250, deadline=None)
def test_sr0_annual_nondecreasing_in_n_trials(
    n_a: int, n_b: int, variance: float
) -> None:
    lo, hi = (n_a, n_b) if n_a <= n_b else (n_b, n_a)
    assert sr0_annual(lo, variance) <= sr0_annual(hi, variance) + 1e-12


@given(market=known_markets)
@settings(max_examples=50, deadline=None)
def test_ppy_for_known_matches_markets_config(market: str) -> None:
    p = ppy_for(market)
    assert isinstance(p, int)
    assert p > 1
    assert p == markets.load(market)["periods_per_year"]


@given(market=unknown_markets)
@settings(max_examples=100, deadline=None)
def test_ppy_for_unknown_raises_chinese_valueerror(market: str) -> None:
    with pytest.raises(ValueError, match="未知市场"):
        ppy_for(market)


@given(
    seed=st.integers(min_value=0, max_value=10_000),
    n_strategies=st.integers(min_value=2, max_value=8),
    n_obs=st.integers(min_value=3, max_value=MIN_N_OBS - 1),
)
@settings(max_examples=40, deadline=None)
def test_run_demo_rejects_when_n_obs_below_min(
    seed: int, n_strategies: int, n_obs: int
) -> None:
    """Documented gate: passed requires n_obs >= MIN_N_OBS (and DSR_MIN, …)."""
    assume(MIN_N_OBS > 3)
    assert DSR_MIN == 0.95
    out = run_demo(seed=seed, n_strategies=n_strategies, n_obs=n_obs, market="demo")
    assert all(r["passed"] is False for r in out["results"])
    assert all(0.0 <= r["dsr"] <= 1.0 for r in out["results"])
