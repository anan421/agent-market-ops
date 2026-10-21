import math
import pytest
from pipeline.margin_of_safety_demo import Company, normal_profit, fair_value_band, verdict, EXAMPLE


def test_normal_profit_takes_the_lower():
    c = Company("x", 10, 1, last_q_profit=10, ttm_profit=15, ocf_ttm=15)
    assert normal_profit(c) == 15  # ttm 15 < 10*4*0.5=20


def test_haircut_bounds():
    with pytest.raises(ValueError):
        normal_profit(EXAMPLE[0], haircut=0)


def test_band_and_calls():
    a, b = (verdict(c) for c in EXAMPLE[:2])
    assert a["call"] == "expensive"        # DEMO-A: price 150 > band top 108
    assert b["call"] == "margin of safety"


def test_band_values():
    lo, hi = fair_value_band(EXAMPLE[1])
    assert math.isclose(lo, 2.0 * 15) and math.isclose(hi, 2.0 * 18)


def test_cheap_but_poor_cash_is_not_margin():
    c = Company("x", 1, 10, last_q_profit=10, ttm_profit=35, ocf_ttm=5)
    assert verdict(c)["call"] == "fair, no margin"


def test_volatile_profit_goes_to_too_hard_pile():
    c = Company("x", 1, 10, last_q_profit=50, ttm_profit=40, ocf_ttm=40)
    assert verdict(c)["call"] == "too hard pile"


def test_every_call_has_a_note():
    for c in EXAMPLE:
        assert verdict(c)["note"]


def test_markets_and_no_earnings():
    by = {c.name: verdict(c) for c in EXAMPLE}
    assert by["DEMO-HK (fictional)"]["currency"] == "HKD"
    assert by["DEMO-COIN (fictional, no earnings)"]["call"] == "too hard pile"
