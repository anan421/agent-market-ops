import dataclasses
import datetime as dt
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pytest
from pipeline import reflexivity_demo as rd


def _data():
    return rd.generate_demo_data(seed=7, n=60, market_key="us")


def test_determinism_by_seed():
    a, b = rd.generate_demo_data(1, market_key="hk"), rd.generate_demo_data(1, market_key="hk")
    assert a["DEMO-IDX"] == b["DEMO-IDX"] and a["DEMO-NARRATIVE"] == b["DEMO-NARRATIVE"]
    assert rd.generate_demo_data(2, market_key="hk")["DEMO-IDX"] != a["DEMO-IDX"]
    assert "示例数据" in a["disclaimer"]


def test_feedback_metrics_and_divergence():
    d = rd.generate_demo_data(market_key="crypto")
    r = rd.returns(d["DEMO-IDX"])
    ll = rd.lead_lag(r, d["DEMO-NARRATIVE"][1:], 3)
    assert set(ll) == set(range(-3, 4))
    assert ll[1] > 0  # narrative chases returns by construction
    rc = rd.rolling_corr(r, d["DEMO-NARRATIVE"][1:], 20)
    assert len(rc) == len(r) and rc[0] is None
    assert rd.divergence_points([1, 2, 3, 4], [0, 1, 0, -1], lookback=2, mom=1)[0]["type"] == "price_high_narrative_fading"


def test_price_threshold_boundary_ge():
    d = _data()
    peak = max(d["DEMO-IDX"])
    end = d["dates"][-1]
    assert rd.evaluate(rd.PriceThresholdThesis("DEMO-IDX", peak, end), d) == rd.FALSIFIED
    assert rd.evaluate(rd.PriceThresholdThesis("DEMO-IDX", peak + 1e-9, end), d) == rd.NOT_FALSIFIED


def test_relative_thesis_both_outcomes():
    d = _data()
    dates = d["dates"]
    d["DEMO-BASKET-A"] = [100.0] * 60; d["DEMO-BASKET-B"] = [100.0] * 60
    d["DEMO-BENCH"] = [100.0] * 59 + [101.0]
    t = rd.RelativeThesis(("DEMO-BASKET-A", "DEMO-BASKET-B"), "DEMO-BENCH", dates[0], dates[-1])
    assert rd.evaluate(t, d) == rd.NOT_FALSIFIED
    d["DEMO-BASKET-A"] = [100.0] * 59 + [103.0]  # basket +1.5% > bench +1%
    assert rd.evaluate(t, d) == rd.FALSIFIED


def test_thesis_immutable():
    t = rd.PriceThresholdThesis("DEMO-IDX", 120.0, dt.date(2000, 3, 1))
    with pytest.raises(dataclasses.FrozenInstanceError):
        t.threshold = 999.0
    r = rd.RelativeThesis(("DEMO-BASKET-A",), "DEMO-BENCH", dt.date(2000, 1, 3), dt.date(2000, 2, 1))
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.end = dt.date(2001, 1, 1)


def test_output_never_says_correct():
    d = _data()
    outs = {rd.evaluate(rd.PriceThresholdThesis("DEMO-IDX", x, d["dates"][-1]), d) for x in (0, 1e9)}
    assert outs == {"falsified", "not_falsified"}
    for o in outs:
        assert "correct" not in o and "right" not in o and o != "confirmed"


@pytest.mark.parametrize("key", sorted(rd.MARKET_PRESETS))
def test_all_markets_run(key, capsys):
    d = rd.main(["--market", key])
    for name in d["meta"]:
        m = rd.series_meta(d, name)
        assert m == rd.MARKET_PRESETS[key]
    t = rd.PriceThresholdThesis("DEMO-IDX", 1e9, d["dates"][-1])
    assert rd.evaluate(t, d) == rd.NOT_FALSIFIED


def test_market_read_from_fields_not_codes():
    with pytest.raises(ValueError):
        rd.generate_demo_data(1)  # no default market
    with pytest.raises(ValueError):
        rd.generate_demo_data(1, market={"market": "cn_a", "currency": "CNY"})  # tz missing
    d = rd.generate_demo_data(1, market={"market": "us", "currency": "USD", "tz": "America/New_York"})
    d["meta"]["DEMO-BENCH"] = {"market": "hk", "currency": "HKD", "tz": "Asia/Hong_Kong"}
    t = rd.RelativeThesis(("DEMO-BASKET-A",), "DEMO-BENCH", d["dates"][0], d["dates"][9])
    with pytest.raises(ValueError):
        rd.evaluate(t, d)


def test_cli_report_wording(capsys):
    rd.main(["--market", "us", "--seed", "3"])
    out = capsys.readouterr().out
    assert "被证伪" in out and "未被证伪 ≠ 我对了" in out
    assert "market: us (美股)" in out and "America/New_York" in out
    assert "correct" not in out.lower() and "我是对的" not in out


def test_market_enum_exact():
    assert set(rd.MARKET_PRESETS) == set(rd.ALLOWED_MARKETS) == {"cn_a", "hk", "us", "crypto", "futures", "fx", "demo"}
    assert rd.MARKET_PRESETS["demo"] == {"market": "demo", "currency": "DEMO", "tz": "UTC"}
    with pytest.raises(ValueError):
        rd.validate_meta({"market": "A股", "currency": "CNY", "tz": "Asia/Shanghai"})
    with pytest.raises(SystemExit):
        rd.main(["--market", "rates"])
