# Schema validate

Schema validate checks demo market configs and price bars against the public JSON Schemas and per-market currency/tz consistency.

## Sub-features

- `validate-markets` every `markets/*.json` validates as `market_config`.
- `validate-bars` every demo bar validates and matches its market currency/tz.
- `validate-actions` demo brief_actions.json rows validate.

## How to get to it (user POV)

- Run `python scripts/validate_demo.py` from the repo root (CI / maintainer path).

## Driving it with amo_verify

Preconditions:

- Doctor is `DOCTOR_OK`.
- `examples/demo/price_bars.csv` and `examples/demo/brief_actions.json` exist.

- **Full validate.** Run `python scripts/validate_demo.py`. Exit `0`; stdout ends with `OK`.
- **Proof.** Save transcript under evidence `schema-validate/transcript.txt`.

Or: `helpers/amo_verify.sh drive schema-validate`.

## Gotchas

- `AMO_MARKET=<name>` restricts validation to one market; a zero-bar market still fails when selected alone if that market has no rows.
- Requires `jsonschema` (pulled in via `.[dev]`).
