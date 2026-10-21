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
    with pytest.raises(markets.UnknownMarketError, match="available: .*cn_a"):
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
