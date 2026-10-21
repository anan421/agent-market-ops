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
    assert m.map_tickers("电池工厂", kw) == ["DEMO-Y"]
    assert m.map_tickers("orbit battery", kw) == ["DEMO-X", "DEMO-Y"]
    assert m.map_tickers("nothing here", kw) == []


def test_summary_on_demo(demo):
    s = m.summarize(demo["posts"], demo["keywords"])
    assert (s["DEMO-X"]["first_hand_posts"], s["DEMO-X"]["engagement"]) == (2, 160)
    assert (s["DEMO-Y"]["first_hand_posts"], s["DEMO-Y"]["engagement"]) == (2, 120)
    assert s["DEMO-X"]["total_posts"] == 4 and s["DEMO-Y"]["total_posts"] == 6


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
    assert all(p["author"].startswith("demo_user_") for p in demo["posts"])


def test_snr_values(demo):
    s = m.summarize(demo["posts"], demo["keywords"])
    assert s["DEMO-X"]["snr"] == pytest.approx(2 / 4, abs=1e-3)
    assert s["DEMO-Y"]["snr"] == pytest.approx(2 / 6, abs=1e-3)


def test_consensus_noise_flag(demo):
    s = m.summarize(demo["posts"], demo["keywords"])
    assert s["DEMO-Y"]["consensus_noise"] is True
    assert s["DEMO-X"]["consensus_noise"] is False


def test_low_snr_but_quiet_is_not_consensus_noise():
    kw = {"DEMO-X": ["rocket"]}
    posts = [{"type": "repost", "text": "rocket news repost", "likes": 1},
             {"type": "repost", "text": "rocket news repost", "likes": 1},
             {"type": "original", "text": "rocket news original", "likes": 1}]
    r = m.summarize(posts, kw)["DEMO-X"]
    assert r["snr"] < 0.4 and r["consensus_noise"] is False


def test_threshold_configurable(demo):
    s = m.summarize(demo["posts"], demo["keywords"], snr_threshold=0.2)
    assert s["DEMO-Y"]["consensus_noise"] is False


def test_empty_ticker_safe():
    r = m.summarize([], {"DEMO-X": ["rocket"]})["DEMO-X"]
    assert r["snr"] == 0.0 and r["consensus_noise"] is False


def test_render_chinese(demo):
    out = m.render(m.summarize(demo["posts"], demo["keywords"]))
    assert m.NOTICE in out
    assert "信号：DEMO-X[美股]，2 条一手。噪声：2 条，扔了。" in out
    assert "共识噪声" in out.split("DEMO-Y")[1]


def test_chinese_short_post_rules():
    assert m.is_low_effort("链上冲！")      # 3 汉字 = 9 < 10
    assert m.is_low_effort("火箭🚀")
    assert not m.is_low_effort("利好利好") and m.text_weight("利好利好") == 12
    assert not m.is_low_effort("电池工厂产量翻倍")
    assert m.is_first_hand({"type": "original", "text": "示例项目链上活跃地址翻倍"})


def test_mixed_language_weight():
    assert m.text_weight("ok 链上") == 2 + 2 * m.CJK_WEIGHT
    assert m.text_weight("🔥🔥!!") == 0


def test_markets_cover_three_incl_crypto(demo):
    mk = {v["market"] for v in demo["keywords"].values()}
    assert len(mk) >= 3 and "crypto" in mk and mk <= set(m.MARKETS)


def test_market_filter(demo):
    s = m.summarize(demo["posts"], demo["keywords"], market="crypto")
    assert list(s) == ["DEMO-Z"]
    assert s["DEMO-Z"]["first_hand_posts"] == 2 and s["DEMO-Z"]["total_posts"] == 3
    assert m.summarize(demo["posts"], demo["keywords"], market="fx") == {}
    with pytest.raises(ValueError):
        m.summarize(demo["posts"], demo["keywords"], market="NASDAQ")


def test_cli_market(capsys):
    out = m.main(["--market", "cn_a"])
    assert "DEMO-Y[A股]" in out and "DEMO-X" not in out and m.NOTICE in out
    assert "没有示例标的" in m.main(["--market", "futures"])


def test_bad_market_rejected(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text(json.dumps({"_notice": m.NOTICE, "posts": [],
                             "keywords": {"DEMO-Q": {"market": "A股", "words": ["x"]}}}), encoding="utf-8")
    with pytest.raises(ValueError):
        m.load_demo(f)


def test_market_enum_exact():
    assert m.MARKETS == ("cn_a", "hk", "us", "crypto", "futures", "fx", "demo")
    assert set(m.MARKET_NAMES) == set(m.MARKETS)


def test_cli_rejects_chinese_market_name():
    with pytest.raises(SystemExit):
        m.main(["--market", "加密"])
    with pytest.raises(SystemExit):
        m.main(["--market", "US"])
