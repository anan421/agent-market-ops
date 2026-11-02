# Brief lint

Brief lint checks a daily markdown brief for balanced fences, a closed `action` block, and the hard rule that a 「今天不做」 day must not carry a non-empty `picks` fence.

## Sub-features

- `lint-ok-cash` accepts `examples/brief.md` (cash day, no picks).
- `lint-reject-picks` rejects a cash-day brief that includes data rows under `picks`.
- `lint-missing-action` rejects markdown with no `action` fence.
- `lint-unclosed` rejects an unclosed fence.

## How to get to it (user POV)

- Run `python -m pipeline.brief_check_demo <path-to-brief.md>` from the repo root (README quick start).

## Driving it with amo_verify

Preconditions:

- Doctor is `DOCTOR_OK`.
- `examples/brief.md` exists and is the stock demo cash-day brief.
- Evidence dir `/workspace/verify-evidence/agent-market-ops/$RUN_ID/brief-lint/` is writable.

- **OK cash day.** Lint the sample brief. Run `python -m pipeline.brief_check_demo examples/brief.md`. Exit code `0`; stdout is `OK`.
- **Reject picks on cash day.** Write a bad brief under `/tmp/amo-verify-$RUN_ID/bad_picks.md` containing an `action` with 「今天不做」 and a nonempty `picks` fence; run `python -m pipeline.brief_check_demo` on it. Exit code `1`; stderr mentions 「今天不做」.
- **Missing action.** Lint a file with only `# no action`. Exit code `1`; stderr mentions `action`.
- **Proof.** Save stdout/stderr/exit codes to `transcript.txt` and copy the bad fixture path into `META.txt` with feature id `brief-lint`.

Or: `helpers/amo_verify.sh drive brief-lint` (captures the above).

## Gotchas

- Fence counting is line-based on lines matching `^\s*````; nested oddities can confuse humans but the CLI is the source of truth.
- Comment-only lines inside `picks` (starting with `#`) do not count as data rows.
- Passing pytest alone is not a user-path proof; always drive the CLI module.
