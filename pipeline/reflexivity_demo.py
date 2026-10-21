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
market configs come only from the repo's `markets/` adapter (markets.load /
markets.available); logic reads the market only from those fields. Stdlib, no network.

关键纪律 / discipline: 论点在 registered_on 当天登记，参数只用登记日及之前的数据，
评估只看登记日之后的数据；到期前只能是 pending（未到期）。
"""
from __future__ import annotations

import datetime as _dt
import importlib
import math
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Union

DISCLAIMER = "示例数据，不构成建议 / synthetic demo data, not advice"
FALSIFIED = "falsified"
NOT_FALSIFIED = "not_falsified"
PENDING = "pending"
STATUSES = (FALSIFIED, NOT_FALSIFIED, PENDING)
START = _dt.date(2000, 1, 3)
SERIES_NAMES = ("DEMO-IDX", "DEMO-NARRATIVE", "DEMO-BASKET-A", "DEMO-BASKET-B", "DEMO-BENCH")
REQUIRED_FIELDS = ("market", "currency", "tz")

# 示例论点的登记规则，事先声明，不看登记日之后的数据 / declared up front, no hindsight.
REGISTER_DAYS_BEFORE_END = 60   # registered_on = 数据末日前 60 天
PRICE_FACTOR = 1.05             # 阈值 = 登记日收盘 × 1.05
HORIZON_DAYS = 40               # 到期 / 窗口长度：登记日后 40 天
MAX_LAG = 5                     # lead-lag 试 -5..+5 共 11 个滞后


class ReflexivityDemoError(ValueError):
    """所有面向用户的错误（中文 + English）/ user-facing errors."""


# ---------- markets/ 适配层 / adapter ----------

def _markets():
    try:
        return importlib.import_module("markets")
    except ImportError as e:
        raise ReflexivityDemoError("缺少 markets/ 适配层，请先合并 #5 / missing markets/ adapter, merge #5 first") from e


def available_markets() -> List[str]:
    return list(_markets().available())


def _cfg_get(cfg, key):
    if isinstance(cfg, dict):
        return cfg.get(key)
    return getattr(cfg, key, None)


def load_market(name: str) -> Dict[str, str]:
    """Build market/currency/tz fields from markets.load(name)."""
    m = _markets()
    unknown = getattr(m, "UnknownMarketError", LookupError)
    try:
        cfg = m.load(name)
    except (unknown, KeyError) as e:
        raise ReflexivityDemoError(f"未知市场：{name}（可用：{', '.join(m.available())}）/ unknown market") from e
    meta = {"market": name, "currency": _cfg_get(cfg, "currency"), "tz": _cfg_get(cfg, "tz")}
    return validate_meta(meta)


def validate_meta(meta: Dict[str, str]) -> Dict[str, str]:
    for f in REQUIRED_FIELDS:
        if not meta.get(f):
            raise ReflexivityDemoError(f"缺少必填字段：{f} / missing required field")
    if meta["market"] not in available_markets():
        raise ReflexivityDemoError(f"未知市场：{meta['market']} / unknown market")
    return dict(meta)


def _series(data: Dict[str, object], name: str) -> List[float]:
    if name not in data or name not in data.get("meta", {}):
        raise ReflexivityDemoError(f"找不到序列：{name} / series not found")
    return data[name]


def series_meta(data: Dict[str, object], name: str) -> Dict[str, str]:
    """Market/currency/tz come only from the series' own fields."""
    _series(data, name)
    return validate_meta(data["meta"][name])


# ---------- 合成数据 / synthetic data ----------

def generate_demo_data(seed: int = 42, n: int = 250, market_key: Optional[str] = None,
                       market: Optional[Dict[str, str]] = None) -> Dict[str, object]:
    """Synthetic price + narrative with a built-in feedback loop (示例数据).

    Narrative chases past returns; price drift is pushed by narrative (reflexive loop).
    """
    if market is None:
        if market_key is None:
            raise ReflexivityDemoError("请传入 market_key 或 market 字段 / pass market_key or market fields")
        market = load_market(market_key)
    meta = validate_meta(market)
    rng = random.Random(seed)
    dates = [START + _dt.timedelta(days=i) for i in range(n)]
    idx, narr = [100.0], [0.0]
    for t in range(1, n):
        ret_prev = idx[-1] / idx[-2] - 1 if t > 1 else 0.0
        cycle = math.sin(2 * math.pi * t / 120)
        narr.append(0.8 * narr[-1] + 6.0 * ret_prev + 0.15 * cycle + rng.gauss(0, 0.1))
        idx.append(idx[-1] * (1 + 0.002 * narr[-2] + rng.gauss(0, 0.01)))

    def walk(mu: float, sd: float) -> List[float]:
        p = [100.0]
        for _ in range(n - 1):
            p.append(p[-1] * (1 + rng.gauss(mu, sd)))
        return p

    return {
        "disclaimer": DISCLAIMER,
        "meta": {k: dict(meta) for k in SERIES_NAMES},
        "dates": dates,
        "DEMO-IDX": idx,
        "DEMO-NARRATIVE": narr,
        "DEMO-BASKET-A": walk(0.0004, 0.02),
        "DEMO-BASKET-B": walk(0.0002, 0.025),
        "DEMO-BENCH": walk(0.0003, 0.012),
    }


