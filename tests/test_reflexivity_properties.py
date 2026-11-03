"""Hypothesis properties for pipeline.reflexivity_demo (formal check).

Promises grounded in PriceThresholdThesis / RelativeThesis / evaluate /
returns / lead_lag / divergence_points / load_market:
1. PriceThresholdThesis: threshold must be finite and > 0 (「门槛」);
   deadline must be after registered_on (「到期日」).
2. RelativeThesis: empty/duplicate/benchmark-in-basket rejected; window
   must start on/after registered_on and end after start.
3. evaluate(PriceThreshold): FALSIFIED iff any close in (registered_on,
   deadline] >= threshold; else PENDING if deadline > last date, else
   NOT_FALSIFIED. Close ON registered_on never counts.
4. evaluate(Relative): PENDING if end > last date; else FALSIFIED iff
   equal-weight basket return > benchmark return; else NOT_FALSIFIED.
5. evaluate always returns one of STATUSES (never claims "correct").
6. returns length is n-1; lead_lag tries 2*max_lag+1 lags; SE = 1/sqrt(n).
7. divergence_points are causal (future edits do not move past flags) and
   only emit the two documented types.
8. load_market / generate_demo_data unknown market → 「未知市场」.
9. example_theses threshold = round(close[reg] * PRICE_FACTOR, 2) using
   only pre-registration data.
"""
from __future__ import annotations

import datetime as dt
import math

import pytest
from hypothesis import assume, given, settings, strategies as st

import markets
from pipeline.reflexivity_demo import (
    FALSIFIED,
    HORIZON_DAYS,
    MAX_LAG,
    NOT_FALSIFIED,
    PENDING,
    PRICE_FACTOR,
    REGISTER_DAYS_BEFORE_END,
    START,
    STATUSES,
    PriceThresholdThesis,
    ReflexivityDemoError,
    RelativeThesis,
    divergence_points,
    evaluate,
    example_theses,
    generate_demo_data,
    lead_lag,
    lead_lag_summary,
    load_market,
    returns,
    rolling_corr,
)

KNOWN_MARKETS = sorted(markets.available())
assert KNOWN_MARKETS

known_markets = st.sampled_from(KNOWN_MARKETS)
unknown_markets = st.one_of(
    st.sampled_from(["CN_A", "nasdaq", "", "../demo", "DEMO", "btc", "A股", "rates", "crypto_x"]),
    st.text(
        alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
        min_size=1,
        max_size=12,
    ).filter(lambda s: s not in set(KNOWN_MARKETS)),
)

# Finite positive thresholds (bool is subclass of int — exclude via strategy).
finite_pos = st.floats(min_value=1e-6, max_value=1e6, allow_nan=False, allow_infinity=False)
bad_threshold = st.one_of(
    st.just(0.0),
    st.just(True),
    st.just(False),
    st.floats(min_value=-1e3, max_value=0.0, allow_nan=False, allow_infinity=False),
    st.sampled_from([float("nan"), float("inf"), float("-inf")]),
)

day_offsets = st.integers(min_value=0, max_value=400)


def _d(i: int) -> dt.date:
    return START + dt.timedelta(days=i)


@given(threshold=bad_threshold, due=day_offsets, reg=day_offsets)
@settings(max_examples=200, deadline=None)
def test_price_threshold_rejects_non_finite_positive(
    threshold: float, due: int, reg: int
) -> None:
    assume(due > reg)  # isolate the threshold gate
    with pytest.raises(ReflexivityDemoError, match="门槛"):
        PriceThresholdThesis("DEMO-IDX", threshold, _d(due), _d(reg))


@given(threshold=finite_pos, due=day_offsets, reg=day_offsets)
@settings(max_examples=200, deadline=None)
def test_price_threshold_rejects_deadline_not_after_registration(
    threshold: float, due: int, reg: int
) -> None:
    assume(due <= reg)
    with pytest.raises(ReflexivityDemoError, match="到期日"):
        PriceThresholdThesis("DEMO-IDX", threshold, _d(due), _d(reg))


