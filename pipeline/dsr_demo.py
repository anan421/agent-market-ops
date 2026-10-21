"""Deflated Sharpe Ratio 演示模块（示例数据，不构成建议）。

参考: Bailey & López de Prado (2014), "The Deflated Sharpe Ratio".
所有数据均为随机种子生成的合成数据（示例数据）。
"""
from __future__ import annotations

import functools
import math
from typing import Iterable, Mapping

import numpy as np

try:
    from scipy.stats import norm as _norm

    def _ppf(p: float) -> float:
        return float(_norm.ppf(p))

    def _cdf(x: float) -> float:
        return float(_norm.cdf(x))
except ImportError:  # pragma: no cover
    from statistics import NormalDist

    _ND = NormalDist()

    def _ppf(p: float) -> float:
        return _ND.inv_cdf(p)

    def _cdf(x: float) -> float:
        return _ND.cdf(x)

GAMMA = 0.5772156649  # Euler-Mascheroni
V_FLOOR = 0.25
DSR_MIN = 0.95
MIN_N_OBS = 30

@functools.lru_cache(maxsize=None)
def ppy_for(market: str) -> int:
    """从 markets/ 配置读取该市场的 `periods_per_year`；未知市场抛出中文错误。"""
    import markets  # 市场列表与参数只在 markets/ 维护，这里不复制
    try:
        cfg = markets.load(market)
    except markets.UnknownMarketError:
        raise ValueError(
            f"未知市场: {market!r}。可用值: {', '.join(markets.available())}（须小写）") from None
    p = cfg.get("periods_per_year")
    if not isinstance(p, int) or isinstance(p, bool) or p <= 1:
        raise ValueError(f"市场 {market!r} 的配置缺少合法的 periods_per_year（得到 {p!r}）")
    return p


def sr0_annual(n_trials: int, variance: float) -> float:
    """N 次试验下、纯噪声预期最大年化 Sharpe（SR0）。variance 为年化 SR 的跨试验方差。"""
    if n_trials < 2:
        return 0.0
    v = max(variance, V_FLOOR)
    z1 = _ppf(1 - 1 / n_trials)
    z2 = _ppf(1 - 1 / (n_trials * math.e))
    return math.sqrt(v) * ((1 - GAMMA) * z1 + GAMMA * z2)


def deflated_sharpe(returns: Iterable[float], ppy: int, sr0_ann: float,
                    trials: Iterable[Mapping] | None = None) -> float:
    """返回 DSR ∈ [0,1]。returns 为每期收益，ppy 为每年期数；SR 按每期口径，峰度为原始峰度。
    给出 trials 时，SR0 去年化所用 ppy 必须与这组试验自身年化所用 ppy 相同，否则报错。"""
    if trials is not None:
        check_same_ppy(trials, ppy)
    r = np.asarray(list(returns), dtype=float)
    n = r.size
    if n < 3 or r.std(ddof=1) == 0:
        return 0.0
    sd = r.std(ddof=1)
    sr = r.mean() / sd
    z = (r - r.mean()) / r.std(ddof=0)
    skew = float(np.mean(z ** 3))
    kurt = float(np.mean(z ** 4))  # raw kurtosis, normal = 3
    sr0 = sr0_ann / math.sqrt(ppy)
    denom = 1 - skew * sr + (kurt - 1) / 4 * sr ** 2
    if denom <= 0:
        return 0.0
    return min(1.0, max(0.0, _cdf((sr - sr0) * math.sqrt(n - 1) / math.sqrt(denom))))


def is_event(t: Mapping) -> bool:
    """事件型试验必须显式标记 kind='event'，不能靠 ppy=1 之类的值暗中改类。"""
    return t.get("kind", "periodic") == "event"


