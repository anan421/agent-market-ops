"""Per-market config loader (stdlib only). Configs live next to this file as <name>.json."""
from __future__ import annotations
import json
from pathlib import Path

_DIR = Path(__file__).resolve().parent


class UnknownMarketError(KeyError):
    def __str__(self) -> str:
        return self.args[0]


def available() -> list[str]:
    return sorted(p.stem for p in _DIR.glob("*.json"))


def load(name: str) -> dict:
    path = _DIR / f"{name}.json"
    if not name or not path.is_file():
        raise UnknownMarketError(f"unknown market {name!r}; available: {', '.join(available())}")
    return json.loads(path.read_text(encoding="utf-8"))
