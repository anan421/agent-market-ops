import dataclasses
import datetime as dt
import sys

import markets
import pytest

from pipeline import reflexivity_demo as rd

MARKETS = markets.available()
D = lambda i: rd.START + dt.timedelta(days=i)


def _data(n=60, key="us"):
    return rd.generate_demo_data(seed=7, n=n, market_key=key)


def test_determinism_by_seed():
    a, b = rd.generate_demo_data(1, market_key="hk"), rd.generate_demo_data(1, market_key="hk")
    assert a["DEMO-IDX"] == b["DEMO-IDX"] and a["DEMO-NARRATIVE"] == b["DEMO-NARRATIVE"]
    assert rd.generate_demo_data(2, market_key="hk")["DEMO-IDX"] != a["DEMO-IDX"]
    assert "示例数据" in a["disclaimer"]


def test_feedback_metrics_and_divergence():
    d = rd.generate_demo_data(market_key="crypto")
    r = rd.returns(d["DEMO-IDX"])
    s = rd.lead_lag_summary(r, d["DEMO-NARRATIVE"][1:], 3)
    assert s["tried"] == 7 and s["se"] == pytest.approx(1 / s["n"] ** 0.5)
    rc = rd.rolling_corr(r, d["DEMO-NARRATIVE"][1:], 20)
    assert len(rc) == len(r) and rc[0] is None
    assert rd.divergence_points([1, 2, 3, 4], [0, 1, 0, -1], lookback=2, mom=1)[0]["type"] == "price_high_narrative_fading"


def test_price_threshold_boundary_ge_and_strictly_after_registration():
    d = _data()
    reg, due = D(10), D(40)
    peak = max(d["DEMO-IDX"][11:41])
    assert rd.evaluate(rd.PriceThresholdThesis("DEMO-IDX", peak, due, reg), d) == rd.FALSIFIED
    assert rd.evaluate(rd.PriceThresholdThesis("DEMO-IDX", peak + 1e-9, due, reg), d) == rd.NOT_FALSIFIED
    d["DEMO-IDX"][10] = 1e9  # close ON registered_on must not count
    assert rd.evaluate(rd.PriceThresholdThesis("DEMO-IDX", peak + 1e-9, due, reg), d) == rd.NOT_FALSIFIED


def test_relative_thesis_both_outcomes():
    d = _data()
    d["DEMO-BASKET-A"] = [100.0] * 60; d["DEMO-BASKET-B"] = [100.0] * 60
    d["DEMO-BENCH"] = [100.0] * 59 + [101.0]
    t = rd.RelativeThesis(("DEMO-BASKET-A", "DEMO-BASKET-B"), "DEMO-BENCH", D(5), D(59), D(5))
    assert rd.evaluate(t, d) == rd.NOT_FALSIFIED
    d["DEMO-BASKET-A"] = [100.0] * 59 + [103.0]
    assert rd.evaluate(t, d) == rd.FALSIFIED


def test_window_before_registration_and_empty_basket_rejected():
    with pytest.raises(rd.ReflexivityDemoError, match="登记日"):
        rd.RelativeThesis(("DEMO-BASKET-A",), "DEMO-BENCH", D(4), D(20), D(5))
    with pytest.raises(rd.ReflexivityDemoError, match="篮子不能为空"):
        rd.RelativeThesis((), "DEMO-BENCH", D(5), D(20), D(5))
    with pytest.raises(rd.ReflexivityDemoError, match="到期日"):
        rd.PriceThresholdThesis("DEMO-IDX", 1.0, D(5), D(5))


def test_pending_when_deadline_after_data():
    d = _data()
    assert rd.evaluate(rd.PriceThresholdThesis("DEMO-IDX", 1e9, D(80), D(10)), d) == rd.PENDING
    t = rd.RelativeThesis(("DEMO-BASKET-A",), "DEMO-BENCH", D(10), D(80), D(10))
    assert rd.evaluate(t, d) == rd.PENDING
    # already hit before deadline -> falsified even if deadline is in the future
    assert rd.evaluate(rd.PriceThresholdThesis("DEMO-IDX", 1e-9, D(80), D(10)), d) == rd.FALSIFIED


def test_thesis_immutable():
    t = rd.PriceThresholdThesis("DEMO-IDX", 120.0, D(50), D(1))
    with pytest.raises(dataclasses.FrozenInstanceError):
        t.threshold = 999.0
    r = rd.RelativeThesis(("DEMO-BASKET-A",), "DEMO-BENCH", D(1), D(30), D(1))
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.end = D(300)
    with pytest.raises(dataclasses.FrozenInstanceError):
        r.registered_on = D(0)


def test_example_theses_use_only_pre_registration_data():
    d = rd.generate_demo_data(42, market_key="us")
    t1, t2 = rd.example_theses(d)
    i = d["dates"].index(t1.registered_on)
    d2 = {**d, "DEMO-IDX": d["DEMO-IDX"][:i + 1] + [x * 3 for x in d["DEMO-IDX"][i + 1:]]}
    assert rd.example_theses(d2) == (t1, t2)  # future data does not move parameters
    assert t1.threshold == round(d["DEMO-IDX"][i] * rd.PRICE_FACTOR, 2)
    assert t2.start >= t2.registered_on


