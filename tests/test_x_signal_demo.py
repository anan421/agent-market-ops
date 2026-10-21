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
    assert m.is_first_hand({"type": "quote", "text": "quote with substantive new content", "is_primary_source": True})


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
    assert s["DEMO-X"]["total_posts"] == 4 and s["DEMO-Y"]["total_posts"] == 7


def test_missing_notice_rejected(tmp_path):
    f = tmp_path / "bad.json"
    f.write_text(json.dumps({"keywords": {}, "posts": []}), encoding="utf-8")
    with pytest.raises(ValueError):
        m.load_demo(f)


def test_bad_type_rejected(tmp_path):
    f = tmp_path / "bad.json"
    post = {"id": "x", "author": "demo_user_9", "type": "like", "text": "t", "ts": "t", "likes": 0, "is_primary_source": True}
    f.write_text(json.dumps({"_notice": m.NOTICE, "keywords": {}, "posts": [post]}), encoding="utf-8")
    with pytest.raises(ValueError):
        m.load_demo(f)


def test_only_demo_authors_and_tickers(demo):
    assert all(p["author"].startswith("demo_user_") for p in demo["posts"])
    assert all(t.startswith("DEMO-") for t in demo["keywords"])


def test_snr_values(demo):
    s = m.summarize(demo["posts"], demo["keywords"])
    assert s["DEMO-X"]["snr"] == pytest.approx(2 / 4, abs=1e-3)
    assert s["DEMO-Y"]["snr"] == pytest.approx(2 / 7, abs=1e-3)


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
    assert "信号：DEMO-X[美股]，2 条一手。路人原创：0 条，不算一手。噪声：2 条，扔了。" in out
    assert "共识噪声" in out.split("DEMO-Y")[1]


def test_chinese_short_post_rules():
    assert m.is_low_effort("链上冲！")      # 3 汉字 = 9 < 10
    assert m.is_low_effort("火箭🚀")
    assert not m.is_low_effort("利好利好") and m.text_weight("利好利好") == 12
    assert not m.is_low_effort("电池工厂产量翻倍")
    assert m.is_first_hand({"type": "original", "text": "示例项目链上活跃地址翻倍", "is_primary_source": True})


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
    import markets
    assert list(m.MARKETS) == markets.available()


def test_market_names_match_markets_available():
    import markets
    assert sorted(m.MARKET_NAMES) == markets.available()


def test_cli_choices_from_markets():
    import markets
    for name in markets.available():
        assert m.NOTICE in m.main(["--market", name])


def test_cli_rejects_chinese_market_name():
    with pytest.raises(SystemExit):
        m.main(["--market", "加密"])
    with pytest.raises(SystemExit):
        m.main(["--market", "US"])


def test_primary_source_required(tmp_path):
    f = tmp_path / "bad.json"
    post = {"id": "x", "author": "demo_user_9", "type": "original", "text": "t", "ts": "t", "likes": 0}
    f.write_text(json.dumps({"_notice": m.NOTICE, "keywords": {}, "posts": [post]}), encoding="utf-8")
    with pytest.raises(ValueError):
        m.load_demo(f)
    post["is_primary_source"] = "yes"
    f.write_text(json.dumps({"_notice": m.NOTICE, "keywords": {}, "posts": [post]}), encoding="utf-8")
    with pytest.raises(ValueError):
        m.load_demo(f)


def test_bystander_original_not_first_hand():
    post = {"type": "original", "text": "a long thoughtful bystander analysis post", "is_primary_source": False}
    assert not m.is_first_hand(post)
    assert m.is_bystander_original(post)
    post["is_primary_source"] = True
    assert m.is_first_hand(post) and not m.is_bystander_original(post)


def test_bystander_counted_separately(demo):
    s = m.summarize(demo["posts"], demo["keywords"])
    assert s["DEMO-Y"]["bystander_original"] == 1
    assert s["DEMO-Y"]["first_hand_posts"] == 2
    out = m.render(s)
    assert "信号：DEMO-Y[A股]，2 条一手。路人原创：1 条，不算一手。噪声：4 条，扔了。" in out


def test_word_boundary_english():
    kw = {"DEMO-X": {"market": "us", "words": ["rocket"]}}
    assert m.map_tickers("rocketry club meeting", kw) == []
    assert m.map_tickers("the rocket flew", kw) == ["DEMO-X"]
    assert m.map_tickers("Rocket!", kw) == ["DEMO-X"]


def test_chinese_substring_kept():
    kw = {"DEMO-Y": {"market": "cn_a", "words": ["电池"]}}
    assert m.map_tickers("固态电池产线", kw) == ["DEMO-Y"]
