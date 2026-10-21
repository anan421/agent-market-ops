import json
import os
from pathlib import Path
import pytest
jsonschema = pytest.importorskip("jsonschema")
import markets

ROOT = Path(__file__).resolve().parents[1]
S = lambda n: json.loads((ROOT / "schema" / n).read_text(encoding="utf-8"))
ENUM = S("price_bar.schema.json")["properties"]["market"]["enum"]
PPY = {"cn_a": 242, "hk": 246, "us": 252, "crypto": 365, "futures": 242, "fx": 260, "demo": 252}
TARGET = [os.environ["AMO_MARKET"]] if os.environ.get("AMO_MARKET") else markets.available()


def test_enum_matches_configs():
    assert sorted(ENUM) == markets.available()
    assert set(ENUM) == {"cn_a", "hk", "us", "crypto", "futures", "fx", "demo"}


@pytest.mark.parametrize("name", TARGET)
def test_config_valid(name):
    cfg = markets.load(name)
    jsonschema.validate(cfg, S("market_config.schema.json"))
    assert cfg["name"] == name
    assert cfg["periods_per_year"] == PPY[name]


def test_unknown_market_friendly():
    with pytest.raises(markets.UnknownMarketError, match="未登记的市场：mars。可选：.*cn_a"):
        markets.load("mars")


def test_bad_config_rejected():
    cfg = {**markets.load("us"), "periods_per_year": 2.5}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(cfg, S("market_config.schema.json"))
    cfg = {k: v for k, v in markets.load("us").items() if k != "settlement"}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(cfg, S("market_config.schema.json"))


@pytest.mark.parametrize("bad", ["../schema/price_bar.schema", "us/../hk", "", "US"])
def test_path_traversal_rejected(bad):
    with pytest.raises(markets.UnknownMarketError):
        markets.load(bad)


def test_cashflow_constraint():
    s = S("market_config.schema.json")
    for ac in ("crypto", "commodity", "fx"):
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate({**markets.load("us"), "asset_class": ac, "has_cashflow": True}, s)
    jsonschema.validate({**markets.load("us"), "asset_class": "equity", "has_cashflow": True}, s)
    assert markets.load("fx")["asset_class"] == "fx"
    d = markets.load("demo")
    assert d["asset_class"] == "equity" and d["has_cashflow"] is True


@pytest.mark.parametrize("name", TARGET)
def test_example_values_flagged(name):
    assert markets.load(name)["example_values"] is True


def test_every_market_has_demo_bars():
    from scripts import validate_demo as vd
    seen = {b["market"] for b in vd.bar_rows(ROOT / "examples/demo/price_bars.csv")}
    assert seen == set(markets.available())


def test_currency_tz_mismatch_rejected():
    from scripts import validate_demo as vd
    bar = {"symbol": "DEMO1", "market": "cn_a", "currency": "USD", "tz": "UTC", "date": "2026-10-19",
           "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 1, "synthetic": True}
    with pytest.raises(ValueError, match="currency"):
        vd.check_bar(bar)
    vd.check_bar({**bar, "currency": "CNY", "tz": "Asia/Shanghai"})


def test_zero_rows_fails(monkeypatch, tmp_path):
    from scripts import validate_demo as vd
    monkeypatch.delenv("AMO_MARKET", raising=False)
    real = vd.bar_rows
    monkeypatch.setattr(vd, "bar_rows", lambda p: (b for b in real(p) if b["market"] != "hk"))
    assert vd.main() == 1
