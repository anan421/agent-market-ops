"""Validate demo data files against JSON schemas. Exit 1 on any failure."""
from __future__ import annotations
import csv, json, sys
from pathlib import Path
import jsonschema

ROOT = Path(__file__).resolve().parents[1]

def schema(name): return json.loads((ROOT / "schema" / name).read_text(encoding="utf-8"))

def bar_rows(path):
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            yield {"symbol": r["symbol"], "date": r["date"], **{k: float(r[k]) for k in ("open","high","low","close")},
                   "volume": int(r["volume"]), "synthetic": r["synthetic"].lower() == "true"}

def check_bar(b):
    jsonschema.validate(b, schema("price_bar.schema.json"))
    if not (b["low"] <= min(b["open"], b["close"]) and b["high"] >= max(b["open"], b["close"])):
        raise ValueError(f"OHLC inconsistent: {b}")

def main() -> int:
    errors = 0
    for b in bar_rows(ROOT / "examples/demo/price_bars.csv"):
        try: check_bar(b)
        except Exception as e: errors += 1; print("FAIL", e)
    for a in json.loads((ROOT / "examples/demo/brief_actions.json").read_text(encoding="utf-8")):
        try: jsonschema.validate(a, schema("brief_action.schema.json"))
        except Exception as e: errors += 1; print("FAIL", e)
    print("OK" if not errors else f"{errors} error(s)")
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main())
