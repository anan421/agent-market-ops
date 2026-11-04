---
name: verify-formal-fees
description: >
  Formally check (Hypothesis property tests on real code) that agent-market-ops
  pipeline/fees.py keeps buy-side stamp_duty at 0, sell-side stamp_duty > 0 for
  positive notional, and fee_breakdown total == sum of parts. Use when changing
  pipeline/fees.py, its unit tests, or paper P&L code that consumes FeeSchedule.
---

# verify-formal-fees

## Property (plain)

**Promise:** For every finite notional ≥ 0 (and generated FeeSchedule with stamp_duty_sell > 0):

1. `fee_breakdown(n, "buy", …)["stamp_duty"] == 0`
2. If `n > 0`, `fee_breakdown(n, "sell", …)["stamp_duty"] > 0` and equals `n * stamp_duty_sell`
3. For both sides, `total` equals the sum of `commission + transfer + slippage + stamp_duty`

**Harm if broken:** Paper P&L silently taxes buys, skips sell stamp, or reports a total that does not match the named components — teaching numbers and any downstream reconcile lie.

## Tool and why

- **Tool:** [Hypothesis](https://hypothesis.readthedocs.io/) against the **real** `pipeline.fees.fee_breakdown` / `commission`.
- **Why not TLA+/TLC:** the question is “for every notional/side/schedule in a numeric bound, do the fee helpers keep A-share-like stamp asymmetry and additive totals?”, not event ordering. Hypothesis calls the shipping functions directly.
- **Bounds:** notionals in `[0, 1e9]` (positive subset `[1e-6, 1e9]`); schedule rates in small non-negative ranges with `stamp_duty_sell ∈ [1e-9, 0.01]`; sides include mixed-case / padded `"buy"`/`"sell"`; 200–400 examples per property (`deadline=None`).
- **Install:** `pip install -e ".[dev,formal]"` (optional extra `formal` = hypothesis; pin also in `formal/fees/REQUIREMENTS.txt`).

## Coverage record

| Covered code | Role |
|---|---|
| `pipeline/fees.py` → `fee_breakdown` | stamp asymmetry + additive total |
| `pipeline/fees.py` → `commission` | max(rate×notional, floor) |
| `pipeline/fees.py` → `FeeSchedule` / `DEFAULT_FEES` | rate inputs |

**Sync commit:** `325ba051cc9f71617d646a0edc2e98bc56d202a2` (product `pipeline/fees.py` at confirm; formal artifacts landed in a later local-only commit). Move forward only after re-reading those functions and confirming the properties still describe them.

**Not covered:** `round_trip_cost_pct` (large-notional teaching constant; ignores commission floor), negative notional rejection vs `abs` coercion, broker-specific schedules beyond generated ranges, currency rounding/tick sizes, concurrent or stateful fee accrual, reconcile HTML / schema.

Sibling formal check for brief cash-day policy: `.cursor/skills/verify-formal-cash-day-picks/`.

## How to run (cold)

From repo root with venv active:

```bash
cd /home/box/src/agent-market-ops
. .venv/bin/activate
pip install -e ".[dev,formal]" -q
pytest -q tests/test_fees_properties.py
# or the formal runner:
python formal/fees/run_check.py
```

Exit 0 = properties held under the stated bounds. Exit non-zero = Hypothesis counterexample (notional / side / schedule in the failure).

This check is Hypothesis-only — do not invent TLC flags here. For a TLA+ model elsewhere, use pstack `/statechart` by name.

## Updating after intentional changes

If stamp policy or part keys change on purpose, update `tests/test_fees_properties.py` and this skill’s property sentences in the same change, re-run, then advance **Sync commit**. Use `/maintain-formal-verification-skill` after drive-by edits to `fees.py`.

## Able to fail (scratch protocol)

1. Temporarily make buy-side apply stamp (e.g. always `n * schedule.stamp_duty_sell`) or set `parts["total"] = sum(...) + 1`.
2. Run `pytest -q tests/test_fees_properties.py` — must fail.
3. Revert the scratch edit.
4. Re-run — must pass again.
