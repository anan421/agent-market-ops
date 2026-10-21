# agent-market-ops

[![ci](https://img.shields.io/badge/ci-pytest-brightgreen)](.github/workflows/ci.yml)
[![license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](pyproject.toml)

**Schema-first, agent-native toolkit for daily market ops loops** — scrape → validate → brief lint → reconcile HTML — designed for maintainers who run that loop with coding agents such as **OpenAI Codex** or Claude Code.

> **Demo data only. Not investment advice. No live trading.**
> This repository ships synthetic prices, fake ledgers, and example briefs so you can practice the *ops* layer without leaking edge or credentials.

Suggested GitHub repository name: **`agent-market-ops`**.

---

## Why this exists / 为什么做这个

Coding agents are good at glue work; they are bad at silent schema drift, fee math mistakes, and “no-trade day still has picks” regressions. This package gives you:

| Piece | What you get |
|---|---|
| **JSON schemas** | posts, filings, ledger rows, reconcile summaries |
| **Brief lint** | locked phrases like 「今天不做」, fence balance, no picks on cash days |
| **Fee scaffolding** | illustrative A-share-like one-way / round-trip cost helpers |
| **Reconcile HTML** | tiny offline renderer for a paper end-of-day page |
| **Agent Skill** | `SKILL.md` describing the daily loop for Codex-class agents |
| **Falsifier hooks** | placeholder convention for dated hypothesis invalidation notes |

中文摘要：面向「每天用 Agent 跑采集 → 校验 → 简报检查 → 对账页」的维护者。Schema 优先、费用可审计、简报有锁定句式检查。仓库只有演示数据，不是交易系统，不下单、不提供实盘建议。

---

## Quick start

```bash
git clone https://github.com/anan421/agent-market-ops.git
cd agent-market-ops
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

Run the demos (all offline):

```bash
python -m pipeline.fetch_prices_demo --symbol DEMO01 --days 5
python -m pipeline.brief_check_demo examples/brief.md
python -m pipeline.reconcile_demo --date 2026-10-21 -o /tmp/reconcile.html
```

---

## Layout

```
agent-market-ops/
├── SKILL.md                 # Agent Skills entry for the daily loop
├── schema/                  # JSON Schema (draft 2020-12)
├── pipeline/                # demo Python modules (no network)
├── examples/                # sample brief, ledger.csv, reconcile HTML
├── tests/                   # pytest
├── CONTRIBUTING.md          # Codex-oriented PR workflow
└── SECURITY.md
```

---

## Brief lint (demo rule)

On days whose ```action``` block contains **今天不做**, the brief must not carry a non-empty ```picks``` fence. Unclosed markdown fences always fail.

```bash
python -m pipeline.brief_check_demo examples/brief.md
# → OK
```

---

## Fees (documentation example)

`pipeline/fees.py` exposes an illustrative schedule (commission floor, sell-side stamp duty, transfer fee, slippage). Replace with your broker’s real schedule before any serious paper study. Round-trip cost for large notionals is on the order of **~0.30%** in the default table — a teaching constant, not a quote.

---

## Using with OpenAI Codex

See [CONTRIBUTING.md](CONTRIBUTING.md). Typical agent tasks that fit this repo:

1. Add a schema field + example row + pytest in one PR.
2. Extend `brief_check_demo` with a new locked phrase and failing fixtures first.
3. Regenerate `examples/reconcile_sample.html` from `reconcile_demo`.

Install the skill by pointing your agent at `SKILL.md` in this repo (Agent Skills format).

---

## Disclaimer / 免责声明

- English: Educational scaffolding only. No offers to buy or sell securities. Authors are not responsible for trading losses.
- 简体中文：仅供学习与 Agent 运维脚手架演示。不构成任何证券投资建议，作者不对交易损失负责。

## License

MIT © 2026 anan421 / Vincent Gu — see [LICENSE](LICENSE).

---

## Markets (`markets/`)

One JSON config per market (`cn_a`, `hk`, `us`, `crypto`, `futures`, `fx`, `demo`), loaded with `markets.load(name)`. CI generates its per-market matrix from `markets.available()`.

> **Example values:** `fee_bps` and `price_limit_pct` (and every config carries `example_values: true`) are illustrative round numbers, not real exchange or broker parameters. Non-cash-flow asset classes (`crypto`, `commodity`, `fx`) must set `has_cashflow: false`.
