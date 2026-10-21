"""Synthetic OHLCV generator for demos (no network).

    python -m pipeline.fetch_prices_demo --symbol DEMO01 --days 5
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from datetime import date, timedelta
from pathlib import Path


def _seed(symbol: str) -> int:
    return int(hashlib.sha256(symbol.encode()).hexdigest()[:8], 16)


def synthetic_ohlcv(
    symbol: str,
    start: date,
    days: int,
    start_price: float = 100.0,
) -> list[dict]:
    """Deterministic fake daily bars. Weekends skipped (simple Mon–Fri)."""
    rng = _seed(symbol)
    rows: list[dict] = []
    px = start_price
    d = start
    while len(rows) < days:
        if d.weekday() < 5:
            # cheap LCG
            rng = (1103515245 * rng + 12345) & 0x7FFFFFFF
            shock = ((rng % 2001) - 1000) / 100000.0  # ±1%
            o = px
            c = max(0.01, px * (1.0 + shock))
            h = max(o, c) * (1.0 + abs(shock) * 0.5)
            l = min(o, c) * (1.0 - abs(shock) * 0.5)
            vol = 1_000_000 + (rng % 500_000)
            rows.append(
                {
                    "date": d.isoformat(),
                    "symbol": symbol,
                    "open": round(o, 4),
                    "high": round(h, 4),
                    "low": round(l, 4),
                    "close": round(c, 4),
                    "volume": vol,
                    "synthetic": True,
                }
            )
            px = c
        d += timedelta(days=1)
    return rows


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--symbol", default="DEMO01")
    p.add_argument("--days", type=int, default=5)
    p.add_argument("--start", default="2026-10-14", help="YYYY-MM-DD")
    p.add_argument("--format", choices=("json", "csv"), default="json")
    p.add_argument("-o", "--output", type=Path, default=None)
    args = p.parse_args(argv)

    start = date.fromisoformat(args.start)
    rows = synthetic_ohlcv(args.symbol, start, args.days)

    if args.format == "json":
        text = json.dumps(rows, ensure_ascii=False, indent=2)
    else:
        buf = []
        w = csv.DictWriter(
            _ListWriter(buf),
            fieldnames=["date", "symbol", "open", "high", "low", "close", "volume", "synthetic"],
        )
        w.writeheader()
        w.writerows(rows)
        text = "".join(buf)

    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")
    return 0


class _ListWriter:
    def __init__(self, buf: list[str]) -> None:
        self.buf = buf

    def write(self, s: str) -> int:
        self.buf.append(s)
        return len(s)


if __name__ == "__main__":
    raise SystemExit(main())