# ---------- 反馈环 / feedback loop ----------

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


def _lag_pair(x, y, lag):
    return (x[:len(x) - lag], y[lag:]) if lag >= 0 else (x[-lag:], y[:len(y) + lag])


def lead_lag(x: Sequence[float], y: Sequence[float], max_lag: int = MAX_LAG) -> Dict[int, float]:
    """corr(x[t], y[t+lag]). Positive lag => x leads y."""
    return {lag: _corr(*_lag_pair(x, y, lag)) for lag in range(-max_lag, max_lag + 1)}


def lead_lag_summary(x, y, max_lag: int = MAX_LAG) -> Dict[str, float]:
    """Peak |corr| lag, n, approx SE = 1/sqrt(n), and corr/SE. No multiple-comparison adjustment."""
    ll = lead_lag(x, y, max_lag)
    lag, c = max(ll.items(), key=lambda kv: abs(kv[1]))
    n = len(_lag_pair(x, y, lag)[0])
    se = 1 / math.sqrt(n)
    return {"lag": lag, "corr": c, "n": n, "se": se, "z": abs(c) / se, "tried": len(ll)}


def divergence_points(price: Sequence[float], narrative: Sequence[float],
                      lookback: int = 20, mom: int = 5) -> List[Dict[str, object]]:
    """Candidate turning points, causal (uses only data up to t): price above prior
    lookback high while narrative momentum < 0, or below prior low while momentum > 0."""
    pts = []
    for t in range(max(lookback, mom), len(price)):
        win = price[t - lookback:t]
        m = narrative[t] - narrative[t - mom]
        if price[t] > max(win) and m < 0:
            pts.append({"t": t, "type": "price_high_narrative_fading", "narr_mom": m})
        elif price[t] < min(win) and m > 0:
            pts.append({"t": t, "type": "price_low_narrative_rising", "narr_mom": m})
    return pts


# ---------- 事先登记的证伪器 / pre-registered falsifier ----------

@dataclass(frozen=True)
class PriceThresholdThesis:
    """Wrong if any close in (registered_on, deadline] >= threshold."""
    series: str
    threshold: float
    deadline: _dt.date
    registered_on: _dt.date

    def __post_init__(self):
        if self.deadline <= self.registered_on:
            raise ReflexivityDemoError("到期日必须晚于登记日 / deadline must be after registered_on")


@dataclass(frozen=True)
class RelativeThesis:
    """Wrong if equal-weight basket return beats benchmark over [start, end] (unadjusted closes)."""
    basket: tuple
    benchmark: str
    start: _dt.date
    end: _dt.date
    registered_on: _dt.date

    def __post_init__(self):
        if not self.basket:
            raise ReflexivityDemoError("篮子不能为空 / basket must not be empty")
        if self.start < self.registered_on:
            raise ReflexivityDemoError("窗口起点早于登记日，属于事后选窗口 / window starts before registered_on")
        if self.end <= self.start:
            raise ReflexivityDemoError("窗口终点必须晚于起点 / end must be after start")


Thesis = Union[PriceThresholdThesis, RelativeThesis]


def _close_on(data, name, d):
    dates = data["dates"]
    try:
        return _series(data, name)[dates.index(d)]
    except ValueError as e:
        raise ReflexivityDemoError(f"{d} 没有数据 / no data on {d}") from e


def evaluate(thesis: Thesis, data: Dict[str, object]) -> str:
    """Return only 'falsified', 'not_falsified' or 'pending'. Never claims the thesis is confirmed.
    Uses only data strictly after registered_on."""
    dates = data["dates"]
    last = dates[-1]
    if isinstance(thesis, PriceThresholdThesis):
        series_meta(data, thesis.series)
        px = _series(data, thesis.series)
        for d, c in zip(dates, px):
            if thesis.registered_on < d <= thesis.deadline and c >= thesis.threshold:
                return FALSIFIED
        return PENDING if thesis.deadline > last else NOT_FALSIFIED
    if isinstance(thesis, RelativeThesis):
        names = (*thesis.basket, thesis.benchmark)
        if len({series_meta(data, x)["market"] for x in names}) != 1:
            raise ReflexivityDemoError("篮子和基准必须同一市场 / basket and benchmark must share one market")
        if thesis.start < thesis.registered_on:  # defensive; __post_init__ already blocks
            raise ReflexivityDemoError("窗口起点早于登记日 / window starts before registered_on")
        if thesis.end > last:
            return PENDING
        rets = [_close_on(data, s, thesis.end) / _close_on(data, s, thesis.start) - 1 for s in thesis.basket]
        bench = _close_on(data, thesis.benchmark, thesis.end) / _close_on(data, thesis.benchmark, thesis.start) - 1
        return FALSIFIED if sum(rets) / len(rets) > bench else NOT_FALSIFIED
    raise ReflexivityDemoError("未知论点类型 / unknown thesis type")


