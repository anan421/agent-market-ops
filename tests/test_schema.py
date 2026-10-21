import csv
import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schema"


def _load(name: str) -> dict:
    return json.loads((SCHEMA / name).read_text(encoding="utf-8"))


def test_post_schema_accepts_demo_row():
    schema = _load("post.schema.json")
    row = {
        "id": "demo:post:001",
        "source_id": "demo_feed",
        "url": None,
        "published_at": "2026-10-21T08:00:00+08:00",
        "collected_at": "2026-10-21T08:05:00+08:00",
        "text": "hello demo",
        "tier": "T3",
        "tags": ["demo"],
        "synthetic": True,
    }
    jsonschema.validate(row, schema)


def test_filing_schema_accepts_demo_row():
    schema = _load("filing.schema.json")
    row = {
        "id": "demo:filing:001",
        "source_id": "demo_exchange",
        "title": "Demo clarification",
        "url": "https://example.com/filing",
        "published_at": "2026-10-21",
        "published_at_precision": "date",
        "ticker": "DEMO01",
        "category": "clarification",
        "text_excerpt": "no material matter",
        "synthetic": True,
    }
    jsonschema.validate(row, schema)


def test_ledger_csv_rows_match_schema():
    schema = _load("ledger_row.schema.json")
    path = ROOT / "examples" / "ledger.csv"
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            obj = {
                "date": row["date"],
                "account": row["account"],
                "action": row["action"],
                "symbol": row["symbol"] or None,
                "qty": float(row["qty"]) if row["qty"] else None,
                "pnl_pct": float(row["pnl_pct"]),
                "note": row["note"],
                "synthetic": row["synthetic"].lower() == "true",
            }
            jsonschema.validate(obj, schema)


def test_reconcile_summary_schema():
    from pipeline.reconcile_demo import sample_summary

    schema = _load("reconcile_summary.schema.json")
    jsonschema.validate(sample_summary("2026-10-21"), schema)


def test_synthetic_prices_shape():
    from datetime import date

    from pipeline.fetch_prices_demo import synthetic_ohlcv

    rows = synthetic_ohlcv("DEMO01", date(2026, 10, 14), 3)
    assert len(rows) == 3
    assert rows[0]["synthetic"] is True
    assert rows[0]["close"] > 0
