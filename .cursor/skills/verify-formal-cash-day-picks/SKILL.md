---
name: verify-formal-cash-day-picks
description: >
  Formally check (Hypothesis property tests on real code) that agent-market-ops
  brief lint never accepts a 「今天不做」 action day with a non-empty ```picks
  block. Use when changing pipeline/brief_check_demo.py, its tests, or brief
  examples that encode cash-day policy.
---

# verify-formal-cash-day-picks

## Property (plain)

**Promise:** If a brief has balanced fences, at least one closed `action` body that contains 「今天不做」, and a `picks` fence with at least one non-comment data row, then `check_brief_text` must return `(False, …)` and the message must mention 「今天不做」.

**Harm if broken:** Agents and humans can ship a “cash / 今天不做” day that still lists tradable picks — the exact silent regression this repo exists to catch.

## Tool and why

- **Tool:** [Hypothesis](https://hypothesis.readthedocs.io/) property tests against the **real** `pipeline.brief_check_demo.check_brief_text` (and helpers).
- **Why not TLA+/TLC here:** the question is “for every brief *shape* up to a bound, does the Python lint decide correctly?”, not “can concurrent events reorder”. There is no event-ordering protocol; a model checker would only re-encode the same string rules. Hypothesis exercises the shipping function directly.
- **Bounds:** generated briefs use small alphabets, ≤3 action bodies, ≤3 pick rows, optional surrounding prose; 200 examples per property by default (`settings(max_examples=200)`).
- **Install:** `pip install -e ".[dev]" hypothesis` (optional extra `formal` in `pyproject.toml`; pin also in `formal/cash_day_picks/REQUIREMENTS.txt`).

## Coverage record

| Covered code | Role |
|---|---|
| `pipeline/brief_check_demo.py` → `check_brief_text` | decision under test |
| `pipeline/brief_check_demo.py` → `is_no_trade_day`, `picks_nonempty`, `fences_unclosed`, `parse_actions` | helpers composing the decision |

**Sync commit:** `325ba051cc9f71617d646a0edc2e98bc56d202a2` (confirmed when this skill was created). Move the sync commit forward only after you re-read those functions and confirm the properties still describe them.

**Not covered:** fee math (see sibling `.cursor/skills/verify-formal-fees/`), reconcile HTML, schema validation, markdown rendering outside the fence rules, Unicode lookalikes of 「今天不做」, nested/odd fence dialects beyond line-based counting, multi-language synonyms of cash-day.

## How to run (cold)

From repo root with venv active:

```bash
cd /home/box/src/agent-market-ops
. .venv/bin/activate
pip install -e ".[dev,formal]" -q
pytest -q tests/test_brief_check_properties.py
# or the formal runner:
python formal/cash_day_picks/run_check.py
```

Exit 0 = properties held under the stated bounds. Exit non-zero = counterexample in Hypothesis output (read the falsifying brief text in the failure).

When interpreting failures, prefer reading the printed brief over re-deriving the regexes. For a TLA+ model elsewhere in this monorepo, use pstack `/statechart` by name; this check is Hypothesis-only — do not invent TLC flags here.

## Updating after intentional changes

If cash-day policy changes on purpose, update `tests/test_brief_check_properties.py` and this skill’s property sentence in the same change, re-run the check, then advance **Sync commit**. Use `/maintain-formal-verification-skill` after drive-by edits to `brief_check_demo.py`.

## Able to fail (scratch protocol)

To prove the check catches a break:

1. Temporarily delete or bypass the `is_no_trade_day and picks_nonempty` guard in `check_brief_text`.
2. Run `pytest -q tests/test_brief_check_properties.py` — must fail.
3. Revert the scratch edit.
4. Re-run — must pass again (or fail only on documented findings).
