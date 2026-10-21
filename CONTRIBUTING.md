# Contributing

Thanks for helping improve **agent-market-ops**. This repo is designed so coding
agents (OpenAI Codex, Claude Code, etc.) and humans can collaborate safely.

## Ground rules

1. **Demo data only** — never commit live prices, real ledgers, scraped posts, or API keys.
2. **Schema first** — new fields belong in `schema/*.schema.json` before code uses them.
3. **Tests required** — every behavior change should update or add a pytest.
4. **No trading advice** — docs and examples stay educational / scaffolding.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
# or: pip install -r requirements.txt && pip install -e .
pytest -q
```

## Using Codex (or similar agents) on a PR

Suggested agent loop for contributors:

1. **Clarify the change** — which schema / pipeline module / example?
2. **Generate tests first** — ask Codex to draft failing pytest cases under `tests/`.
3. **Implement the minimal fix** — keep demos self-contained (no network).
4. **Run CI locally** — `pytest -q` must pass before opening a PR.
5. **Ask Codex for a review pass** — focus on schema drift, fee arithmetic, and
   brief-lint locked phrases (`今天不做`, fence closure, etc.).

Example Codex prompts:

- *“Add a pytest that rejects an unclosed markdown fence in `brief_check_demo`.”*
- *“Update `ledger_row.schema.json` and regenerate the sample CSV header.”*
- *“Write a CONTRIBUTING note for a new fee row without inventing live broker rates.”*

## Pull request checklist

- [ ] `pytest -q` passes
- [ ] Schemas still validate the files under `examples/`
- [ ] No credentials or proprietary paths
- [ ] README / SKILL updated if the daily agent loop changed

## Code style

- Python 3.10+, stdlib preferred in demos
- Type hints on public functions
- Keep modules under `pipeline/` runnable as `python -m pipeline.<name>`
