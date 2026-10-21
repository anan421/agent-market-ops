# Packaging notes (internal — for Grok Bot / maintainers)

This file documents what was **sanitized** when carving a public OSS package from
Vincent's private A-share agent ops work. Do **not** treat this as user-facing docs.

## Source inspiration (read lightly, never copied wholesale)

- Structure ideas from private `mindspider-market/pipeline/README.md` (deterministic daily steps).
- Brief-lint concept from private `check_brief.py` (locked phrase 「今天不做」, fence checks).
- Agent loop framing from private `skill/.../SKILL.md` (collect → validate → brief → reconcile).
- Fee scaffolding idea from private P&L docs (rates rewritten as illustrative examples only).

## Hard exclusions

| Excluded | Why |
|---|---|
| Real OHLCV / minute bars under `quant/data` | Live edge + market data redistrib risk |
| Real `ledger.csv` / pnl ledgers / dashboard JSON | Personal P&L and hit-rate trail |
| `collector/raw_responses`, X JSONL, filings dumps | Scraped content + handles |
| Strategy / scorer / pair-spread / falsifier live JSON | Trading edge |
| Primary source whitelists, API tokens, SEC UA strings | Credentials / ops secrets |
| Live briefs with real picks / policy flags | Not demo-safe |
| Proprietary path names that map 1:1 to private layout | Fingerprinting |

## What this public package *does* include

- Generic JSON schemas (posts, filings, ledger rows, reconcile summary).
- Demo Python: synthetic prices, fee table as documentation, brief lint for locked phrases, sample HTML reconcile.
- Agent Skills `SKILL.md` describing a generic daily loop with **relative** paths.
- CI + CONTRIBUTING oriented at Codex / coding-agent maintainers.
- Fake numbers only (`+0.00%` cash day, demo tickers `DEMO01` / `000001` style placeholders).

## Application use

Repo is meant to look like a real maintainer project for **OpenAI Codex for Open Source**:
clear problem, installable package, runnable examples, pytest CI, agent-oriented CONTRIBUTING.

## Do not

- Push until Vincent confirms the GitHub repo name / visibility.
- Link back to private `mindspider-market` paths in public README.
- Re-introduce live CSI / SOX / named strategy symbols in examples.