def trial_ppy(t: Mapping) -> int:
    """周期型试验的 ppy。有 market 时以市场默认值为准，显式 ppy 与之冲突即报错；
    事件型试验（kind='event'）返回 0，计入 N、不计入 V。"""
    kind = t.get("kind", "periodic")
    if kind not in ("periodic", "event"):
        raise ValueError(f"未知试验类型 kind={kind!r}，只能是 'periodic' 或 'event'")
    if "market" in t:
        p = ppy_for(t["market"])
        if "ppy" in t and t["ppy"] != p:
            raise ValueError(
                f"试验 ppy={t['ppy']} 与市场 {t['market']} 的 ppy={p} 冲突。"
                "有 market 时不允许改写 ppy；事件型试验请显式标记 kind='event'。")
    else:
        p = t.get("ppy")
        if not is_event(t) and (p is None or p <= 1):
            raise ValueError(
                f"周期型试验缺少 market 或 ppy 不合法（ppy={p}）。"
                "事件型试验请显式标记 kind='event'，不要用 ppy=1 表示。")
    return 0 if is_event(t) else int(p)


def check_same_ppy(trials: Iterable[Mapping], ppy: int | None = None) -> int | None:
    """同一组周期型试验必须同一 ppy（年化口径一致）；ppy 给定时还须与之相同。返回该组 ppy。"""
    ps = {trial_ppy(t) for t in trials if trial_ppy(t) > 1}
    if ppy is not None:
        ps.add(ppy)
    if len(ps) > 1:
        raise ValueError(
            f"同一组试验混用了不同的每年期数 ppy={sorted(ps)}（例如 crypto 与 cn_a 混在一组）。"
            "年化口径不一致，方差与 DSR 不可比，请按市场分组分别计算。")
    return ps.pop() if ps else None


def estimate_variance(trials: Iterable[Mapping]) -> float:
    """所有可比周期型试验（不只是赢家）年化 SR 的方差。只用周期型(ppy>1)且 n>=30 的试验；
    事件型(kind='event')/小样本只计入 N。下限 V_FLOOR。周期型试验混用 ppy 时报错。"""
    trials = list(trials)
    check_same_ppy(trials)
    srs = [float(t["sr_annual"]) for t in trials
           if trial_ppy(t) > 1 and t.get("n", 0) >= MIN_N_OBS]
    if len(srs) < 2:
        return V_FLOOR
    return max(float(np.var(srs, ddof=1)), V_FLOOR)


def t_stat(r: np.ndarray) -> float:
    return float(r.mean() / r.std(ddof=1) * math.sqrt(r.size))


def run_demo(seed: int = 42, n_strategies: int = 30, n_obs: int = 504, market: str = "demo",
             cost: float = 0.0) -> dict:
    """合成 n_strategies 个纯噪声策略 + 1 个带真实漂移的策略，逐一当作试验计数。"""
    ppy = ppy_for(market)
    rng = np.random.default_rng(seed)
    rets = [rng.normal(0.0, 0.01, n_obs) for _ in range(n_strategies)]
    rets.append(rng.normal(0.0015, 0.01, n_obs))  # 示例：有正漂移的合成策略
    # 成本只扣一次：试验 Sharpe、V、SR0、t、DSR、报告的 sr_annual 全部用净收益
    nets = [r - cost for r in rets]
    trials = []
    for net in nets:
        trials.append({"market": market, "ppy": ppy, "n": n_obs,
                       "sr_annual": net.mean() / net.std(ddof=1) * math.sqrt(ppy)})
    trials.append({"kind": "event", "market": market, "n": 12, "sr_annual": 3.0})  # 事件型：计入 N，不计入 V
    N = len(trials)
    V = estimate_variance(trials)
    s0 = sr0_annual(N, V)
    results = []
    for i, net in enumerate(nets):
        dsr = deflated_sharpe(net, ppy, s0, trials)
        t = t_stat(net)
        passed = n_obs >= MIN_N_OBS and abs(t) >= 2.4 and net.mean() > 0 and dsr >= DSR_MIN
        results.append({"id": f"SYN-{i:02d}", "sr_annual": trials[i]["sr_annual"],
                        "t": t, "dsr": dsr, "passed": passed})
    return {"N": N, "V": V, "SR0": s0, "trials": trials, "results": results}