def test_causality_no_future_data():
    d = rd.generate_demo_data(42, market_key="demo")
    k = 150
    base = [p for p in rd.divergence_points(d["DEMO-IDX"], d["DEMO-NARRATIVE"]) if p["t"] <= k]
    px = d["DEMO-IDX"][:k + 1] + [x * 5 for x in d["DEMO-IDX"][k + 1:]]
    nr = d["DEMO-NARRATIVE"][:k + 1] + [-x for x in d["DEMO-NARRATIVE"][k + 1:]]
    assert [p for p in rd.divergence_points(px, nr) if p["t"] <= k] == base
    t = rd.PriceThresholdThesis("DEMO-IDX", d["DEMO-IDX"][100] * 1.02, D(k), D(100))
    r = rd.RelativeThesis(("DEMO-BASKET-A", "DEMO-BASKET-B"), "DEMO-BENCH", D(100), D(k), D(100))
    before = (rd.evaluate(t, d), rd.evaluate(r, d))
    d2 = dict(d)
    for s in ("DEMO-IDX", "DEMO-BASKET-A", "DEMO-BASKET-B", "DEMO-BENCH"):
        d2[s] = d[s][:k + 1] + [x * 9 for x in d[s][k + 1:]]
    assert (rd.evaluate(t, d2), rd.evaluate(r, d2)) == before


def test_statuses_never_say_correct():
    d = _data()
    outs = {rd.evaluate(rd.PriceThresholdThesis("DEMO-IDX", x, due, D(1)), d)
            for x, due in ((1e-9, D(50)), (1e9, D(50)), (1e9, D(99)))}
    assert outs == set(rd.STATUSES) == {"falsified", "not_falsified", "pending"}
    for o in outs:
        assert "correct" not in o and "right" not in o


@pytest.mark.parametrize("key", MARKETS)
def test_all_markets_run(key):
    d = rd.main(["--market", key])
    cfg = markets.load(key)
    for name in d["meta"]:
        assert rd.series_meta(d, name) == {"market": key, "currency": cfg["currency"], "tz": cfg["tz"]}


def test_market_errors_in_chinese(monkeypatch):
    with pytest.raises(rd.ReflexivityDemoError, match="未知市场"):
        rd.generate_demo_data(1, market_key="rates")
    with pytest.raises(rd.ReflexivityDemoError, match="缺少必填字段"):
        rd.generate_demo_data(1, market={"market": "cn_a", "currency": "CNY"})
    with pytest.raises(rd.ReflexivityDemoError, match="请传入"):
        rd.generate_demo_data(1)
    d = rd.generate_demo_data(1, market_key="us")
    d["meta"]["DEMO-BENCH"] = rd.load_market("hk")
    with pytest.raises(rd.ReflexivityDemoError, match="同一市场"):
        rd.evaluate(rd.RelativeThesis(("DEMO-BASKET-A",), "DEMO-BENCH", D(1), D(9), D(1)), d)
    with pytest.raises(rd.ReflexivityDemoError, match="找不到序列"):
        rd.evaluate(rd.PriceThresholdThesis("NOPE", 1.0, D(9), D(1)), d)
    monkeypatch.setitem(sys.modules, "markets", None)
    with pytest.raises(rd.ReflexivityDemoError, match="请先合并 #5"):
        rd.load_market("us")


def test_cli_report_wording(capsys):
    rd.main(["--market", "us", "--seed", "3"])
    out = capsys.readouterr().out
    assert "被证伪" in out and "未被证伪 ≠ 我对了" in out and "试了 11 个滞后" in out
    assert "market: us" in out and "America/New_York" in out
    assert "correct" not in out.lower()
    with pytest.raises(SystemExit):
        rd.main(["--market", "rates"])


# ---- 复审反例：每条都能让论点躲掉证伪 ----
DT = dt.date


def _rel(**kw):
    base = dict(basket=("DEMO-A", "DEMO-B"), benchmark="DEMO-BENCH",
                start=DT(2026, 3, 1), end=DT(2026, 4, 1), registered_on=DT(2026, 2, 1))
    base.update(kw)
    return rd.RelativeThesis(**base)


@pytest.mark.parametrize("basket,bench", [(("DEMO-BENCH",), "DEMO-BENCH"),
                                          (("DEMO-A", "DEMO-BENCH"), "DEMO-BENCH"),
                                          (("DEMO-A", "DEMO-A"), "DEMO-BENCH")])
def test_benchmark_in_basket_or_duplicates_rejected(basket, bench):
    with pytest.raises(rd.ReflexivityDemoError):
        _rel(basket=basket, benchmark=bench)


@pytest.mark.parametrize("t", [float("nan"), float("inf"), -1.0, 0.0, True, "100"])
def test_threshold_must_be_finite_positive(t):
    with pytest.raises(rd.ReflexivityDemoError, match="门槛"):
        rd.PriceThresholdThesis("DEMO-A", t, DT(2026, 5, 1), DT(2026, 4, 1))


def test_list_basket_frozen_after_registration():
    b = ["DEMO-A", "DEMO-B"]
    th = _rel(basket=b)
    b.append("DEMO-BENCH")
    assert th.basket == ("DEMO-A", "DEMO-B")
    with pytest.raises(rd.ReflexivityDemoError):
        _rel(basket=("DEMO-A", 3))
    with pytest.raises(rd.ReflexivityDemoError):
        _rel(basket="DEMO-A")


def test_datetime_rejected_in_chinese():
    with pytest.raises(rd.ReflexivityDemoError, match="datetime.date"):
        rd.PriceThresholdThesis("DEMO-A", 1.0, dt.datetime(2026, 5, 1), DT(2026, 4, 1))
    with pytest.raises(rd.ReflexivityDemoError, match="datetime.date"):
        _rel(registered_on=dt.datetime(2026, 2, 1))


@pytest.mark.parametrize("field,bad", [("currency", "XXX"), ("tz", "UTC")])
def test_market_dict_checked_against_config(field, bad):
    good = rd.load_market("cn_a")
    rd.generate_demo_data(market=good, n=20)
    with pytest.raises(rd.ReflexivityDemoError, match=field):
        rd.generate_demo_data(market={**good, field: bad}, n=20)