def example_theses(data: Dict[str, object]):
    """Register examples using only data up to registered_on and constants declared above."""
    dates = data["dates"]
    i = len(dates) - 1 - REGISTER_DAYS_BEFORE_END
    reg = dates[i]
    thr = round(data["DEMO-IDX"][i] * PRICE_FACTOR, 2)
    due = reg + _dt.timedelta(days=HORIZON_DAYS)
    t1 = PriceThresholdThesis("DEMO-IDX", thr, due, reg)
    t2 = RelativeThesis(("DEMO-BASKET-A", "DEMO-BASKET-B"), "DEMO-BENCH", reg, due, reg)
    return t1, t2


# ---------- 报告 / report ----------

VERDICT_ZH = {FALSIFIED: "被证伪 / falsified", NOT_FALSIFIED: "未被证伪 / not falsified",
              PENDING: "未到期 / pending"}
DIV_WHY = {
    "price_high_narrative_fading": "价格新高但叙事降温：买的人越来越少相信故事，循环可能见顶 / price new high while belief cools: loop may be topping.",
    "price_low_narrative_rising": "价格新低但叙事回暖：看法先修复，价格可能跟上 / price new low while belief recovers: loop may be bottoming.",
}
WHY_PRICE = {FALSIFIED: "登记后收盘碰到了阈值，论点错了 / a post-registration close touched the threshold, thesis is wrong.",
             NOT_FALSIFIED: "到期前收盘没碰到阈值，论点暂时活着 / no close touched the threshold by the deadline, thesis survives for now.",
             PENDING: "还没到期，只能等 / deadline not reached yet, wait."}
WHY_REL = {FALSIFIED: "篮子跑赢了基准（未复权收盘），论点错了 / basket beat benchmark, thesis is wrong.",
           NOT_FALSIFIED: "篮子没跑赢基准（未复权收盘），论点暂时活着 / basket did not beat benchmark, thesis survives for now.",
           PENDING: "窗口还没结束，只能等 / window not over yet, wait."}


def build_report(d: Dict[str, object]) -> str:
    m = series_meta(d, "DEMO-IDX")
    dates = d["dates"]
    L = [DISCLAIMER, f"市场 market: {m['market']} | 货币 currency: {m['currency']} | 时区 tz: {m['tz']}", ""]
    s = lead_lag_summary(returns(d["DEMO-IDX"]), d["DEMO-NARRATIVE"][1:])
    lag = s["lag"]
    if lag > 0:
        why = f"价格领先叙事 {lag} 天：价格先动，大家再去找故事 / price leads narrative by {lag}d."
    elif lag < 0:
        why = f"叙事领先价格 {-lag} 天：大家先相信，价格再跟 / narrative leads price by {-lag}d."
    else:
        why = "同日最相关：价格和叙事同步 / strongest same-day."
    L += [f"[循环强度 loop strength] 峰值 lag={lag:+d}, corr={s['corr']:.3f}", "  " + why,
          f"  试了 {s['tried']} 个滞后，取绝对值最大；n≈{s['n']}，SE≈1/√n={s['se']:.3f}，corr 约 {s['z']:.1f} 个标准误，"
          f"未过多重比较，不算信号 / tried {s['tried']} lags, took the max; no multiple-comparison adjustment, not a signal.", ""]
    L.append("[最近 3 个背离点 latest 3 divergences]")
    for p in divergence_points(d["DEMO-IDX"], d["DEMO-NARRATIVE"])[-3:]:
        L.append(f"  {dates[p['t']]} {p['type']}: {DIV_WHY[p['type']]}")
    t1, t2 = example_theses(d)
    v1, v2 = evaluate(t1, d), evaluate(t2, d)
    L += ["", f"[示例登记论点 example registered theses] 登记日 registered_on={t1.registered_on}，数据截至 {dates[-1]}",
          f"  1) 价格阈值 price threshold（= 登记日收盘 × {PRICE_FACTOR}）: 若 DEMO-IDX 在 ({t1.registered_on}, {t1.deadline}] 收盘 >= {t1.threshold} 则错 -> {VERDICT_ZH[v1]}",
          "     " + WHY_PRICE[v1],
          f"  2) 相对 relative（窗口 = 登记日起 {HORIZON_DAYS} 天）: 若等权 DEMO-BASKET-A+B 在 {t2.start}~{t2.end} 跑赢 DEMO-BENCH 则错 -> {VERDICT_ZH[v2]}",
          "     " + WHY_REL[v2],
          "", "未被证伪 ≠ 我对了 / not falsified is not proof"]
    return "\n".join(L)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=DISCLAIMER)
    ap.add_argument("--market", choices=available_markets(), required=True)
    ap.add_argument("--seed", type=int, default=42)
    a = ap.parse_args(argv)
    d = generate_demo_data(a.seed, market_key=a.market)
    print(build_report(d))
    return d


if __name__ == "__main__":
    try:
        main()
    except ReflexivityDemoError as e:
        raise SystemExit(f"错误 / error: {e}")
