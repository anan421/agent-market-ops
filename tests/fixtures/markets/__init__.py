"""TEST-ONLY stub of the repo `markets/` adapter (PR #5). DO NOT COMMIT as the real package.
Injected via tests/conftest.py monkeypatch; mirrors load()/available()/UnknownMarketError."""
_CFG = {
    "cn_a": {"currency": "CNY", "tz": "Asia/Shanghai", "periods_per_year": 244, "has_cashflow": True},
    "hk": {"currency": "HKD", "tz": "Asia/Hong_Kong", "periods_per_year": 247, "has_cashflow": True},
    "us": {"currency": "USD", "tz": "America/New_York", "periods_per_year": 252, "has_cashflow": True},
    "crypto": {"currency": "USD", "tz": "UTC", "periods_per_year": 365, "has_cashflow": False},
    "futures": {"currency": "CNY", "tz": "Asia/Shanghai", "periods_per_year": 244, "has_cashflow": False},
    "fx": {"currency": "USD", "tz": "UTC", "periods_per_year": 260, "has_cashflow": False},
    "demo": {"currency": "DEMO", "tz": "UTC", "periods_per_year": 252, "has_cashflow": False},
}


class UnknownMarketError(LookupError):
    pass


def available():
    return list(_CFG)


def load(name):
    if name not in _CFG:
        raise UnknownMarketError(name)
    return dict(_CFG[name])
