# Reconcile HTML

Reconcile HTML builds a synthetic end-of-day paper reconcile page from a summary dict for a given date.

## Sub-features

- `reconcile-file` writes HTML via `-o`.
- `reconcile-json` also prints summary JSON with `--json`.
- `reconcile-disclaimer` always includes the demo disclaimer text.

## How to get to it (user POV)

- Run `python -m pipeline.reconcile_demo --date 2026-10-21 -o /tmp/reconcile.html` (README).

## Driving it with amo_verify

Preconditions:

- Doctor is `DOCTOR_OK`.
- Scratch dir ready.

- **Write HTML.** Run `python -m pipeline.reconcile_demo --date 2026-10-21 -o /tmp/amo-verify-$RUN_ID/reconcile.html`. Exit `0`.
- **Confirm content.** File contains `Paper reconcile 2026-10-21`, `今天不做`, and `Demo data only. Not investment advice`.
- **Proof.** Copy HTML into evidence and save a `grep` listing of those markers.

Or: `helpers/amo_verify.sh drive reconcile-html`.

## Gotchas

- Without `-o`, HTML goes to stdout (fine for eyeballing, awkward for artifacts — always use `-o` in proofs).
- Numbers are synthetic scaffolding; do not treat them as live performance.
