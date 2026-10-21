from pipeline.fees import DEFAULT_FEES, commission, fee_breakdown, round_trip_cost_pct


def test_commission_floor():
    assert commission(1000) == DEFAULT_FEES.commission_min


def test_commission_large():
    assert commission(1_000_000) == 1_000_000 * DEFAULT_FEES.commission_rate


def test_round_trip_approx_30bp():
    # documentation example: ~0.30% all-in for large notionals
    pct = round_trip_cost_pct()
    assert 0.0025 < pct < 0.0035


def test_fee_breakdown_sell_has_stamp():
    b = fee_breakdown(100_000, "sell")
    assert b["stamp_duty"] > 0
    assert b["total"] == sum(v for k, v in b.items() if k != "total")


def test_fee_breakdown_buy_no_stamp():
    b = fee_breakdown(100_000, "buy")
    assert b["stamp_duty"] == 0.0
