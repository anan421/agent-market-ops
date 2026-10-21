"""Per-market config loader (stdlib only). Configs live next to this file as <name>.json."""
from __future__ import annotations
import json
import re
from pathlib import Path

_DIR = Path(__file__).resolve().parent


class UnknownMarketError(KeyError):
    def __str__(self) -> str:
        return self.args[0]


def available() -> list[str]:
    return sorted(p.stem for p in _DIR.glob("*.json"))


def load(name: str) -> dict:
    if not isinstance(name, str) or not re.fullmatch(r"[a-z_]+", name) or name not in available():
        raise UnknownMarketError(f"未登记的市场：{name}。可选：{', '.join(available())}")
    return json.loads((_DIR / f"{name}.json").read_text(encoding="utf-8"))
