"""Hypothesis properties for pipeline.fetch_prices_demo (formal check).

Promises grounded in synthetic_ohlcv:
1. len(rows) == days for days >= 0 (days == 0 → []).
2. Same (symbol, start, days, start_price) → identical rows (deterministic).
3. Every bar date is Mon–Fri; consecutive bars are successive weekdays
   (weekend gaps only).
4. If start is Sat/Sun, first bar is the following Monday.
5. Every row: symbol matches; synthetic is True; volume in
   [1_000_000, 1_499_999]; keys are the documented OHLCV set.
6. First open == round(start_price, 4); row[i].open == row[i-1].close.
7. After rounding: high >= max(open, close), low <= min(open, close),
   close >= 0.01, open/high/low/close all finite and > 0.
"""
from __future__ import annotations

from datetime import date, timedelta

from hypothesis import given, settings, strategies as st

from pipeline.fetch_prices_demo import synthetic_ohlcv

ROW_KEYS = ("date", "symbol", "open", "high", "low", "close", "volume", "synthetic")

symbols = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-_"),
    min_size=0,
    max_size=12,
)
# Bound calendar so weekday arithmetic stays cheap; include weekends.
starts = st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31))
days_vals = st.integers(min_value=0, max_value=60)
start_prices = st.floats(
    min_value=0.01,
    max_value=1e6,
    allow_nan=False,
    allow_infinity=False,
)


def _next_weekday(d: date) -> date:
    out = d
    while out.weekday() >= 5:
        out += timedelta(days=1)
    return out


def _next_session_after(d: date) -> date:
    nxt = d + timedelta(days=1)
    return _next_weekday(nxt)


@given(symbol=symbols, start=starts, days=days_vals, start_price=start_prices)
@settings(max_examples=250, deadline=None)
def test_length_equals_days(
    symbol: str, start: date, days: int, start_price: float
) -> None:
    rows = synthetic_ohlcv(symbol, start, days, start_price)
    assert len(rows) == days


@given(symbol=symbols, start=starts, days=days_vals, start_price=start_prices)
@settings(max_examples=200, deadline=None)
def test_deterministic_same_inputs(
    symbol: str, start: date, days: int, start_price: float
) -> None:
    a = synthetic_ohlcv(symbol, start, days, start_price)
    b = synthetic_ohlcv(symbol, start, days, start_price)
    assert a == b


@given(symbol=symbols, start=starts, days=days_vals, start_price=start_prices)
@settings(max_examples=200, deadline=None)
def test_weekdays_only_and_successive_sessions(
    symbol: str, start: date, days: int, start_price: float
) -> None:
    rows = synthetic_ohlcv(symbol, start, days, start_price)
    prev: date | None = None
    for r in rows:
        d = date.fromisoformat(r["date"])
        assert d.weekday() < 5
        if prev is None:
            assert d == _next_weekday(start)
        else:
            assert d == _next_session_after(prev)
        prev = d


@given(
    symbol=symbols,
    start=st.sampled_from(
        [
            date(2026, 10, 17),  # Sat
            date(2026, 10, 18),  # Sun
            date(2026, 1, 3),  # Sat
            date(2025, 12, 28),  # Sun
        ]
    ),
    days=st.integers(min_value=1, max_value=10),
    start_price=start_prices,
)
@settings(max_examples=80, deadline=None)
def test_weekend_start_begins_on_monday(
    symbol: str, start: date, days: int, start_price: float
) -> None:
    assert start.weekday() >= 5
    rows = synthetic_ohlcv(symbol, start, days, start_price)
    first = date.fromisoformat(rows[0]["date"])
    assert first.weekday() == 0
    assert first == _next_weekday(start)


@given(symbol=symbols, start=starts, days=days_vals, start_price=start_prices)
@settings(max_examples=250, deadline=None)
def test_row_shape_symbol_synthetic_volume(
    symbol: str, start: date, days: int, start_price: float
) -> None:
    rows = synthetic_ohlcv(symbol, start, days, start_price)
    for r in rows:
        assert tuple(r.keys()) == ROW_KEYS or set(r.keys()) == set(ROW_KEYS)
        assert r["symbol"] == symbol
        assert r["synthetic"] is True
        assert 1_000_000 <= r["volume"] <= 1_499_999
        assert isinstance(r["volume"], int)


@given(symbol=symbols, start=starts, days=days_vals, start_price=start_prices)
@settings(max_examples=200, deadline=None)
def test_open_chain_and_first_open(
    symbol: str, start: date, days: int, start_price: float
) -> None:
    rows = synthetic_ohlcv(symbol, start, days, start_price)
    if not rows:
        return
    assert rows[0]["open"] == round(start_price, 4)
    for i in range(1, len(rows)):
        assert rows[i]["open"] == rows[i - 1]["close"]


@given(symbol=symbols, start=starts, days=days_vals, start_price=start_prices)
@settings(max_examples=250, deadline=None)
def test_ohlc_inequalities_and_positive_close(
    symbol: str, start: date, days: int, start_price: float
) -> None:
    rows = synthetic_ohlcv(symbol, start, days, start_price)
    for r in rows:
        o, h, l, c = r["open"], r["high"], r["low"], r["close"]
        assert all(isinstance(x, float) for x in (o, h, l, c))
        assert all(x > 0 for x in (o, h, l, c))
        assert c >= 0.01
        assert h >= max(o, c)
        assert l <= min(o, c)
