"""Reflexivity / bias turning-point demo  反射性 / 偏差拐点 示例

示例数据，不构成建议。 Synthetic example data only; not investment advice.

给新手的 30 秒解释 / Reflexivity for beginners
-------------------------------------------
教科书说：价格反映基本面。反射性说：价格和人们的看法互相推动。
  1. 价格涨 -> 大家更相信故事（叙事升温）;
  2. 故事更热 -> 更多人买 -> 价格继续涨;
  3. 循环自我强化，直到看法和现实差得太远，循环反转（拐点）。
Textbook view: prices reflect fundamentals. Reflexive view: prices and beliefs
push each other in a loop that self-reinforces until the gap ("bias") between
belief and reality gets too wide, then it reverses.

本模块教你三件事 / What this module shows:
  * 量循环有多强：滚动相关 + 领先滞后（谁先动）/ measure the loop: rolling corr + lead-lag.
  * 找候选拐点：价格创新高但叙事动量走弱（或反之）/ flag price-narrative divergence.
  * 事先登记证伪条件：只回答"被证伪/未被证伪"，从不说"我对了"
    / pre-register how you could be wrong; output is only falsified / not_falsified.

All series (DEMO-IDX, DEMO-BASKET-*, DEMO-BENCH, DEMO-NARRATIVE) are fictional,
generated from a fixed random seed. Each series carries market/currency/tz fields;
logic reads the market only from those fields. Pure stdlib, no network.
"""
from __future__ import annotations

import datetime as _dt
import math
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

DISCLAIMER = "示例数据，不构成建议 / synthetic demo data, not advice"
FALSIFIED = "falsified"
NOT_FALSIFIED = "not_falsified"
START = _dt.date(2000, 1, 3)

ALLOWED_MARKETS = ("cn_a", "hk", "us", "crypto", "futures", "fx", "demo")
# Display labels for the report only; the `market` field always holds the enum value.
MARKET_LABEL_ZH = {"cn_a": "A股", "hk": "港股", "us": "美股", "crypto": "加密",
                   "futures": "期货", "fx": "外汇", "demo": "演示"}
# CLI convenience only; logic reads market from each series' fields, never from codes.
MARKET_PRESETS = {
    "cn_a": {"market": "cn_a", "currency": "CNY", "tz": "Asia/Shanghai"},
    "hk": {"market": "hk", "currency": "HKD", "tz": "Asia/Hong_Kong"},
    "us": {"market": "us", "currency": "USD", "tz": "America/New_York"},
    "crypto": {"market": "crypto", "currency": "USD", "tz": "UTC"},
    "futures": {"market": "futures", "currency": "CNY", "tz": "Asia/Shanghai"},
    "fx": {"market": "fx", "currency": "USD", "tz": "UTC"},
    "demo": {"market": "demo", "currency": "DEMO", "tz": "UTC"},
}
REQUIRED_FIELDS = ("market", "currency", "tz")


def validate_meta(meta: Dict[str, str]) -> Dict[str, str]:
    for f in REQUIRED_FIELDS:
        if not meta.get(f):
            raise ValueError(f"missing required field: {f}")
    if meta["market"] not in ALLOWED_MARKETS:
        raise ValueError(f"unknown market: {meta['market']}")
    return dict(meta)


def series_meta(data: Dict[str, object], name: str) -> Dict[str, str]:
    """Market/currency/tz come only from the series' own fields."""
    return validate_meta(data["meta"][name])


