---
name: verify-formal-dsr
description: >
  Formally check (Hypothesis property tests on real code) that agent-market-ops
  pipeline/dsr_demo.py keeps Deflated Sharpe in [0,1], returns 0 on degenerate
  series, sr0_annual(n_trials<2)==0 and nondecreasing for n>=2, ppy_for unknown
  markets raising Chinese ValueError, and run_demo rejecting when n_obs <
  MIN_N_OBS. Use when changing pipeline/dsr_demo.py, its tests, or DSR gates.
---

# verify-formal-dsr

## Property (plain)

**Promise:**

1. **Unit interval:** For every finite return series / ppy≥2 / sr0_ann≥0 in bound, `deflated_sharpe(...) ∈ [0, 1]` and finite.
2. **Degenerate → 0:** If `n < 3` or the series is constant (sample std 0), `deflated_sharpe` returns `0.0`.
3. **SR0 shape:** `sr0_annual(n_trials, v) == 0` when `n_trials < 2`; when `n_trials ≥ 2` the value is finite, ≥0, respects `V_FLOOR`, and is non-decreasing in `n_trials` at fixed variance.
4. **ppy_for:** Known markets return `markets.load(...)["periods_per_year"]` (int > 1); unknown market ids raise `ValueError` whose message contains 「未知市场」.
5. **MIN_N_OBS gate:** `run_demo(..., n_obs < MIN_N_OBS)` never sets `passed=True` on any strategy (`DSR_MIN == 0.95` remains the documented threshold constant).

**Harm if broken:** Paper DSR can leave `[0,1]`, treat noise / constant series as significant, understate the multi-trial SR0 bar, silently accept unknown market calendars, or mark short-sample strategies as passing the DSR gate.

## Tool and why

- **Tool:** [Hypothesis](https://hypothesis.readthedocs.io/) against the **real** `pipeline.dsr_demo` helpers (`deflated_sharpe`, `sr0_annual`, `ppy_for`, `run_demo`).
- **Why not TLA+/TLC:** the question is “for every numeric / market input in a bound, do the shipping helpers keep the documented DSR / SR0 / ppy / gate shape?”, not event ordering. Hypothesis calls the functions directly.
- **Bounds:** returns elems in `[-0.05, 0.05]`, series length ≤120; ppy ∈ `[2, 400]`; sr0_ann ∈ `[0, 5]`; n_trials ∈ `[0, 500]`; variance ∈ `[0, 4]`; unknown market strings filtered against `markets.available()`; `run_demo` uses small `n_strategies` and `n_obs < MIN_N_OBS`; 40–300 examples per property (`deadline=None`).
- **Install:** `pip install -e ".[dev]"` (hypothesis is in the `dev` extra; optional `formal` also lists it; pin also in `formal/dsr/REQUIREMENTS.txt`).

## Coverage record

| Covered code | Role |
|---|---|
| `pipeline/dsr_demo.py` → `deflated_sharpe` | unit interval + degenerate → 0 |
| `pipeline/dsr_demo.py` → `sr0_annual` | n&lt;2 → 0; floor; nondecreasing |
| `pipeline/dsr_demo.py` → `ppy_for` | known / 「未知市场」 |
| `pipeline/dsr_demo.py` → `run_demo` + `MIN_N_OBS` / `DSR_MIN` | short-sample gate |

**Sync commit:** `1a70608f27793a3a610e73a6224fc98fd91e8866` (product `pipeline/dsr_demo.py` unchanged at confirm; formal artifacts land in a later commit on `verify/formal-dsr`). Move forward only after re-reading those functions and confirming the properties still describe them.

**Not covered:** `luck_generator` / `robustness` seed ensembles, `estimate_variance` mixed-ppy / event exclusion (see unit tests in `tests/test_dsr_demo.py`), `trial_ppy` / `check_same_ppy` conflict messages beyond what unit tests already pin, CLI `main` printing, scipy vs `statistics.NormalDist` fallback path, live market calendar drift.

Sibling formal checks: `.cursor/skills/verify-formal-fees/`, `.cursor/skills/verify-formal-cash-day-picks/`, `.cursor/skills/verify-formal-reconcile/`.

## How to run (cold)

From repo root with venv active:

```bash
cd /home/box/src/agent-market-ops
. .venv/bin/activate
pip install -e ".[dev]" -q
pytest -q tests/test_dsr_properties.py
# or the formal runner:
python formal/dsr/run_check.py
```

Exit 0 = properties held under the stated bounds. Exit non-zero = Hypothesis counterexample (returns / n_trials / market in the failure).

This check is Hypothesis-only — do not invent TLC flags here. For a TLA+ model elsewhere, use pstack `/statechart` by name.

## Updating after intentional changes

If DSR clamps, SR0 formula, ppy errors, or MIN_N_OBS / DSR_MIN gates change on purpose, update `tests/test_dsr_properties.py` and this skill’s property sentences in the same change, re-run, then advance **Sync commit**. Use `/maintain-formal-verification-skill` after drive-by edits to `dsr_demo.py`.

## Able to fail (scratch protocol)

1. Temporarily break a guard, e.g. make `deflated_sharpe` return `1.5`, or `sr0_annual` return `1.0` when `n_trials < 2`, or drop the `n_obs >= MIN_N_OBS` conjunct in `run_demo`’s `passed`.
2. Run `pytest -q tests/test_dsr_properties.py` — must fail.
3. Revert the scratch edit.
4. Re-run — must pass again.