@given(
    start=day_offsets,
    end=day_offsets,
    reg=day_offsets,
)
@settings(max_examples=150, deadline=None)
def test_relative_rejects_window_before_registration(
    start: int, end: int, reg: int
) -> None:
    assume(start < reg)
    assume(end > start)
    with pytest.raises(ReflexivityDemoError, match="登记日"):
        RelativeThesis(("DEMO-BASKET-A",), "DEMO-BENCH", _d(start), _d(end), _d(reg))


@given(start=day_offsets, end=day_offsets, reg=day_offsets)
@settings(max_examples=150, deadline=None)
def test_relative_rejects_end_not_after_start(
    start: int, end: int, reg: int
) -> None:
    assume(start >= reg)
    assume(end <= start)
    with pytest.raises(ReflexivityDemoError, match="窗口终点"):
        RelativeThesis(("DEMO-BASKET-A",), "DEMO-BENCH", _d(start), _d(end), _d(reg))


@given(data=st.data())
@settings(max_examples=100, deadline=None)
def test_relative_rejects_empty_duplicate_or_benchmark_in_basket(data) -> None:
    reg, end = 5, 20
    bad = data.draw(
        st.sampled_from(
            [
                (),
                ("DEMO-BENCH",),
                ("DEMO-BASKET-A", "DEMO-BENCH"),
                ("DEMO-BASKET-A", "DEMO-BASKET-A"),
            ]
        )
    )
    with pytest.raises(ReflexivityDemoError):
        RelativeThesis(bad, "DEMO-BENCH", _d(reg), _d(end), _d(reg))


