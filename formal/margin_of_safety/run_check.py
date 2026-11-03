#!/usr/bin/env python3
"""Cold entry: run margin_of_safety_demo Hypothesis properties."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        str(ROOT / "tests" / "test_margin_of_safety_properties.py"),
    ]
    print("running:", " ".join(cmd))
    return subprocess.call(cmd, cwd=str(ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
