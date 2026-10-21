"""示例数据，不构成建议。x_signal_demo 测试。"""
import json
from pathlib import Path

import pytest

from pipeline import x_signal_demo as m

DATA = Path(__file__).resolve().parent.parent / "data" / "示例数据_x_posts.json"


@pytest.fixture
def demo():
    return m.load_demo(DATA)


def test_notice_present(demo):
    assert m.NOTICE in demo["_notice"]
    assert m.NOTICE in Path(m.__file__).read_text(encoding="utf-8")


def test_repost_and_reply_are_noise():
    assert not m.is_first_hand({"type": "repost", "text": "a long enough repost text"})
    assert not m.is_first_hand({"type": "reply", "text": "a long enough reply text"})


def test_low_effort_filtered():
    assert m.is_low_effort("🔥🔥🔥")
    assert m.is_low_effort("wow")
    assert not m.is_first_hand({"type": "quote", "text": "wow!!"})
    assert m.is_first_hand({"type": "quote", "text": "quote with substantive new content"})


def test_map_tickers(demo):
    kw = demo["keywords"]
    assert m.map_tickers("Rocket LAUNCH", kw) == ["DEMO-X"]
    assert m.map_tickers("orbit battery", kw) == ["DEMO-X", "DEMO-Y"]
    assert m.map_tickers("nothing here", kw) == []


def test_summary_on_demo(demo):
    s = m.summarize(demo["posts"], demo["keywords"])
    assert s["DEMO-X"] == {"first_hand_posts": 2, "engagement": 160}
    assert s["DEMO-Y"] == {"first_hand_posts": 2, "engagement": 120}


def test_missing_notice_rejected(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text(json.dumps({"keywords": {}, "posts": []}), encoding="utf-8")
    with pytest.raises(ValueError):
        m.load_demo(f)


def test_bad_type_rejected(tmp_path):
    f = tmp_path / "bad.json"
    post = {"id": "x", "author": "demo_user_9", "type": "like", "text": "t", "ts": "t", "likes": 0}
    f.write_text(json.dumps({"_notice": m.NOTICE, "keywords": {}, "posts": [post]}), encoding="utf-8")
    with pytest.raises(ValueError):
        m.load_demo(f)


def test_only_demo_authors_and_tickers(demo):
    assert all(p["author"].startswith("demo_user_") for p in demo["posts"])
    assert all(t.startswith("DEMO-") for t in demo["keywords"])
