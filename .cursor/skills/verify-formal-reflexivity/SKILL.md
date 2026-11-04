---
name: verify-formal-reflexivity
description: >
  Formally check (Hypothesis property tests on real code) that agent-market-ops
  pipeline/reflexivity_demo.py keeps PriceThreshold / Relative thesis gates,
  evaluate's falsified/pending/not_falsified partition (registration-day close
  excluded), returns/lead-lag/divergence causality, Chinese 「未知市场」 errors,
  and example_theses pre-registration parameter discipline. Use when changing
  pipeline/reflexivity_demo.py, its tests, or reflexivity / falsifier gates.
---

# verify-formal-reflexivity

## Property (plain)

**Promise:**

1. **PriceThresholdThesis gates:** threshold must be finite and `> 0` (message contains 「门槛」); `deadline` must be after `registered_on` (「到期日」).
2. **RelativeThesis gates:** empty basket / duplicates / benchmark-in-basket rejected; window must start on/after `registered_on` (「登记日」) and `end > start` (「窗口终点」).
3. **evaluate(PriceThreshold):** `FALSIFIED` iff any close in `(registered_on, deadline] >= threshold`; else `PENDING` if `deadline > last` date; else `NOT_FALSIFIED`. Close **on** `registered_on` never counts.
4. **evaluate(Relative):** `PENDING` if `end > last`; else `FALSIFIED` iff equal-weight basket return `> ` benchmark return; else `NOT_FALSIFIED`.
5. **Statuses:** `evaluate` always returns one of `STATUSES` (`falsified` / `not_falsified` / `pending`) — never claims "correct".
6. **returns / lead_lag:** `len(returns(p)) == len(p) - 1`; `lead_lag` tries `2*max_lag+1` lags; summary `se = 1/√n`, `z = |corr|/se`.
7. **divergence_points:** only the two documented types; flags are causal (future edits do not move past `t ≤ k` points); `rolling_corr` prefixes `None` then finite values in `[-1, 1]`.
8. **Market gate:** unknown `market_key` → `ReflexivityDemoError` with 「未知市场」.
9. **example_theses:** `threshold = round(close[reg] * PRICE_FACTOR, 2)` with `reg` at `REGISTER_DAYS_BEFORE_END` before end; future price edits do not move parameters.

**Harm if broken:** Paper reflexivity can invent a post-hoc window, count the registration-day close as a falsifier (or miss a real post-reg hit), let a basket that embeds the benchmark never fail, accept NaN/∞ thresholds that never falsify, leak future prices into divergence flags, or silently accept unknown markets.

## Tool and why

- **Tool:** [Hypothesis](https://hypothesis.readthedocs.io/) against the **real** `pipeline.reflexivity_demo` helpers (`PriceThresholdThesis`, `RelativeThesis`, `evaluate`, `returns`, `lead_lag` / `lead_lag_summary`, `divergence_points`, `rolling_corr`, `load_market`, `generate_demo_data`, `example_theses`).
- **Why not TLA+/TLC:** the question is “for every date / price / market input in a bound, do the shipping falsifier and loop helpers keep the documented gates and partition?”, not event ordering. Hypothesis calls the functions directly.
- **Bounds:** demo series length 40–280; day offsets 0–400; thresholds in `(0, 1e6]` plus NaN/inf/≤0/bool bad cases; lead-lag `max_lag ≤ MAX_LAG`; divergence lookback/mom small; markets from `markets.available()` plus filtered unknowns; 60–200 examples per property (`deadline=None`).
- **Install:** `pip install -e ".[dev]"` (hypothesis is in the `dev` extra; pin also in `formal/reflexivity/REQUIREMENTS.txt`).

## Coverage record

| Covered code | Role |
|---|---|
| `pipeline/reflexivity_demo.py` → `PriceThresholdThesis` | threshold / deadline gates |
| `pipeline/reflexivity_demo.py` → `RelativeThesis` | basket / window gates |
| `pipeline/reflexivity_demo.py` → `evaluate` | FALSIFIED / PENDING / NOT_FALSIFIED partition |
| `pipeline/reflexivity_demo.py` → `returns` / `lead_lag` / `lead_lag_summary` | length, tried count, SE |
| `pipeline/reflexivity_demo.py` → `divergence_points` / `rolling_corr` | types + causality + prefix None |
| `pipeline/reflexivity_demo.py` → `load_market` / `generate_demo_data` | 「未知市场」 |
| `pipeline/reflexivity_demo.py` → `example_theses` / `PRICE_FACTOR` / `REGISTER_DAYS_BEFORE_END` | pre-registration discipline |

**Sync commit:** `1062e47172668bc7eaf9b4d1da0e864afda3cfef` (product `pipeline/reflexivity_demo.py` unchanged at confirm; formal artifacts land in a later commit on `verify/formal-reflexivity`). Move forward only after re-reading those functions and confirming the properties still describe them.

**Not covered:** CLI `main` / `build_report` wording, markets adapter ImportError path (`请先合并 #5`), currency/tz mismatch strings beyond unit tests, cross-market RelativeThesis rejection beyond unit tests, inventing new thesis types.

Sibling formal checks: `.cursor/skills/verify-formal-fees/`, `.cursor/skills/verify-formal-cash-day-picks/`, `.cursor/skills/verify-formal-reconcile/`, `.cursor/skills/verify-formal-dsr/`, `.cursor/skills/verify-formal-margin-of-safety/`.

## How to run (cold)

From repo root with venv active:

```bash
cd /home/box/src/agent-market-ops
. .venv/bin/activate
pip install -e ".[dev]" -q
pytest -q tests/test_reflexivity_properties.py
# or the formal runner:
python formal/reflexivity/run_check.py
```

Exit 0 = properties held under the stated bounds. Exit non-zero = Hypothesis counterexample (dates / prices / market in the failure).

This check is Hypothesis-only — do not invent TLC flags here. For a TLA+ model elsewhere, use pstack `/statechart` by name.

## Updating after intentional changes

If falsifier windows, status partition, lead-lag SE, divergence types, or registration constants change on purpose, update `tests/test_reflexivity_properties.py` and this skill’s property sentences in the same change, re-run, then advance **Sync commit**. Use `/maintain-formal-verification-skill` after drive-by edits to `reflexivity_demo.py`.

## Able to fail (scratch protocol)

1. Temporarily break a guard, e.g. make `evaluate` treat `d >= registered_on` (count registration-day close), drop the `c >= threshold` check, or allow `threshold <= 0` in `PriceThresholdThesis`.
2. Run `pytest -q tests/test_reflexivity_properties.py` — must fail.
3. Revert the scratch edit.
4. Re-run — must pass again.
