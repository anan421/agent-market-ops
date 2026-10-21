"""Illustrative A-share-like fee table for paper P&L scaffolding.

These rates are **documentation examples**, not a broker quote and not advice.
Replace with your own broker schedule before any real simulation.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeeSchedule:
    """Simple one-way fee components (fractions of notional unless noted)."""

    commission_rate: float = 0.00025  # 0.025%
    commission_min: float = 5.0  # currency units
    stamp_duty_sell: float = 0.0005  # 0.05%, sell side only
    transfer_fee: float = 0.00001  # 0.001%
    slippage: float = 0.001  # 0.1% illustrative slippage


DEFAULT_FEES = FeeSchedule()


def commission(notional: float, schedule: FeeSchedule = DEFAULT_FEES) -> float:
    """Commission for one side of a trade."""
    if notional < 0:
        raise ValueError("notional must be >= 0")
    return max(abs(notional) * schedule.commission_rate, schedule.commission_min)


def round_trip_cost_pct(schedule: FeeSchedule = DEFAULT_FEES) -> float:
    """Rough all-in cost for a buy+sell round trip, as a fraction of notional.

    Ignores the commission floor (valid for large notionals). Includes
    stamp duty on the sell, transfer fee both ways, and slippage both ways.
    """
    one_way = (
        schedule.commission_rate
        + schedule.transfer_fee
        + schedule.slippage
    )
    return one_way * 2 + schedule.stamp_duty_sell


def fee_breakdown(notional: float, side: str, schedule: FeeSchedule = DEFAULT_FEES) -> dict[str, float]:
    """Return named fee components for a single side (`buy` or `sell`)."""
    side = side.lower().strip()
    if side not in {"buy", "sell"}:
        raise ValueError("side must be 'buy' or 'sell'")
    n = abs(float(notional))
    parts = {
        "commission": commission(n, schedule),
        "transfer": n * schedule.transfer_fee,
        "slippage": n * schedule.slippage,
        "stamp_duty": n * schedule.stamp_duty_sell if side == "sell" else 0.0,
    }
    parts["total"] = sum(parts.values())
    return parts