@given(
    market=known_markets,
    seed=st.integers(min_value=0, max_value=10_000),
    n=st.integers(min_value=80, max_value=160),
    reg_i=st.integers(min_value=5, max_value=40),
    horizon=st.integers(min_value=5, max_value=50),
    thr_scale=st.floats(min_value=0.5, max_value=2.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=120, deadline=None)
def test_evaluate_price_threshold_partition(
    market: str,
    seed: int,
    n: int,
    reg_i: int,
    horizon: int,
    thr_scale: float,
) -> None:
    """FALSIFIED / PENDING / NOT_FALSIFIED match the documented close window."""
    assume(reg_i + horizon < n + 100)  # deadline may be past or future vs data
    d = generate_demo_data(seed=seed, n=n, market_key=market)
    dates = d["dates"]
    px = d["DEMO-IDX"]
    reg = dates[reg_i]
    due = reg + dt.timedelta(days=horizon)
    # Threshold relative to max post-registration close in data (or reg close).
    window = [c for day, c in zip(dates, px) if reg < day <= due]
    base = max(window) if window else px[reg_i]
    assume(base > 0 and math.isfinite(base))
    threshold = round(base * thr_scale, 6)
    assume(threshold > 0 and math.isfinite(threshold))
    thesis = PriceThresholdThesis("DEMO-IDX", threshold, due, reg)
    got = evaluate(thesis, d)
    assert got in STATUSES

    hit = any(c >= threshold for day, c in zip(dates, px) if reg < day <= due)
    last = dates[-1]
    if hit:
        assert got == FALSIFIED
    elif due > last:
        assert got == PENDING
    else:
        assert got == NOT_FALSIFIED


@given(
    market=known_markets,
    seed=st.integers(min_value=0, max_value=5000),
    n=st.integers(min_value=40, max_value=100),
    reg_i=st.integers(min_value=2, max_value=20),
    horizon=st.integers(min_value=3, max_value=25),
    bump=st.floats(min_value=1.0, max_value=1e6, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=80, deadline=None)
def test_close_on_registration_day_never_falsifies(
    market: str, seed: int, n: int, reg_i: int, horizon: int, bump: float
) -> None:
    d = generate_demo_data(seed=seed, n=n, market_key=market)
    dates = d["dates"]
    reg = dates[reg_i]
    due = reg + dt.timedelta(days=horizon)
    assume(due <= dates[-1])  # force settled window
    # Make registration-day close huge; keep post-reg closes safely below threshold.
    px = list(d["DEMO-IDX"])
    post = [c for day, c in zip(dates, px) if reg < day <= due]
    assume(post)
    ceiling = max(post)
    threshold = ceiling + 1.0  # strictly above every post-reg close
    px[reg_i] = ceiling + bump  # ON registered_on — must not count
    d2 = {**d, "DEMO-IDX": px}
    thesis = PriceThresholdThesis("DEMO-IDX", threshold, due, reg)
    assert evaluate(thesis, d2) == NOT_FALSIFIED


@given(
    market=known_markets,
    seed=st.integers(min_value=0, max_value=5000),
    n=st.integers(min_value=50, max_value=120),
    reg_i=st.integers(min_value=2, max_value=30),
    basket_end=st.floats(min_value=50.0, max_value=200.0, allow_nan=False, allow_infinity=False),
    bench_end=st.floats(min_value=50.0, max_value=200.0, allow_nan=False, allow_infinity=False),
    pending=st.booleans(),
)
@settings(max_examples=120, deadline=None)
def test_evaluate_relative_partition(
    market: str,
    seed: int,
    n: int,
    reg_i: int,
    basket_end: float,
    bench_end: float,
    pending: bool,
) -> None:
    d = generate_demo_data(seed=seed, n=n, market_key=market)
    dates = d["dates"]
    assume(reg_i + 2 < n)
    reg = dates[reg_i]
    if pending:
        end = dates[-1] + dt.timedelta(days=5)
    else:
        end = dates[min(reg_i + 10, n - 1)]
        assume(end > reg)
    start = reg
    # Flat series at 100 until end index (or last available), then set end levels.
    def flat_then(end_level: float) -> list[float]:
        out = [100.0] * n
        if not pending:
            end_i = dates.index(end)
            out[end_i] = end_level
        return out

    d2 = {
        **d,
        "DEMO-BASKET-A": flat_then(basket_end),
        "DEMO-BASKET-B": flat_then(basket_end),
        "DEMO-BENCH": flat_then(bench_end),
    }
    thesis = RelativeThesis(
        ("DEMO-BASKET-A", "DEMO-BASKET-B"), "DEMO-BENCH", start, end, reg
    )
    got = evaluate(thesis, d2)
    assert got in STATUSES
    if pending:
        assert got == PENDING
    else:
        basket_ret = basket_end / 100.0 - 1.0
        bench_ret = bench_end / 100.0 - 1.0
        if basket_ret > bench_ret:
            assert got == FALSIFIED
        else:
            assert got == NOT_FALSIFIED


@given(
    prices=st.lists(
        st.floats(min_value=1.0, max_value=1e3, allow_nan=False, allow_infinity=False),
        min_size=2,
        max_size=80,
    )
)
@settings(max_examples=200, deadline=None)
def test_returns_length_is_n_minus_one(prices: list[float]) -> None:
    r = returns(prices)
    assert len(r) == len(prices) - 1
    for i, ret in enumerate(r):
        assert ret == pytest.approx(prices[i + 1] / prices[i] - 1)


@given(
    x=st.lists(
        st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=20,
        max_size=60,
    ),
    y=st.lists(
        st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        min_size=20,
        max_size=60,
    ),
    max_lag=st.integers(min_value=0, max_value=MAX_LAG),
)
@settings(max_examples=100, deadline=None)
def test_lead_lag_tried_count_and_se(
    x: list[float], y: list[float], max_lag: int
) -> None:
    n = min(len(x), len(y))
    x, y = x[:n], y[:n]
    assume(n > 2 * max_lag + 2)
    ll = lead_lag(x, y, max_lag)
    assert set(ll) == set(range(-max_lag, max_lag + 1))
    assert len(ll) == 2 * max_lag + 1
    s = lead_lag_summary(x, y, max_lag)
    assert s["tried"] == 2 * max_lag + 1
    assert s["se"] == pytest.approx(1 / math.sqrt(s["n"]))
    assert s["z"] == pytest.approx(abs(s["corr"]) / s["se"])
    assert s["lag"] in ll
    assert s["corr"] == ll[s["lag"]]


@given(
    lookback=st.integers(min_value=2, max_value=8),
    mom=st.integers(min_value=1, max_value=5),
    n=st.integers(min_value=15, max_value=40),
    seed=st.integers(min_value=0, max_value=10_000),
)
@settings(max_examples=80, deadline=None)
def test_divergence_types_and_causality(
    lookback: int, mom: int, n: int, seed: int
) -> None:
    rng = __import__("random").Random(seed)
    price = [100.0]
    narr = [0.0]
    for _ in range(n - 1):
        price.append(price[-1] * (1 + rng.uniform(-0.05, 0.05)))
        narr.append(narr[-1] + rng.uniform(-1.0, 1.0))
    pts = divergence_points(price, narr, lookback=lookback, mom=mom)
    for p in pts:
        assert p["type"] in ("price_high_narrative_fading", "price_low_narrative_rising")
        t = p["t"]
        assert t >= max(lookback, mom)
        win = price[t - lookback:t]
        m = narr[t] - narr[t - mom]
        if p["type"] == "price_high_narrative_fading":
            assert price[t] > max(win) and m < 0
        else:
            assert price[t] < min(win) and m > 0
        assert p["narr_mom"] == pytest.approx(m)

    # Causality: mutating the future must not change flags with t <= k.
    k = n // 2
    assume(k >= max(lookback, mom))
    base = [p for p in pts if p["t"] <= k]
    px2 = price[: k + 1] + [x * 5 for x in price[k + 1:]]
    nr2 = narr[: k + 1] + [-x for x in narr[k + 1:]]
    assert [p for p in divergence_points(px2, nr2, lookback=lookback, mom=mom) if p["t"] <= k] == base


@given(market=unknown_markets, seed=st.integers(min_value=0, max_value=100))
@settings(max_examples=80, deadline=None)
def test_unknown_market_raises_chinese(market: str, seed: int) -> None:
    with pytest.raises(ReflexivityDemoError, match="未知市场"):
        load_market(market)
    with pytest.raises(ReflexivityDemoError, match="未知市场"):
        generate_demo_data(seed=seed, n=20, market_key=market)


@given(
    market=known_markets,
    seed=st.integers(min_value=0, max_value=5000),
    n=st.integers(min_value=REGISTER_DAYS_BEFORE_END + HORIZON_DAYS + 5, max_value=280),
)
@settings(max_examples=60, deadline=None)
def test_example_theses_use_pre_registration_close(
    market: str, seed: int, n: int
) -> None:
    d = generate_demo_data(seed=seed, n=n, market_key=market)
    t1, t2 = example_theses(d)
    i = d["dates"].index(t1.registered_on)
    assert i == len(d["dates"]) - 1 - REGISTER_DAYS_BEFORE_END
    assert t1.threshold == round(d["DEMO-IDX"][i] * PRICE_FACTOR, 2)
    assert t1.deadline == t1.registered_on + dt.timedelta(days=HORIZON_DAYS)
    assert t2.start >= t2.registered_on
    assert t2.end == t2.start + dt.timedelta(days=HORIZON_DAYS)
    # Future price edits must not move registration parameters.
    d2 = {
        **d,
        "DEMO-IDX": d["DEMO-IDX"][: i + 1] + [x * 3 for x in d["DEMO-IDX"][i + 1:]],
    }
    assert example_theses(d2) == (t1, t2)
    # Statuses never claim correctness.
    for th in (t1, t2):
        v = evaluate(th, d)
        assert v in STATUSES
        assert "correct" not in v and "right" not in v


@given(
    x=st.lists(
        st.floats(min_value=-2.0, max_value=2.0, allow_nan=False, allow_infinity=False),
        min_size=25,
        max_size=50,
    ),
    y=st.lists(
        st.floats(min_value=-2.0, max_value=2.0, allow_nan=False, allow_infinity=False),
        min_size=25,
        max_size=50,
    ),
    window=st.integers(min_value=5, max_value=15),
)
@settings(max_examples=60, deadline=None)
def test_rolling_corr_prefix_none_then_finite(
    x: list[float], y: list[float], window: int
) -> None:
    n = min(len(x), len(y))
    x, y = x[:n], y[:n]
    assume(n >= window)
    rc = rolling_corr(x, y, window)
    assert len(rc) == n
    assert rc[: window - 1] == [None] * (window - 1)
    for v in rc[window - 1:]:
        assert v is not None
        assert math.isfinite(v)
        assert -1.0 - 1e-9 <= v <= 1.0 + 1e-9
