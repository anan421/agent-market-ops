"""Generate the price_bar `market` enum from markets/*.json (single source of truth).

    python scripts/gen_market_enum.py          # rewrite schema/price_bar.schema.json
    python scripts/gen_market_enum.py --check  # exit 1 if the schema is out of date
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import markets  # noqa: E402

SCHEMA = ROOT / "schema" / "price_bar.schema.json"


def render() -> str:
    s = json.loads(SCHEMA.read_text(encoding="utf-8"))
    s["properties"]["market"]["enum"] = markets.available()
    s["properties"]["market"]["description"] = "Generated from markets/*.json by scripts/gen_market_enum.py; do not edit by hand"
    return json.dumps(s, ensure_ascii=False, indent=2) + "\n"


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    new = render()
    if "--check" in argv:
        if SCHEMA.read_text(encoding="utf-8") != new:
            print("price_bar market enum out of date; run: python scripts/gen_market_enum.py")
            return 1
        print("market enum: OK")
        return 0
    SCHEMA.write_text(new, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
