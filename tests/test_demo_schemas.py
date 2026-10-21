import json
from pathlib import Path
import pytest
jsonschema = pytest.importorskip("jsonschema")
from scripts import validate_demo as vd

ROOT = Path(__file__).resolve().parents[1]
BAR = {"symbol": "DEMO1", "market": "us", "currency": "USD", "tz": "America/New_York", "date": "2026-10-19", "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 1, "synthetic": True}

def S(n): return json.loads((ROOT / "schema" / n).read_text(encoding="utf-8"))

def test_demo_data_validates():
    assert vd.main() == 0

def test_bar_ok():
    vd.check_bar(BAR)

@pytest.mark.parametrize("patch", [{"symbol": "AAPL"}, {"close": -1}, {"synthetic": False}, {"date": "20261019"}, {"extra": 1}, {"market": "mars"}, {"currency": "usd"}])
def test_bar_bad(patch):
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate({**BAR, **patch}, S("price_bar.schema.json"))

def test_bar_ohlc_inconsistent():
    with pytest.raises(ValueError):
        vd.check_bar({**BAR, "high": 1.0})

def test_action_ok():
    jsonschema.validate({"date": "2026-10-21", "action": "hold", "picks": ["DEMO2"]}, S("brief_action.schema.json"))

@pytest.mark.parametrize("obj", [
    {"date": "2026-10-21", "action": "今天不做", "picks": ["DEMO1"]},
    {"date": "2026-10-21", "action": "yolo", "picks": []},
    {"date": "2026-10-21", "action": "hold"},
])
def test_action_bad(obj):
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(obj, S("brief_action.schema.json"))

def test_ledger_bad_account():
    row = {"date": "2026-10-21", "account": "real", "action": "hold", "pnl_pct": 0.0}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(row, S("ledger_row.schema.json"))

@pytest.mark.parametrize("key", ["market", "currency", "tz"])
def test_bar_missing_market_fields(key):
    bad = {k: v for k, v in BAR.items() if k != key}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, S("price_bar.schema.json"))

def test_demo_covers_two_markets():
    assert len({b["market"] for b in vd.bar_rows(ROOT / "examples/demo/price_bars.csv")}) >= 2
