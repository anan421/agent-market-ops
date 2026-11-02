"""Hypothesis properties for pipeline.fees (formal check).

Promises grounded in A-share-like fee_breakdown / commission:
1. Buy side: stamp_duty is always 0 for notional >= 0.
2. Sell side: stamp_duty > 0 whenever notional > 0 (DEFAULT_FEES.stamp_duty_sell > 0).
3. For both sides, total == sum of the named parts (commission, transfer, slippage, stamp_duty).
"""
from __future__ import annotations

from hypothesis import given, settings, strategies as st

from pipeline.fees import DEFAULT_FEES, FeeSchedule, commission, fee_breakdown

PART_KEYS = ("commission", "transfer", "slippage", "stamp_duty")

# Finite non-negative notionals; upper bound keeps float products well-behaved.
notionals = st.floats(
    min_value=0.0,
    max_value=1e9,
    allow_nan=False,
    allow_infinity=False,
)
positive_notionals = st.floats(
    min_value=1e-6,
    max_value=1e9,
    allow_nan=False,
    allow_infinity=False,
)
sides = st.sampled_from(["buy", "sell", "BUY", " Sell "])


@given(notional=notionals)
@settings(max_examples=300, deadline=None)
def test_buy_stamp_duty_always_zero(notional: float) -> None:
    b = fee_breakdown(notional, "buy")
    assert b["stamp_duty"] == 0.0


@given(notional=positive_notionals)
@settings(max_examples=300, deadline=None)
def test_sell_stamp_duty_positive_when_notional_positive(notional: float) -> None:
    assert DEFAULT_FEES.stamp_duty_sell > 0
    b = fee_breakdown(notional, "sell")
    assert b["stamp_duty"] > 0
    assert b["stamp_duty"] == notional * DEFAULT_FEES.stamp_duty_sell


@given(notional=notionals, side=sides)
@settings(max_examples=400, deadline=None)
def test_total_equals_sum_of_parts(notional: float, side: str) -> None:
    b = fee_breakdown(notional, side)
    parts_sum = sum(b[k] for k in PART_KEYS)
    assert b["total"] == parts_sum
    assert set(PART_KEYS) | {"total"} == set(b)


@given(notional=notionals)
@settings(max_examples=200, deadline=None)
def test_commission_is_max_of_rate_and_floor(notional: float) -> None:
    got = commission(notional)
    expected = max(notional * DEFAULT_FEES.commission_rate, DEFAULT_FEES.commission_min)
    assert got == expected


@given(
    notional=positive_notionals,
    commission_rate=st.floats(min_value=0.0, max_value=0.01, allow_nan=False, allow_infinity=False),
    commission_min=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    stamp=st.floats(min_value=1e-9, max_value=0.01, allow_nan=False, allow_infinity=False),
    transfer=st.floats(min_value=0.0, max_value=0.01, allow_nan=False, allow_infinity=False),
    slippage=st.floats(min_value=0.0, max_value=0.05, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=200, deadline=None)
def test_sell_stamp_scales_with_schedule(
    notional: float,
    commission_rate: float,
    commission_min: float,
    stamp: float,
    transfer: float,
    slippage: float,
) -> None:
    schedule = FeeSchedule(
        commission_rate=commission_rate,
        commission_min=commission_min,
        stamp_duty_sell=stamp,
        transfer_fee=transfer,
        slippage=slippage,
    )
    b = fee_breakdown(notional, "sell", schedule)
    assert b["stamp_duty"] == notional * stamp
    assert b["stamp_duty"] > 0
    buy = fee_breakdown(notional, "buy", schedule)
    assert buy["stamp_duty"] == 0.0
    assert b["total"] == sum(b[k] for k in PART_KEYS)
    assert buy["total"] == sum(buy[k] for k in PART_KEYS)
