---
name: verify-formal-x-signal
description: >
  Formally check (Hypothesis property tests on real code) that agent-market-ops
  pipeline/x_signal_demo.py keeps text_weight / low-effort / first-hand /
  bystander partitions, English word-boundary vs CJK substring keyword hits,
  map_tickers sorting, market filter ValueError, summarize snr / consensus_noise
  formulas, and render NOTICE. Use when changing pipeline/x_signal_demo.py, its
  tests, or first-hand / SNR / consensus-noise gates.
---

# verify-formal-x-signal

## Property (plain)

**Promise:**

1. **text_weight:** latin/digit chars count 1 each; CJK chars count `CJK_WEIGHT` (3); emoji/punctuation/whitespace contribute 0.
2. **is_low_effort:** true iff `text_weight(text) < min_chars`.
3. **has_new_content:** true only when `type ∈ {original, quote}` and not low-effort.
4. **is_first_hand:** true iff has_new_content and `is_primary_source is True` (strict True).
5. **is_bystander_original:** true iff `type == original` and has_new_content and `is_primary_source is not True`; never co-true with is_first_hand; reply/repost never either.
6. **keyword_hit:** English keywords use `\b` word boundary (`rocketry` ↛ `rocket`); keywords containing CJK use substring match.
7. **map_tickers:** returns the sorted list of tickers whose words hit the text.
8. **filter_market / summarize(market=…):** unknown market id → `ValueError`; known market keeps only matching tickers.
9. **summarize:** `snr = round(first_hand/total, 3)` or `0.0` when total=0; `consensus_noise` iff `total>0` and `snr < snr_threshold` and `total_engagement >= high_engagement`; counters / engagement add only for mapped tickers.
10. **render:** always includes `NOTICE`; empty summary → 「这个市场没有示例标的」.
11. **MARKETS** equals `markets.available()`; documented defaults (`DEFAULT_MIN_CHARS=10`, `DEFAULT_SNR_THRESHOLD=0.4`, `DEFAULT_HIGH_ENGAGEMENT=500`, `CJK_WEIGHT=3`) hold.

**Harm if broken:** Paper x-signal can count emoji-only posts as first-hand, treat bystander originals as primary source, match `rocketry` as `rocket`, silently accept unknown markets, mis-flag consensus noise (or miss it), or drop the required 「示例数据，不构成建议」 notice from render.

## Tool and why

- **Tool:** [Hypothesis](https://hypothesis.readthedocs.io/) against the **real** `pipeline.x_signal_demo` helpers (`text_weight`, `is_low_effort`, `has_new_content`, `is_first_hand`, `is_bystander_original`, `keyword_hit`, `map_tickers`, `filter_market`, `summarize`, `render`).
- **Why not TLA+/TLC:** the question is “for every post / keyword / market input in a bound, do the shipping helpers keep the documented first-hand / SNR / market gates?”, not event ordering. Hypothesis calls the functions directly.
- **Bounds:** latin/CJK/junk composed texts (latin ≤20, CJK ≤12); `min_chars` 1–40; likes 0–5000; up to 12 posts per summarize example; snr_threshold ∈ [0.05, 0.9]; high_engagement 10–2000; markets from `markets.available()` plus fixed unknowns; 40–300 examples per property (`deadline=None`). Generators construct weight / type / primary by design (no discard-heavy `assume`).
- **Install:** `pip install -e ".[dev]"` (hypothesis is in the `dev` extra; pin also in `formal/x_signal/REQUIREMENTS.txt`).

## Coverage record

| Covered code | Role |
|---|---|
| `pipeline/x_signal_demo.py` → `text_weight` / `CJK_WEIGHT` | latin + CJK weight; junk → 0 |
| `pipeline/x_signal_demo.py` → `is_low_effort` | weight &lt; min_chars |
| `pipeline/x_signal_demo.py` → `has_new_content` | original/quote + not low-effort |
| `pipeline/x_signal_demo.py` → `is_first_hand` / `is_bystander_original` | primary True vs bystander partition; mutual exclusion |
| `pipeline/x_signal_demo.py` → `keyword_hit` / `map_tickers` | `\b` vs CJK substring; sorted hits |
| `pipeline/x_signal_demo.py` → `filter_market` / `summarize` | unknown market; snr / consensus_noise |
| `pipeline/x_signal_demo.py` → `render` / `NOTICE` / `MARKETS` | notice + empty-market line; markets enum |

**Sync commit:** `e180a4dc7dc39dc775c08cdb05f604452f2cb283` (product `pipeline/x_signal_demo.py` unchanged at confirm; formal artifacts land in a later commit on `verify/formal-x-signal`). Move forward only after re-reading those functions and confirming the properties still describe them.

**Not covered:** `load_demo` JSON schema / notice / DEMO-* ticker / bool `is_primary_source` validation (unit tests in `tests/test_x_signal_demo.py`), CLI `main` argparse choices, `market_display_name` zh strings beyond unit tests, inventing non-DEMO tickers in live data.

Sibling formal checks: `.cursor/skills/verify-formal-fees/`, `.cursor/skills/verify-formal-cash-day-picks/`, `.cursor/skills/verify-formal-reconcile/`, `.cursor/skills/verify-formal-dsr/`, `.cursor/skills/verify-formal-margin-of-safety/`, `.cursor/skills/verify-formal-reflexivity/`.

## How to run (cold)

From repo root with venv active:

```bash
cd /home/box/src/agent-market-ops
. .venv/bin/activate
pip install -e ".[dev]" -q
pytest -q tests/test_x_signal_properties.py
# or the formal runner:
python formal/x_signal/run_check.py
```

Exit 0 = properties held under the stated bounds. Exit non-zero = Hypothesis counterexample (post / keyword / market in the failure).

This check is Hypothesis-only — do not invent TLC flags here. For a TLA+ model elsewhere, use pstack `/statechart` by name.

## Updating after intentional changes

If weight rules, first-hand / bystander partitions, keyword matching, SNR / consensus_noise formulas, or NOTICE / MARKETS change on purpose, update `tests/test_x_signal_properties.py` and this skill’s property sentences in the same change, re-run, then advance **Sync commit**. Use `/maintain-formal-verification-skill` after drive-by edits to `x_signal_demo.py`.

## Able to fail (scratch protocol)

1. Temporarily break a guard, e.g. make `is_first_hand` ignore `is_primary_source`, drop the `\b` in `keyword_hit`, or flip `consensus_noise` to always False.
2. Run `pytest -q tests/test_x_signal_properties.py` — must fail.
3. Revert the scratch edit.
4. Re-run — must pass again.
