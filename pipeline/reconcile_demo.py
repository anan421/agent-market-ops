"""Build a sample end-of-day reconcile HTML from a summary dict (demo).

    python -m pipeline.reconcile_demo --date 2026-10-21 -o /tmp/reconcile.html
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

DISCLAIMER = (
    "Demo data only. Not investment advice. No live trading. "
    "Numbers are synthetic scaffolding for agent ops tutorials."
)


def sample_summary(date: str) -> dict:
    return {
        "date": date,
        "headline": f"Paper reconcile {date}: cash day +0.00%",
        "accounts": [
            {"name": "signal", "pnl_pct": 0.0, "status": "今天不做 / flat"},
            {"name": "view", "pnl_pct": 0.0, "status": "今天不做 / flat"},
        ],
        "trades": 0,
        "hit_rate": {
            "correct": 0,
            "judgable": 0,
            "note": "no-trade day: avoid/observe rows are not judgable in this demo rule",
        },
        "disclaimer": DISCLAIMER,
        "synthetic": True,
    }


def render_html(summary: dict) -> str:
    rows = "".join(
        "<tr>"
        f"<td>{html.escape(a['name'])}</td>"
        f"<td>{a['pnl_pct']:+.2f}%</td>"
        f"<td>{html.escape(a['status'])}</td>"
        "</tr>"
        for a in summary["accounts"]
    )
    hr = summary.get("hit_rate") or {}
    hr_line = (
        f"{hr.get('correct', 0)}/{hr.get('judgable', 0)}"
        if hr
        else "n/a"
    )
    note = html.escape(str(hr.get("note", "")))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>Reconcile {html.escape(summary['date'])}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #111; }}
    table {{ border-collapse: collapse; margin: 1rem 0; }}
    th, td {{ border: 1px solid #ccc; padding: 0.4rem 0.8rem; text-align: left; }}
    .muted {{ color: #555; font-size: 0.9rem; }}
    .badge {{ display: inline-block; background: #eef; padding: 0.15rem 0.5rem; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>{html.escape(summary['headline'])}</h1>
  <p><span class="badge">synthetic</span> trades: {summary['trades']}</p>
  <table>
    <thead><tr><th>Account</th><th>P&amp;L</th><th>Status</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <p>Hit-rate (demo): <strong>{hr_line}</strong> — {note}</p>
  <p class="muted">{html.escape(summary['disclaimer'])}</p>
</body>
</html>
"""


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--date", default="2026-10-21")
    p.add_argument("-o", "--output", type=Path, default=None)
    p.add_argument("--json", action="store_true", help="also print summary JSON")
    args = p.parse_args(argv)

    summary = sample_summary(args.date)
    doc = render_html(summary)
    if args.output:
        args.output.write_text(doc, encoding="utf-8")
    else:
        print(doc)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
