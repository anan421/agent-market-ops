# agent-market-ops verification map

Maintained source for verifying the user-facing CLI loop of **agent-market-ops**.
Read this index before driving, then use the matching feature file.

## Baseline preconditions

- Repo root is the `agent-market-ops` checkout; `.venv` activated with `pip install -e ".[dev]"`.
- `helpers/amo_verify.sh doctor` prints `DOCTOR_OK`.
- Set `RUN_ID` (e.g. `20261102-233000`) and write evidence only under `/workspace/verify-evidence/agent-market-ops/$RUN_ID/`.
- Scratch writes go to `/tmp/amo-verify-$RUN_ID/` (created by the helper).
- Never treat a prior agent's leftover `/tmp` tree as healthy without re-running doctor.

## Driving conventions

- Start every recipe from baseline unless a feature lists extra preconditions.
- Commands are literal; keep flags and paths unchanged.
- Harness: bash + `python -m pipeline.*` / `python scripts/validate_demo.py`.
- Restore nothing in product trees; only delete `/tmp/amo-verify-$RUN_ID` on cleanup.
- Keep proof artifacts under `/workspace/verify-evidence/…`.

## Proof and skip reporting

- CLI proof includes the command, stdout, stderr, and exit code.
- File outputs need a second read (size > 0 and content markers).
- Record feature ID and entry point in `META.txt`.
- An unreachable path is a failure with the unmet precondition — never mark it verified via a different path.

## Feature entry contract

Each feature file: H1 + one paragraph, then exactly four H2s:

1. `Sub-features`
2. `How to get to it (user POV)`
3. `Driving it with amo_verify` (starts with `Preconditions:`)
4. `Gotchas`

## Features

- [Brief lint](./brief-lint.md) — cash-day / fence / picks rules on markdown briefs.
- [Fetch prices](./fetch-prices.md) — synthetic OHLCV demo CLI.
- [Reconcile HTML](./reconcile-html.md) — offline paper end-of-day page.
- [Fees](./fees.md) — illustrative A-share-like fee helpers.
- [Schema validate](./schema-validate.md) — demo bars + market configs vs JSON Schema.
