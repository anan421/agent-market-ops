import pytest

np = pytest.importorskip("numpy")

from pipeline import dsr_demo as d


def test_sr0_increases_with_n():
    vals = [d.sr0_annual(n, 0.25) for n in (12, 30, 90, 150)]
    assert all(a < b for a, b in zip(vals, vals[1:]))


def test_floor_applied():
    assert d.sr0_annual(50, 0.01) == d.sr0_annual(50, d.V_FLOOR)
    trials = [{"ppy": 252, "n": 500, "sr_annual": 0.1 + 0.01 * i} for i in range(5)]
    assert d.estimate_variance(trials) == d.V_FLOOR


def test_event_and_small_trials_excluded_from_v():
    base = [{"ppy": 252, "n": 500, "sr_annual": s} for s in (-1.0, 0.0, 1.0, 2.0)]
    v0 = d.estimate_variance(base)
    extra = base + [{"kind": "event", "n": 40, "sr_annual": 50.0},
                    {"ppy": 252, "n": 10, "sr_annual": -50.0}]
    assert d.estimate_variance(extra) == v0


def test_dsr_in_unit_interval():
    rng = np.random.default_rng(0)
    for mu in (-0.01, 0.0, 0.002, 0.05):
        x = d.deflated_sharpe(rng.normal(mu, 0.01, 300), 252, 1.0)
        assert 0.0 <= x <= 1.0


def test_deterministic_with_seed():
    assert d.run_demo(seed=7) == d.run_demo(seed=7)


def test_pure_noise_mostly_fails():
    out = d.run_demo(seed=123, n_strategies=50)
    noise = out["results"][:-1]
    assert sum(r["passed"] for r in noise) <= 1


def test_luck_generator_naive_best_looks_good_but_dsr_fails():
    out = d.luck_generator(seed=29)
    best = out["top"][0]
    assert best["t"] >= 2.4 and best["sr_annual"] > 1.5  # 朴素看很漂亮
    assert out["n_pass"] == 0                            # 但 N=100 下无一过 DSR
    assert out["bar"][1] < out["bar"][10] < out["bar"][100]
    assert out["best_dsr_at"][1] >= d.DSR_MIN > out["best_dsr_at"][100]


def test_ppy_defaults_and_unknown_market():
    import pytest
    assert d.ppy_for("cn_a") == 242 and d.ppy_for("hk") == 246
    assert d.ppy_for("us") == 252 and d.ppy_for("crypto") == 365
    assert d.ppy_for("futures") == 242 and d.ppy_for("fx") == 260
    assert d.ppy_for("demo") == 252
    for bad in ("CN_A", "nasdaq", ""):
        with pytest.raises(ValueError, match="未知市场"):
            d.ppy_for(bad)


def test_robustness_across_seeds():
    rb = d.robustness(range(1, 101))
    assert rb["share_t"] >= 0.3      # 纯噪声里常能挑出 t>=2.4 的"好策略"
    assert rb["share_dsr"] <= 0.05   # 但 N=100 下几乎从不过 DSR


def test_mixed_ppy_raises():
    mixed = [{"market": "crypto", "n": 500, "sr_annual": 1.0},
             {"market": "cn_a", "n": 500, "sr_annual": 0.5}]
    with pytest.raises(ValueError, match="混用了不同的每年期数"):
        d.estimate_variance(mixed)
    same = [{"market": "cn_a", "n": 500, "sr_annual": 1.0}]
    r = np.random.default_rng(1).normal(0, 0.01, 300)
    with pytest.raises(ValueError, match="混用了不同的每年期数"):
        d.deflated_sharpe(r, 365, 1.0, same)  # 用 crypto 口径去年化 cn_a 试验
    assert 0 <= d.deflated_sharpe(r, 242, 1.0, same) <= 1


def test_ppy1_backdoor_repro_raises():
    trials = [{"market": "cn_a", "n": 500, "sr_annual": s} for s in (0.1, 0.5, 0.9)]
    trials.append({"market": "crypto", "ppy": 1, "n": 500, "sr_annual": 9.0})
    with pytest.raises(ValueError, match="冲突"):
        d.estimate_variance(trials)


def test_explicit_event_counts_in_n_not_v():
    base = [{"market": "cn_a", "n": 500, "sr_annual": s} for s in (-1.0, 0.0, 1.0, 2.0)]
    ev = {"kind": "event", "market": "cn_a", "n": 500, "sr_annual": 9.0}
    trials = base + [ev]
    assert len(trials) == 5                      # N 计入
    assert d.estimate_variance(trials) == d.estimate_variance(base)  # V 不计入
    out = d.run_demo(seed=42)
    assert out["N"] == len(out["results"]) + 1   # demo 中事件型试验计入 N


def test_periodic_cannot_be_reclassified_via_ppy():
    with pytest.raises(ValueError, match="冲突"):
        d.trial_ppy({"market": "cn_a", "ppy": 1, "n": 500, "sr_annual": 1.0})
    with pytest.raises(ValueError, match="kind='event'"):
        d.trial_ppy({"ppy": 1, "n": 500, "sr_annual": 1.0})
    with pytest.raises(ValueError, match="未知试验类型"):
        d.trial_ppy({"kind": "evnt", "market": "cn_a", "n": 500, "sr_annual": 1.0})
    assert d.trial_ppy({"market": "cn_a", "ppy": 242, "n": 500, "sr_annual": 1.0}) == 242
