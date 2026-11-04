---
name: verify-formal-fetch-prices
description: >
  Formally check (Hypothesis property tests on real code) that agent-market-ops
  pipeline/fetch_prices_demo.py keeps deterministic synthetic OHLCV length,
  Mon–Fri sessions, open-chain continuity, OHLC inequalities, volume bounds,
  and synthetic=True. Use when changing pipeline/fetch_prices_demo.py, its
  schema tests, or demo price generators.
---

# verify-formal-fetch-prices

## Property (plain)

**Promise:**

1. **length:** `len(synthetic_ohlcv(symbol, start, days, start_price)) == days` for `days >= 0` (including `[]` when `days == 0`).
2. **determinism:** same inputs → identical row lists.
3. **sessions:** every bar date is Mon–Fri; consecutive bars are successive weekdays (weekends skipped only).
4. **weekend start:** if `start` is Sat/Sun, the first bar is the following Monday.
5. **shape:** each row has keys `date/symbol/open/high/low/close/volume/synthetic`; `symbol` matches; `synthetic is True`; `volume ∈ [1_000_000, 1_499_999]`.
6. **open chain:** first `open == round(start_price, 4)`; `row[i].open == row[i-1].close`.
7. **OHLC:** after rounding, `high >= max(open, close)`, `low <= min(open, close)`, all prices `> 0`, `close >= 0.01`.

**Harm if broken:** Demo bars can land on weekends, change across runs, break open/close continuity, invent non-positive prices, or drop the `synthetic` flag — teaching OHLCV and any schema that consumes these bars lie.

## Tool and why

- **Tool:** [Hypothesis](https://hypothesis.readthedocs.io/) against the **real** `pipeline.fetch_prices_demo.synthetic_ohlcv`.
- **Why not TLA+/TLC:** the question is “for every symbol / start / days / start_price in a bound, do the shipping bars keep session / OHLC / determinism gates?”, not event ordering. Hypothesis calls the function directly.
- **Bounds:** symbols ≤12 letters/digits/`-_` (incl. empty); starts 2020-01-01…2030-12-31; days 0–60; start_price ∈ [0.01, 1e6]; weekend starts fixed-sampled; 80–250 examples per property (`deadline=None`). No discard-heavy `assume`.
- **Install:** `pip install -e ".[dev]"` (hypothesis is in the `dev` extra; pin also in `formal/fetch_prices/REQUIREMENTS.txt`).

## Coverage record

| Covered code | Role |
|---|---|
| `pipeline/fetch_prices_demo.py` → `synthetic_ohlcv` | length, determinism, Mon–Fri sessions, OHLC, volume, synthetic flag |
| `pipeline/fetch_prices_demo.py` → `_seed` (via public API) | same symbol → same series |

**Sync commit:** `1d5a4b1a9af90eccf594ce113f72f68d120d56ed` (product `pipeline/fetch_prices_demo.py` unchanged at confirm; formal artifacts land in a later commit on `verify/formal-fetch-prices`). Move forward only after re-reading `synthetic_ohlcv` and confirming the properties still describe it.

**Not covered:** CLI `main` argparse / JSON vs CSV emitters / `-o` file write, network fetches (module is offline-only), negative `days` / non-positive `start_price` rejection (API does not validate), timezone-aware calendars / exchange holidays beyond weekend skip.

Sibling formal checks: `.cursor/skills/verify-formal-fees/`, `.cursor/skills/verify-formal-cash-day-picks/`, `.cursor/skills/verify-formal-reconcile/`, `.cursor/skills/verify-formal-dsr/`, `.cursor/skills/verify-formal-margin-of-safety/`, `.cursor/skills/verify-formal-reflexivity/`, `.cursor/skills/verify-formal-x-signal/`.

## How to run (cold)

From repo root with venv active:

```bash
cd /home/box/src/agent-market-ops
. .venv/bin/activate
pip install -e ".[dev]" -q
pytest -q tests/test_fetch_prices_properties.py
# or the formal runner:
python formal/fetch_prices/run_check.py
```

Exit 0 = properties held under the stated bounds. Exit non-zero = Hypothesis counterexample (symbol / start / days / price in the failure).

This check is Hypothesis-only — do not invent TLC flags here. For a TLA+ model elsewhere, use pstack `/statechart` by name.

## Updating after intentional changes

If session rules, OHLC formulas, volume bounds, or the synthetic flag change on purpose, update `tests/test_fetch_prices_properties.py` and this skill’s property sentences in the same change, re-run, then advance **Sync commit**. Use `/maintain-formal-verification-skill` after drive-by edits to `fetch_prices_demo.py`.

## Able to fail (scratch protocol)

1. Temporarily break a guard, e.g. allow Saturday bars, drop `synthetic=True`, or stop chaining `px = c`.
2. Run `pytest -q tests/test_fetch_prices_properties.py` — must fail.
3. Revert the scratch edit.
4. Re-run — must pass again.
