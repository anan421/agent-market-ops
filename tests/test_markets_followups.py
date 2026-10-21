import json
import re
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")
import markets
from scripts import gen_market_enum as gen
from scripts import validate_demo as vd

ROOT = Path(__file__).resolve().parents[1]
GOOD = {"symbol": "DEMO1", "market": "cn_a", "currency": "CNY", "tz": "Asia/Shanghai", "date": "2026-10-19",
        "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 1, "synthetic": True}


def test_good_bar_passes():
    vd.check_bar(GOOD)


def test_wrong_currency_only():
    with pytest.raises(ValueError, match="currency"):
        vd.check_bar({**GOOD, "currency": "USD"})


def test_wrong_tz_only():
    with pytest.raises(ValueError, match="tz"):
        vd.check_bar({**GOOD, "tz": "UTC"})


def test_enum_is_generated_and_current():
    assert gen.main(["--check"]) == 0
    enum = json.loads((ROOT / "schema/price_bar.schema.json").read_text(encoding="utf-8"))["properties"]["market"]["enum"]
    assert enum == markets.available()


def test_check_detects_drift(monkeypatch):
    monkeypatch.setattr(markets, "available", lambda: markets.available()[:-1])
    assert gen.main(["--check"]) == 1


CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


@pytest.mark.parametrize("name", markets.available())
def test_display_name_zh(name):
    zh = markets.load(name)["display_name_zh"]
    assert isinstance(zh, str) and zh.strip()
    assert CJK.search(zh), f"{name}: display_name_zh {zh!r} has no CJK character"


def test_display_name_zh_required():
    s = json.loads((ROOT / "schema/market_config.schema.json").read_text(encoding="utf-8"))
    cfg = {k: v for k, v in markets.load("us").items() if k != "display_name_zh"}
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(cfg, s)
