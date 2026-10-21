"""Reflexivity / bias turning-point demo.

示例数据，不构成建议。 Synthetic example data only; not investment advice.
All series (DEMO-IDX, DEMO-BASKET-*, DEMO-BENCH, DEMO-NARRATIVE) are fictional,
generated from a fixed random seed. Pure stdlib, no network.
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


def generate_demo_data(seed: int = 42, n: int = 250) -> Dict[str, object]:
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

    return {
        "disclaimer": DISCLAIMER,
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


if __name__ == "__main__":
    d = generate_demo_data()
    print(DISCLAIMER)
    ll = lead_lag(returns(d["DEMO-IDX"]), d["DEMO-NARRATIVE"][1:])
    print("lead-lag:", {k: round(v, 3) for k, v in ll.items()})
    print("divergences:", len(divergence_points(d["DEMO-IDX"], d["DEMO-NARRATIVE"])))
