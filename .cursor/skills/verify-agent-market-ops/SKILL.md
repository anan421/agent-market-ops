---
name: verify-agent-market-ops
description: >
  Drive and prove the agent-market-ops CLI/pipeline demos (brief lint, synthetic
  prices, reconcile HTML, fees, schema validate). Use when changing pipeline/,
  schema/, examples/, or markets/ and you need user-path evidence that the daily
  scrape → lint → reconcile loop still works offline.
---

# verify-agent-market-ops

Primary surface: **CLI / Python modules** under `pipeline/` (no web UI, no server).
Repo root: `/home/box/src/agent-market-ops` (or this checkout). All demos are offline.

Evidence root (survives cleanup):
`/workspace/verify-evidence/agent-market-ops/<RUN_ID>/`

## Launch

One-time / per machine (from repo root):

```bash
cd /home/box/src/agent-market-ops
python3 -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
```

Ready means: `python -c "import pipeline.brief_check_demo, pipeline.fees, markets"` exits 0 and `pytest -q` is green on a clean tree. There is no long-lived process to keep alive — each drive is a short CLI invocation in its own shell.

Teardown of the venv is optional and **not** part of cleanup (shared across runs). Cleanup only removes per-run scratch under `/tmp/amo-verify-$RUN_ID`.

## Doctor

Read-only health check before driving:

```bash
cd /home/box/src/agent-market-ops
. .venv/bin/activate
.cursor/skills/verify-agent-market-ops/helpers/amo_verify.sh doctor
```

Doctor must print `DOCTOR_OK` and exit 0. It checks: venv imports, `examples/brief.md` lints OK, and `python -m pipeline.brief_check_demo --help` works. If anything looks off, run doctor first and refuse to drive a broken install.

## Drive

Feature recipes live in `features/`. Prefer the helper:

```bash
export RUN_ID=$(date +%Y%m%d-%H%M%S)
.cursor/skills/verify-agent-market-ops/helpers/amo_verify.sh drive brief-lint
```

Harness is plain bash + the repo's own `python -m pipeline.*` commands. Drive the real user path (CLI as documented in README), not internal pytest-only setters.

## Evidence

Capture for every proof:

- command + exit code
- stdout / stderr transcripts
- side-effect files (HTML, JSON, CSV) when the feature writes them

Store under `/workspace/verify-evidence/agent-market-ops/<RUN_ID>/<feature-id>/`. Include a `META.txt` with feature ID, entry point, and UTC+8 timestamp label.

Proof standards:

- Exercise the documented CLI path.
- Capture both the action and the resulting state (e.g. lint message **and** exit code; HTML file **and** a grep for the date/headline).
- On mutation features, re-read the written file.
- No network mocks required — demos are offline by design. Confirm offline by absence of network (demos never call out).

## Cleanup

```bash
.cursor/skills/verify-agent-market-ops/helpers/amo_verify.sh cleanup
```

Removes `/tmp/amo-verify-$RUN_ID` only. **Never** deletes `/workspace/verify-evidence/…`. Never `killall python`; these demos do not leave servers running.

## Helpers

| helper | invocation |
|---|---|
| `helpers/amo_verify.sh` | `amo_verify.sh doctor` · `amo_verify.sh drive <feature-id>` · `amo_verify.sh cleanup` |

Requires `RUN_ID` for `drive` / `cleanup` (doctor does not). Must be executable.

## Feature map

See [features/README.md](features/README.md). After the app changes, re-seed with `/maintain-verification-skill`.
