---
name: verify-formal-margin-of-safety
description: >
  Formally check (Hypothesis property tests on real code) that agent-market-ops
  pipeline/margin_of_safety_demo.py keeps haircut / PE / shares / price gates,
  too_hard MAX_SWING behaviour, fair_value_band = eps×PE ordering, Chinese
  unknown-market and no-cashflow errors, and the valued call partition
  (margin of safety / fair / expensive). Use when changing
  pipeline/margin_of_safety_demo.py, its tests, or MoS gates.
---

# verify-formal-margin-of-safety

## Property (plain)

**Promise:**

1. **Haircut:** `normal_profit(..., haircut)` raises `ValueError` (message contains `haircut`) when haircut ∉ (0, 1]; in-range it equals `min(ttm, last_q*4*haircut)`.
2. **too_hard:** Non-positive annualised quarter or TTM → `True`. When both positive, `max/min > MAX_SWING` → `True`; `max/min ≤ MAX_SWING` → `False` (exactly 2× still valued).
3. **fair_value_band:** Invalid PE (not `0 < pe_low ≤ pe_high`) → Chinese `ValueError` with 「PE 区间」; `shares ≤ 0` → 「股本」. When valued, `lo ≤ hi` and equals `eps × pe` with `eps = normal_profit / shares`.
4. **verdict gates:** `price ≤ 0` → 「价格」; `shares ≤ 0` → 「股本」; unknown market → 「未知市场」; no-cashflow market → 「没有现金流」.
5. **too_hard pile:** `call == "too hard pile"`, `band` / `premium_to_band_top` / `cash_quality` are `None`, `note == NOTES[...]`, currency from `markets.load`.
6. **Valued call partition:** With swing ≤ `MAX_SWING`, `price ≤ lo` and cash_quality ≥ 0.5 → `"margin of safety"`; else `price ≤ hi` → `"fair, no margin"`; else `"expensive"`; band / premium / cash_quality rounds match the helpers.
7. **cash_quality:** `ocf/ttm` when `ttm != 0`, else NaN.

**Harm if broken:** Paper MoS can invent a margin on volatile/loss names, accept inverted PE or zero shares/price, silently accept unknown or no-cashflow markets, or mis-bucket cheap/poor-cash names as “margin of safety”.

## Tool and why

- **Tool:** [Hypothesis](https://hypothesis.readthedocs.io/) against the **real** `pipeline.margin_of_safety_demo` helpers (`normal_profit`, `too_hard`, `fair_value_band`, `verdict`, `cash_quality`).
- **Why not TLA+/TLC:** the question is “for every numeric / market input in a bound, do the shipping helpers keep the documented MoS gates and call partition?”, not event ordering. Hypothesis calls the functions directly.
- **Bounds:** profits in `[-500, 500]` / positive `[0.1, 500]`; shares/price positive up to `1e5`; haircut in/out of `(0,1]`; PE in `(0, 80]`; swing factors around `MAX_SWING`; markets from `PE_BANDS` ∩ cashflow vs `has_cashflow=False`; unknown market strings filtered against `markets.available()`; 100–300 examples per property (`deadline=None`).
- **Install:** `pip install -e ".[dev]"` (hypothesis is in the `dev` extra; pin also in `formal/margin_of_safety/REQUIREMENTS.txt`).

## Coverage record

| Covered code | Role |
|---|---|
| `pipeline/margin_of_safety_demo.py` → `normal_profit` | haircut gate + min formula |
| `pipeline/margin_of_safety_demo.py` → `too_hard` / `MAX_SWING` | loss / swing basket |
| `pipeline/margin_of_safety_demo.py` → `fair_value_band` | PE / shares gates + eps×PE |
| `pipeline/margin_of_safety_demo.py` → `verdict` / `_market` | price/shares/market Chinese errors + call partition |
| `pipeline/margin_of_safety_demo.py` → `cash_quality` | ocf/ttm or NaN |
| `pipeline/margin_of_safety_demo.py` → `NOTES` | note always matches call |

**Sync commit:** `6c9284cad7786b5d80986bee01dfe43113bac711` (product `pipeline/margin_of_safety_demo.py` unchanged at confirm; formal artifacts land in a later commit on `verify/formal-margin-of-safety`). Move forward only after re-reading those functions and confirming the properties still describe them.

**Not covered:** CLI `main` / EXAMPLE printing, inventing PE bands for markets outside `PE_BANDS`, live market calendar / currency drift beyond `markets.load`, schema JSON for MoS outputs, interaction with fee / DSR / reconcile formal checks.

Sibling formal checks: `.cursor/skills/verify-formal-fees/`, `.cursor/skills/verify-formal-cash-day-picks/`, `.cursor/skills/verify-formal-reconcile/`, `.cursor/skills/verify-formal-dsr/`.

## How to run (cold)

From repo root with venv active:

```bash
cd /home/box/src/agent-market-ops
. .venv/bin/activate
pip install -e ".[dev]" -q
pytest -q tests/test_margin_of_safety_properties.py
# or the formal runner:
python formal/margin_of_safety/run_check.py
```

Exit 0 = properties held under the stated bounds. Exit non-zero = Hypothesis counterexample (company / PE / market in the failure).

This check is Hypothesis-only — do not invent TLC flags here. For a TLA+ model elsewhere, use pstack `/statechart` by name.

## Updating after intentional changes

If MoS haircut / PE / too_hard / call partition / Chinese error strings change on purpose, update `tests/test_margin_of_safety_properties.py` and this skill’s property sentences in the same change, re-run, then advance **Sync commit**. Use `/maintain-formal-verification-skill` after drive-by edits to `margin_of_safety_demo.py`.

## Able to fail (scratch protocol)

1. Temporarily break a guard, e.g. make `too_hard` always `False`, drop the `q >= 0.5` conjunct in `verdict`, or make `normal_profit` ignore the haircut upper bound.
2. Run `pytest -q tests/test_margin_of_safety_properties.py` — must fail.
3. Revert the scratch edit.
4. Re-run — must pass again.
