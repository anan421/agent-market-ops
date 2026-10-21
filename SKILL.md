---
name: agent-market-ops
description: >
  Schema-first agent-native market ops toolkit for maintainers who run a daily
  scrape → validate → brief-lint → reconcile loop with coding agents (Codex,
  Claude Code, etc.). Use when the user asks to run the demo pipeline, lint a
  brief for 「今天不做」, build a sample reconcile HTML, or extend public JSON
  schemas. Demo / synthetic data only — never live trading advice.
---

# agent-market-ops

`<skill>` means this repository root. All demos are offline.

**Red line:** research and ops scaffolding only. Do not place orders, attach
brokers, or present demo numbers as live performance.

## Daily agent loop (demo)

```
1. Collect   → write synthetic posts/filings matching schema/*.schema.json
2. Validate  → jsonschema (see tests/test_schema.py)
3. Brief     → author markdown with a fenced ```action block
4. Lint      → python -m pipeline.brief_check_demo path/to/brief.md
5. Reconcile → python -m pipeline.reconcile_demo --date YYYY-MM-DD -o out.html
6. Fees      → import pipeline.fees for paper P&L cost scaffolding
```

### Commands

```bash
# synthetic prices
python -m pipeline.fetch_prices_demo --symbol DEMO01 --days 5

# lint the sample brief
python -m pipeline.brief_check_demo examples/brief.md

# sample HTML reconcile
python -m pipeline.reconcile_demo --date 2026-10-21 -o /tmp/reconcile.html

# tests
pytest -q
```

### Brief rules this skill enforces

- Every brief needs a closed ```action fence.
- If the action body contains 「今天不做」, a non-empty ```picks fence is a hard fail.
- Unbalanced ``` fences fail the lint.

### Falsifier hooks (placeholder)

Agents may attach a *falsifier* note in the brief (free text): a dated condition
that would invalidate a working hypothesis. This package does **not** ship live
falsifier JSON; treat hooks as documentation for your own tracker.

### Paths

| path | role |
|---|---|
| `schema/` | public JSON schemas |
| `pipeline/` | demo Python modules |
| `examples/` | sample brief, ledger CSV, reconcile HTML |
| `tests/` | pytest |
| `CONTRIBUTING.md` | Codex-oriented PR workflow |

When extending schemas, update examples and tests in the same change.
