"""Margin-of-safety demo. 示例数据，不构成建议 (example data only, not advice).

Normalised-earnings valuation: value = normal_profit * fair_pe.
All companies and numbers below are FICTIONAL example data.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Company:
    name: str
    price: float
    shares: float          # shares outstanding
    last_q_profit: float   # most recent quarter net profit
    ttm_profit: float      # trailing-twelve-month net profit
    ocf_ttm: float         # trailing operating cash flow
    market: str = "cn_a"   # cn_a / hk / us (Code schema enum) 只影响默认PE区间和货币标签


def normal_profit(c: Company, haircut: float = 0.5) -> float:
    """Conservative 'normal' profit: min(TTM, haircut * last quarter annualised)."""
    if not 0 < haircut <= 1:
        raise ValueError("haircut must be in (0, 1]")
    return min(c.ttm_profit, c.last_q_profit * 4 * haircut)


# 示例参数，不是结论：不同市场的“合理PE”区间。可按自己的判断覆盖。
MARKETS = {
    "cn_a": {"currency": "CNY", "pe": (15, 18)},
    "hk": {"currency": "HKD", "pe": (10, 13)},
    "us": {"currency": "USD", "pe": (15, 20)},
}


def _market(c: Company) -> dict:
    """未登记的市场直接报错，不悄悄套用A股参数。无现金流资产(crypto/futures/fx)不该进估值。"""
    if c.market not in MARKETS:
        raise ValueError(f"市场 {c.market!r} 没有估值参数；无现金流资产请勿调用本模块")
    return MARKETS[c.market]


def fair_value_band(c: Company, pe_low: float | None = None, pe_high: float | None = None,
                    haircut: float = 0.5) -> tuple[float, float]:
    """价值 = 正常每股利润 x 合理PE。没给PE就用该市场的示例区间。"""
    d = _market(c)["pe"]
    pe_low = d[0] if pe_low is None else pe_low
    pe_high = d[1] if pe_high is None else pe_high
    if not 0 < pe_low <= pe_high:
        raise ValueError(f"PE 区间必须满足 0 < pe_low <= pe_high，收到 ({pe_low}, {pe_high})")
    if c.shares <= 0:
        raise ValueError("股本 shares 必须大于 0")
    eps = normal_profit(c, haircut) / c.shares
    return eps * pe_low, eps * pe_high


MAX_SWING = 2.0  # 年化季度利润与 TTM 之比超过 2 倍（任一方向）就算看不懂


def too_hard(c: Company) -> bool:
    """亏损、零利润，或季度年化与 TTM 相差超过 MAX_SWING 倍（两个方向都拦）。"""
    a, t = c.last_q_profit * 4, c.ttm_profit
    if a <= 0 or t <= 0:
        return True
    return max(a, t) / min(a, t) > MAX_SWING


def cash_quality(c: Company) -> float:
    """Operating cash flow / TTM profit. <0.5 means profit not yet collected."""
    return c.ocf_ttm / c.ttm_profit if c.ttm_profit else float("nan")


def verdict(c: Company, **kw) -> dict:
    if c.price <= 0:
        raise ValueError("价格 price 必须大于 0")
    m = _market(c)
    base = {"name": c.name, "market": c.market, "currency": m["currency"]}
    if too_hard(c):  # 进筐就不给估值区间，也不给倍数
        call = "too hard pile"
        return {**base, "band": None, "premium_to_band_top": None, "cash_quality": None,
                "call": call, "note": NOTES[call]}
    lo, hi = fair_value_band(c, **kw)
    gap = c.price / hi - 1
    q = cash_quality(c)
    if c.price <= lo and q >= 0.5:
        call = "margin of safety"
    elif c.price <= hi:
        call = "fair, no margin"
    else:
        call = "expensive"
    return {**base, "band": (round(lo, 2), round(hi, 2)),
            "premium_to_band_top": round(gap, 3), "cash_quality": round(q, 2),
            "call": call, "note": NOTES[call]}


NOTES = {
    "margin of safety": "市场先生今天报了个低价，而且利润真收到了现金。可以研究，不是命令。",
    "fair, no margin": "价格合理不等于便宜。没有安全边际，就等。",
    "expensive": "好公司也可能是坏买卖。价格是你付出的，价值是你得到的。",
    "too hard pile": "利润波动太大、亏损或根本没有利润（如亏损股）。没有现金流就没有内在价值可算，放进“太难”筐。",
}


EXAMPLE = [
    Company("DEMO-A (fictional)", price=150, shares=10, last_q_profit=30, ttm_profit=90, ocf_ttm=20),
    Company("DEMO-B (fictional)", price=25, shares=10, last_q_profit=10, ttm_profit=35, ocf_ttm=30),
    Company("DEMO-HK (fictional)", price=20, shares=10, last_q_profit=10, ttm_profit=36, ocf_ttm=30, market="hk"),
    Company("DEMO-LOSS (fictional, no earnings)", price=50, shares=10, last_q_profit=0, ttm_profit=0, ocf_ttm=0, market="us"),
]

if __name__ == "__main__":
    print("示例数据，不构成建议。")
    for c in EXAMPLE:
        print(verdict(c))