def generate_demo_data(seed: int = 42, n: int = 250, market: Optional[Dict[str, str]] = None,
                       market_key: Optional[str] = None) -> Dict[str, object]:
    """Synthetic price + narrative with a built-in feedback loop.

    Narrative chases past returns; price drift is pushed by narrative (reflexive loop).
    """
    rng = random.Random(seed)
    dates = [START + _dt.timedelta(days=i) for i in range(n)]
    idx, narr = [100.0], [0.0]
    for t in range(1, n):
        ret_prev = idx[-1] / idx[-2] - 1 if t > 1 else 0.0
        cycle = math.sin(2 * math.pi * t / 120)
        s = 0.8 * narr[-1] + 6.0 * ret_prev + 0.15 * cycle + rng.gauss(0, 0.1)
        narr.append(s)
        r = 0.002 * narr[-2] + rng.gauss(0, 0.01)
        idx.append(idx[-1] * (1 + r))

    def walk(mu: float, sd: float) -> List[float]:
        p = [100.0]
        for _ in range(n - 1):
            p.append(p[-1] * (1 + rng.gauss(mu, sd)))
        return p

    if market is None:
        if market_key is None:
            raise ValueError("pass market fields (market/currency/tz) or market_key")
        market = MARKET_PRESETS[market_key]
    meta = validate_meta(market)
    names = ["DEMO-IDX", "DEMO-NARRATIVE", "DEMO-BASKET-A", "DEMO-BASKET-B", "DEMO-BENCH"]
    return {
        "disclaimer": DISCLAIMER,
        "meta": {k: dict(meta) for k in names},
        "dates": dates,
        "DEMO-IDX": idx,
        "DEMO-NARRATIVE": narr,
        "DEMO-BASKET-A": walk(0.0004, 0.02),
        "DEMO-BASKET-B": walk(0.0002, 0.025),
        "DEMO-BENCH": walk(0.0003, 0.012),
    }


def returns(p: Sequence[float]) -> List[float]:
    return [p[i] / p[i - 1] - 1 for i in range(1, len(p))]


def _corr(x: Sequence[float], y: Sequence[float]) -> float:
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    return 0.0 if sxx == 0 or syy == 0 else sxy / math.sqrt(sxx * syy)


def rolling_corr(x: Sequence[float], y: Sequence[float], window: int = 20) -> List[Optional[float]]:
    out: List[Optional[float]] = [None] * min(len(x), window - 1)
    for i in range(window - 1, len(x)):
        out.append(_corr(x[i - window + 1:i + 1], y[i - window + 1:i + 1]))
    return out


def lead_lag(x: Sequence[float], y: Sequence[float], max_lag: int = 5) -> Dict[int, float]:
    """corr(x[t], y[t+lag]). Positive lag => x leads y."""
    res = {}
    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            a, b = x[:len(x) - lag], y[lag:]
        else:
            a, b = x[-lag:], y[:len(y) + lag]
        res[lag] = _corr(a, b)
    return res


def divergence_points(price: Sequence[float], narrative: Sequence[float],
                      lookback: int = 20, mom: int = 5) -> List[Dict[str, object]]:
    """Candidate turning points: price at lookback high while narrative momentum < 0
    (bearish divergence), or price at lookback low while narrative momentum > 0."""
    pts = []
    for t in range(max(lookback, mom), len(price)):
        win = price[t - lookback:t]
        m = narrative[t] - narrative[t - mom]
        if price[t] > max(win) and m < 0:
            pts.append({"t": t, "type": "price_high_narrative_fading", "narr_mom": m})
        elif price[t] < min(win) and m > 0:
            pts.append({"t": t, "type": "price_low_narrative_rising", "narr_mom": m})
    return pts


@dataclass(frozen=True)
class PriceThresholdThesis:
    """Wrong if close >= threshold on or before deadline."""
    series: str
    threshold: float
    deadline: _dt.date


@dataclass(frozen=True)
class RelativeThesis:
    """Wrong if equal-weight basket return beats benchmark over [start, end] (unadjusted closes)."""
    basket: tuple
    benchmark: str
    start: _dt.date
    end: _dt.date


def _ix(dates, d):
    return dates.index(d)


def evaluate(thesis, data: Dict[str, object]) -> str:
    """Return only 'falsified' or 'not_falsified'. Never claims the thesis is confirmed."""
    dates = data["dates"]
    if isinstance(thesis, PriceThresholdThesis):
        series_meta(data, thesis.series)
    elif isinstance(thesis, RelativeThesis):
        ms = {series_meta(data, x)["market"] for x in (*thesis.basket, thesis.benchmark)}
        if len(ms) != 1:
            raise ValueError("basket and benchmark must share one market (from fields)")
    if isinstance(thesis, PriceThresholdThesis):
        px = data[thesis.series]
        for d, c in zip(dates, px):
            if d <= thesis.deadline and c >= thesis.threshold:
                return FALSIFIED
        return NOT_FALSIFIED
    if isinstance(thesis, RelativeThesis):
        i, j = _ix(dates, thesis.start), _ix(dates, thesis.end)
        rets = [data[s][j] / data[s][i] - 1 for s in thesis.basket]
        basket = sum(rets) / len(rets)
        bench = data[thesis.benchmark][j] / data[thesis.benchmark][i] - 1
        return FALSIFIED if basket > bench else NOT_FALSIFIED
    raise TypeError("unknown thesis type")