def luck_generator(seed: int = 29, n_strategies: int = 100, n_obs: int = 504,
                   market: str = "demo", top: int = 5) -> dict:
    """运气生成器：n_strategies 个纯噪声策略（真实均值 0），按朴素 Sharpe 排序。示例数据。"""
    ppy = ppy_for(market)
    rng = np.random.default_rng(seed)
    rets = rng.normal(0.0, 0.01, (n_strategies, n_obs))
    trials = [{"market": market, "ppy": ppy, "n": n_obs,
               "sr_annual": r.mean() / r.std(ddof=1) * math.sqrt(ppy)} for r in rets]
    V = estimate_variance(trials)
    s0 = sr0_annual(n_strategies, V)
    rows = []
    for i, r in enumerate(rets):
        rows.append({"id": f"NOISE-{i:03d}", "sr_annual": trials[i]["sr_annual"],
                     "t": t_stat(r), "dsr": deflated_sharpe(r, ppy, s0, trials)})
    rows.sort(key=lambda x: x["sr_annual"], reverse=True)
    best = rets[int(rows[0]["id"].split("-")[1])]
    bar = {n: sr0_annual(n, V) for n in (1, 10, 100)}
    dsr_at = {n: deflated_sharpe(best, ppy, bar[n]) for n in bar}
    return {"N": n_strategies, "V": V, "SR0": s0, "top": rows[:top],
            "n_pass": sum(r["dsr"] >= DSR_MIN for r in rows),
            "bar": bar, "best_dsr_at": dsr_at}



def robustness(seeds: Iterable[int] = range(1, 101)) -> dict:
    """跨种子稳健性：朴素最佳 t>=2.4 的比例，以及任一策略过 DSR(N=100) 的比例。"""
    seeds = list(seeds)
    t_hit = dsr_hit = 0
    for s in seeds:
        o = luck_generator(seed=s)
        t_hit += o["top"][0]["t"] >= 2.4
        dsr_hit += o["n_pass"] > 0
    return {"n_seeds": len(seeds), "share_t": t_hit / len(seeds), "share_dsr": dsr_hit / len(seeds)}


def _why_fail(r: dict, s0: float) -> str:
    if r["sr_annual"] <= s0:
        head = f"年化 Sharpe {r['sr_annual']:.2f} 连纯运气门槛 {s0:.2f} 都没到"
    else:
        head = (f"年化 Sharpe {r['sr_annual']:.2f} 虽高于纯运气门槛 {s0:.2f}，"
                "但超出的幅度相对两年样本和波动还不够大")
    return f"{head}，DSR={r['dsr']:.2f} < 0.95，分不清是本事还是运气"


def main() -> None:
    print("【示例数据，不构成建议】试得越多，越要怀疑自己。\n")
    out = luck_generator()
    print(f"我们随机生成了 {out['N']} 个策略，它们的真实收益全部为 0（纯噪声，种子 29）。")
    print(f"所有 {out['N']} 次都算试验：N={out['N']}，方差 V={out['V']:.3f}，门槛 SR0={out['SR0']:.2f}。\n")
    print("按朴素 Sharpe 排名的前五名：")
    for i, r in enumerate(out["top"], 1):
        tnote = "t 值已过 2.4，单看像是显著" if r["t"] >= 2.4 else "t 值未过 2.4"
        print(f"  第{i}名 {r['id']}：年化 Sharpe {r['sr_annual']:+.2f}，t={r['t']:+.2f}（{tnote}）")
        print(f"     为什么不通过：{_why_fail(r, out['SR0'])}")
    print(f"\n结论：{out['N']} 个策略中通过 DSR≥0.95 的有 {out['n_pass']} 个。")
    print("\n同一个第一名，如果只承认试过 N 次：")
    for n, b in out["bar"].items():
        ok = "通过" if out["best_dsr_at"][n] >= DSR_MIN else "不通过"
        print(f"  N={n:3d}：门槛 SR0={b:.2f}，DSR={out['best_dsr_at'][n]:.3f} → {ok}")
    print("隐瞒失败的试验，就能把运气包装成本事。所以 N 只增不减。")
    rb = robustness()
    print(f"\n稳健性（种子 1–{rb['n_seeds']}）：朴素第一名 t≥2.4 的占 {rb['share_t']:.0%}，"
          f"有策略通过 DSR 的占 {rb['share_dsr']:.0%}。")


if __name__ == "__main__":
    main()
