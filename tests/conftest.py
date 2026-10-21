"""Test-only: inject the stub `markets` adapter until PR #5 is merged."""
import importlib.util
import pathlib
import sys

import pytest

_STUB = pathlib.Path(__file__).parent / "fixtures" / "markets" / "__init__.py"


def _load_stub():
    spec = importlib.util.spec_from_file_location("markets", _STUB)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(autouse=True)
def stub_markets(monkeypatch):
    stub = _load_stub()
    monkeypatch.setitem(sys.modules, "markets", stub)
    return stub
