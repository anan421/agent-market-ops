"""Validate demo data files against JSON schemas. Exit 1 on any failure."""
from __future__ import annotations
import csv, json, sys
from pathlib import Path
import jsonschema

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def schema(name): return json.loads((ROOT / "schema" / name).read_text(encoding="utf-8"))

def bar_rows(path):
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            yield {**{k: r[k] for k in ("symbol","market","currency","tz","date")}, **{k: float(r[k]) for k in ("open","high","low","close")},
                   "volume": int(r["volume"]), "synthetic": r["synthetic"].lower() == "true"}

def check_bar(b, cfg=None):
    jsonschema.validate(b, schema("price_bar.schema.json"))
    if cfg is None:
        import markets
        cfg = markets.load(b["market"])
    for k in ("currency", "tz"):
        if b[k] != cfg[k]:
            raise ValueError(f"{b['symbol']} {b['date']}: {k}={b[k]!r} != market {b['market']} {k}={cfg[k]!r}")
    if not (b["low"] <= min(b["open"], b["close"]) and b["high"] >= max(b["open"], b["close"])):
        raise ValueError(f"OHLC inconsistent: {b}")

def main() -> int:
    import os, markets
    errors = 0
    only = os.environ.get("AMO_MARKET")
    targets = [only] if only else markets.available()
    counts = {n: 0 for n in targets}
    for name in targets:
        try:
            jsonschema.validate(markets.load(name), schema("market_config.schema.json"))
        except Exception as e:
            errors += 1; print("FAIL market", name, e)
    for b in bar_rows(ROOT / "examples/demo/price_bars.csv"):
        if only and b["market"] != only: continue
        counts[b["market"]] = counts.get(b["market"], 0) + 1
        try: check_bar(b)
        except Exception as e: errors += 1; print("FAIL", e)
    for name, n in counts.items():
        if n == 0:
            errors += 1; print("FAIL market", name, "has 0 demo bars")
    for a in json.loads((ROOT / "examples/demo/brief_actions.json").read_text(encoding="utf-8")):
        try: jsonschema.validate(a, schema("brief_action.schema.json"))
        except Exception as e: errors += 1; print("FAIL", e)
    print("OK" if not errors else f"{errors} error(s)")
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main())
