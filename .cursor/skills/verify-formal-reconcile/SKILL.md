---
name: verify-formal-reconcile
description: >
  Formally check (Hypothesis property tests on real code) that agent-market-ops
  pipeline/reconcile_demo.py keeps cash-day sample summaries at zero P&L diff
  and that render_html matches summary fields (date, accounts, trades, hit-rate,
  disclaimer) with HTML escaping. Use when changing pipeline/reconcile_demo.py,
  its tests, or reconcile HTML examples/schemas that consume the summary shape.
---

# verify-formal-reconcile

## Property (plain)

**Promise:**

1. **Cash-day zero-diff:** For every `YYYY-MM-DD`-shaped date, `sample_summary(date)` returns `date` unchanged, `trades == 0`, both `signal` and `view` accounts at `pnl_pct == 0.0` (equal / flat), hit-rate `0/0`, `synthetic is True`, and the shared `DISCLAIMER`.
2. **Render match:** For every generated summary dict in bound, `render_html(summary)` contains the escaped date (title), escaped headline, each account’s escaped name/status and `:+.2f` P&L cell, `trades: N`, and the escaped disclaimer.
3. **Hit-rate match:** If `hit_rate` is missing/empty → HTML shows `n/a`; otherwise it shows `correct/judgable` and the escaped note.
4. **Escape match:** Strings with `<` / `&` / `>` appear only in `html.escape` form in the document.

**Harm if broken:** End-of-day paper reconcile HTML can invent a non-flat cash day, drop or rewrite account rows, lie about hit-rate, or echo raw markup from status/headline into the page.

## Tool and why

- **Tool:** [Hypothesis](https://hypothesis.readthedocs.io/) against the **real** `pipeline.reconcile_demo.sample_summary` / `render_html`.
- **Why not TLA+/TLC:** the question is “for every summary shape / date in a bound, do the shipping helpers keep zero-diff cash scaffold and field-faithful escaped HTML?”, not event ordering. Hypothesis calls the functions directly.
- **Bounds:** dates via `[0-9]{4}-[0-9]{2}-[0-9]{2}`; ≤5 accounts; pnl in `[-1e6, 1e6]`; trades/hit ints up to 10_000; short unicode text including HTML metacharacters; 100–300 examples per property (`deadline=None`).
- **Install:** `pip install -e ".[dev,formal]"` (optional extra `formal` = hypothesis; pin also in `formal/reconcile/REQUIREMENTS.txt`).

## Coverage record

| Covered code | Role |
|---|---|
| `pipeline/reconcile_demo.py` → `sample_summary` | cash-day zero-diff scaffold |
| `pipeline/reconcile_demo.py` → `render_html` | field match + `html.escape` |
| `pipeline/reconcile_demo.py` → `DISCLAIMER` | shared disclaimer constant |

**Sync commit:** `603303056333a3edb4c570e09072c9e7fac9bbb8` (product `pipeline/reconcile_demo.py` unchanged at confirm; formal artifacts land in a later commit on `verify/formal-reconcile`). Move forward only after re-reading those functions and confirming the properties still describe them.

**Not covered:** CLI `main` / argparse / file IO, JSON pretty-print side channel, schema validation of summaries (`schema/reconcile_summary.schema.json`), calendar-valid dates vs digit patterns, CSS/layout, live ledger CSV matching, fee math (see `.cursor/skills/verify-formal-fees/`), brief cash-day picks (see `.cursor/skills/verify-formal-cash-day-picks/`).

## How to run (cold)

From repo root with venv active:

```bash
cd /home/box/src/agent-market-ops
. .venv/bin/activate
pip install -e ".[dev,formal]" -q
pytest -q tests/test_reconcile_properties.py
# or the formal runner:
python formal/reconcile/run_check.py
```

Exit 0 = properties held under the stated bounds. Exit non-zero = Hypothesis counterexample (summary / date in the failure).

This check is Hypothesis-only — do not invent TLC flags here. For a TLA+ model elsewhere, use pstack `/statechart` by name.

## Updating after intentional changes

If the sample cash-day shape or HTML field mapping changes on purpose, update `tests/test_reconcile_properties.py` and this skill’s property sentences in the same change, re-run, then advance **Sync commit**. Use `/maintain-formal-verification-skill` after drive-by edits to `reconcile_demo.py`.

## Able to fail (scratch protocol)

1. Temporarily break a guard, e.g. set `sample_summary` account `pnl_pct` to `1.0`, or drop `html.escape` on account `name` in `render_html`, or hard-code hit-rate line to `"n/a"`.
2. Run `pytest -q tests/test_reconcile_properties.py` — must fail.
3. Revert the scratch edit.
4. Re-run — must pass again.
