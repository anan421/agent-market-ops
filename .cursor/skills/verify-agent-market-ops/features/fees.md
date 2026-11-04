# Fees

Fees exposes illustrative A-share-like commission / stamp / transfer / slippage helpers for paper P&L scaffolding.

## Sub-features

- `fee-commission-floor` applies the minimum commission on small notionals.
- `fee-buy-no-stamp` buy side stamp duty is 0.
- `fee-sell-stamp` sell side stamp duty is positive.
- `fee-round-trip` large-notional round-trip fraction is ~0.30%.

## How to get to it (user POV)

- Import `pipeline.fees` in a Python REPL / one-liner (documented in README “Fees”).

## Driving it with amo_verify

Preconditions:

- Doctor is `DOCTOR_OK`.

- **Buy vs sell.** Run a Python one-liner that prints `fee_breakdown(100000,"buy")` and `fee_breakdown(100000,"sell")`. Buy `stamp_duty` is `0.0`; sell `stamp_duty` is `> 0`; both `total` equal the sum of parts.
- **Round trip.** Print `round_trip_cost_pct()`; value is between `0.0025` and `0.0035`.
- **Proof.** Save the printed dicts to `fees_out.txt` in the evidence dir.

Or: `helpers/amo_verify.sh drive fees`.

## Gotchas

- Rates are documentation examples, not broker quotes.
- `round_trip_cost_pct` ignores the commission floor (large-notional teaching constant).

## Formal check

Hypothesis properties: `.cursor/skills/verify-formal-fees/` — run `python formal/fees/run_check.py` or `pytest -q tests/test_fees_properties.py`.
