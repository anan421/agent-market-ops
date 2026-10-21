"""Lint a markdown daily brief for locked action phrases (demo).

Rules (educational):
  - Markdown fences must be balanced (even count of ``` lines).
  - At least one fenced ```action block must exist (and be closed).
  - If the action says 「今天不做」 (no-trade day), the brief must not
    contain a fenced ```picks block with data rows.

    python -m pipeline.brief_check_demo examples/brief.md
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

FENCE_LINE = re.compile(r"^\s*```")
ACTION_BLOCK = re.compile(r"```action\s*\n(.*?)```", re.S | re.I)
ACTION_OPEN = re.compile(r"```action\b", re.I)
PICKS_BLOCK = re.compile(r"```picks\s*\n(.*?)```", re.S | re.I)
NO_TRADE = re.compile(r"今天不做")


def fences_unclosed(text: str) -> bool:
    n = sum(1 for ln in text.splitlines() if FENCE_LINE.match(ln))
    return n % 2 == 1


def parse_actions(text: str) -> list[str]:
    return [m.group(1).strip() for m in ACTION_BLOCK.finditer(text or "")]


def is_no_trade_day(text: str) -> bool:
    bodies = parse_actions(text)
    if not bodies:
        return False
    return any(NO_TRADE.search(b) for b in bodies)


def picks_nonempty(text: str) -> bool:
    for m in PICKS_BLOCK.finditer(text or ""):
        body = m.group(1).strip()
        rows = [ln for ln in body.splitlines() if ln.strip() and not ln.strip().startswith("#")]
        if rows:
            return True
    return False


def check_brief_text(text: str) -> tuple[bool, str]:
    text = text or ""
    # Fence balance first so an unclosed ```action is reported clearly.
    if fences_unclosed(text):
        return False, "unclosed markdown fence"
    actions = parse_actions(text)
    if not actions:
        if ACTION_OPEN.search(text):
            return False, "unclosed markdown fence"
        return False, "missing ```action block"
    if is_no_trade_day(text) and picks_nonempty(text):
        return False, "今天不做 day must not carry a non-empty ```picks block"
    return True, "OK"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("path", type=Path, help="path to brief markdown")
    args = p.parse_args(argv)
    text = args.path.read_text(encoding="utf-8")
    ok, msg = check_brief_text(text)
    if ok:
        print(msg)
        return 0
    print(msg, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