VERDICT_ZH = {FALSIFIED: "被证伪 / falsified", NOT_FALSIFIED: "未被证伪 / not falsified"}
DIV_WHY = {
    "price_high_narrative_fading": "价格新高但叙事降温：买的人越来越少相信故事，循环可能见顶 / price new high while belief cools: loop may be topping.",
    "price_low_narrative_rising": "价格新低但叙事回暖：看法先修复，价格可能跟上 / price new low while belief recovers: loop may be bottoming.",
}


def build_report(d: Dict[str, object]) -> str:
    m = series_meta(d, "DEMO-IDX")
    dates = d["dates"]
    L = [DISCLAIMER, f"市场 market: {m['market']} ({MARKET_LABEL_ZH[m['market']]}) | 货币 currency: {m['currency']} | 时区 tz: {m['tz']}", ""]
    ll = lead_lag(returns(d["DEMO-IDX"]), d["DEMO-NARRATIVE"][1:])
    lag, c = max(ll.items(), key=lambda kv: abs(kv[1]))
    if lag > 0:
        why = f"价格领先叙事 {lag} 天：价格先动，大家再去找故事 / price leads narrative by {lag}d: price moves, then the story follows."
    elif lag < 0:
        why = f"叙事领先价格 {-lag} 天：大家先相信，价格再跟 / narrative leads price by {-lag}d: belief first, price follows."
    else:
        why = "同日最相关：价格和叙事同步 / strongest same-day: moving together."
    L += [f"[循环强度 loop strength] 峰值 lag={lag:+d}, corr={c:.3f}", "  " + why, ""]
    L.append("[最近 3 个背离点 latest 3 divergences]")
    for p in divergence_points(d["DEMO-IDX"], d["DEMO-NARRATIVE"])[-3:]:
        L.append(f"  {dates[p['t']]} {p['type']}: {DIV_WHY[p['type']]}")
    px = d["DEMO-IDX"]
    thr = round(max(px) * 1.05, 2)
    t1 = PriceThresholdThesis("DEMO-IDX", thr, dates[-1])
    t2 = RelativeThesis(("DEMO-BASKET-A", "DEMO-BASKET-B"), "DEMO-BENCH", dates[-60], dates[-1])
    v1, v2 = evaluate(t1, d), evaluate(t2, d)
    L += ["", "[示例登记论点 example registered theses]",
          f"  1) 价格阈值 price threshold: 若 DEMO-IDX 收盘 >= {thr} 于 {dates[-1]} 前则错 -> {VERDICT_ZH[v1]}",
          "     " + ("收盘碰到了阈值，论点错了 / close touched the threshold, thesis is wrong." if v1 == FALSIFIED
                     else "收盘没碰到阈值，论点暂时活着 / close never touched the threshold, thesis survives for now."),
          f"  2) 相对 relative: 若等权 DEMO-BASKET-A+B 在 {dates[-60]}~{dates[-1]} 跑赢 DEMO-BENCH 则错 -> {VERDICT_ZH[v2]}",
          "     " + ("篮子跑赢了基准（未复权收盘），论点错了 / basket beat benchmark, thesis is wrong." if v2 == FALSIFIED
                     else "篮子没跑赢基准（未复权收盘），论点暂时活着 / basket did not beat benchmark, thesis survives for now."),
          "", "未被证伪 ≠ 我对了 / not falsified is not proof"]
    return "\n".join(L)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=DISCLAIMER)
    ap.add_argument("--market", choices=list(ALLOWED_MARKETS), required=True)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args(argv)
    d = generate_demo_data(a.seed, market_key=a.market)
    print(build_report(d))
    return d


if __name__ == "__main__":
    main()
