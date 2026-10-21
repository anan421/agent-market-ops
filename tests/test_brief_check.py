from pipeline.brief_check_demo import check_brief_text, is_no_trade_day


OK_BRIEF = """
```action
动作: 今天不做
```
"""

BAD_PICKS = """
```action
动作: 今天不做
```

```picks
DEMO01 | 关注 | note
```
"""

MISSING_ACTION = "# no action here\n"

UNCLOSED = """
```action
动作: 今天不做
"""


def test_ok_no_trade():
    ok, msg = check_brief_text(OK_BRIEF)
    assert ok and msg == "OK"
    assert is_no_trade_day(OK_BRIEF)


def test_rejects_picks_on_no_trade_day():
    ok, msg = check_brief_text(BAD_PICKS)
    assert not ok
    assert "今天不做" in msg


def test_requires_action():
    ok, msg = check_brief_text(MISSING_ACTION)
    assert not ok
    assert "action" in msg.lower()


def test_unclosed_fence():
    ok, msg = check_brief_text(UNCLOSED)
    assert not ok
    assert "fence" in msg.lower()


def test_examples_brief_passes():
    from pathlib import Path

    text = (Path(__file__).resolve().parents[1] / "examples" / "brief.md").read_text(
        encoding="utf-8"
    )
    ok, msg = check_brief_text(text)
    assert ok, msg
