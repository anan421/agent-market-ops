# Fetch prices

Fetch prices generates deterministic synthetic OHLCV bars offline (no network) for a symbol and day count.

## Sub-features

- `prices-json` emits JSON bars to stdout or `-o`.
- `prices-csv` emits CSV with the documented fieldnames.
- `prices-deterministic` same inputs → same closes.

## How to get to it (user POV)

- Run `python -m pipeline.fetch_prices_demo --symbol DEMO01 --days 5` (README).

## Driving it with amo_verify

Preconditions:

- Doctor is `DOCTOR_OK`.
- Scratch dir `/tmp/amo-verify-$RUN_ID` exists.

- **JSON write.** Run `python -m pipeline.fetch_prices_demo --symbol DEMO01 --days 5 --start 2026-10-14 -o /tmp/amo-verify-$RUN_ID/prices.json`. Exit `0`; file is valid JSON array length 5; every row has `"synthetic": true`.
- **CSV write.** Run the same with `--format csv -o /tmp/amo-verify-$RUN_ID/prices.csv`. Exit `0`; header includes `date,symbol,open,high,low,close,volume,synthetic`.
- **Proof.** Copy both outputs into the evidence dir and record byte sizes in `META.txt`.

Or: `helpers/amo_verify.sh drive fetch-prices`.

## Gotchas

- Weekends are skipped; `--days 5` means five sessions, not five calendar days.
- Output path parent must exist; the helper creates `/tmp/amo-verify-$RUN_ID`.
