"""x_signal_demo: 社交帖子一手信源筛选演示。

示例数据，不构成建议。仅演示方法；帖子、作者与标的 DEMO-X / DEMO-Y 均为虚构。
只用标准库。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import markets as _markets

NOTICE = "示例数据，不构成建议"
DEFAULT_MIN_CHARS = 10
VALID_TYPES = {"original", "reply", "quote", "repost"}
REQUIRED = ("id", "author", "type", "text", "ts", "likes", "is_primary_source")
# 市场枚举来自仓库的 markets/ 包（#5），不再写死。
MARKETS = tuple(_markets.available())
# markets/*.json 里没有中文名字段，所以保留这张显示用的表；
# tests 保证它和 markets.available() 完全一致。
MARKET_NAMES = {"cn_a": "A股", "hk": "港股", "us": "美股", "crypto": "加密",
                "futures": "期货", "fx": "外汇", "demo": "演示"}
CJK_WEIGHT = 3  # 一个汉字信息量约等于 3 个拉丁字符
_LATIN = re.compile(r"[A-Za-z0-9]")
_CJK = re.compile(r"[\u4e00-\u9fff]")


def load_demo(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if NOTICE not in data.get("_notice", ""):
        raise ValueError("demo data must carry the notice: " + NOTICE)
    for p in data["posts"]:
        missing = [k for k in REQUIRED if k not in p]
        if missing:
            raise ValueError(f"post {p.get('id')} missing {missing}")
        if not isinstance(p["is_primary_source"], bool):
            raise ValueError(f"post {p['id']} is_primary_source must be bool")
        if p["type"] not in VALID_TYPES:
            raise ValueError(f"post {p['id']} bad type {p['type']}")
    for t, spec in data["keywords"].items():
        if not t.startswith("DEMO-"):
            raise ValueError(f"ticker {t} must be DEMO-*")
        if isinstance(spec, dict) and spec.get("market") not in MARKETS:
            raise ValueError(f"ticker {t} bad market {spec.get('market')}")
    return data


def text_weight(text):
    """有效长度：拉丁字母/数字各算 1，汉字各算 CJK_WEIGHT；emoji、标点不算。"""
    t = text or ""
    return len(_LATIN.findall(t)) + CJK_WEIGHT * len(_CJK.findall(t))


def is_low_effort(text, min_chars=DEFAULT_MIN_CHARS):
    """中英文通用：有效长度不足 min_chars 即水贴（"wow"=3，"链上冲"=9，"火箭🚀"=6）。"""
    return text_weight(text) < min_chars


def has_new_content(post, min_chars=DEFAULT_MIN_CHARS):
    """原创，或带新内容的引用；且不是水贴。"""
    return post["type"] in ("original", "quote") and not is_low_effort(post["text"], min_chars)


def is_first_hand(post, min_chars=DEFAULT_MIN_CHARS):
    """一手 = 当事方本人说的：有新内容，且 is_primary_source 为 True。"""
    return has_new_content(post, min_chars) and post.get("is_primary_source") is True


def is_bystander_original(post, min_chars=DEFAULT_MIN_CHARS):
    """路人原创：有新内容的原创帖，但作者不是当事方。不算一手。"""
    return (post["type"] == "original" and has_new_content(post, min_chars)
            and post.get("is_primary_source") is not True)


def _words(spec):
    return spec["words"] if isinstance(spec, dict) else spec


def market_of(spec):
    return spec.get("market") if isinstance(spec, dict) else None


def filter_market(keywords, market):
    if market is None:
        return keywords
    if market not in MARKETS:
        raise ValueError(f"unknown market {market}; choose from {MARKETS}")
    return {t: v for t, v in keywords.items() if market_of(v) == market}


def keyword_hit(keyword, text):
    """英文关键词按词边界 \\b 匹配（rocketry 不命中 rocket）；含中文的关键词按子串匹配。"""
    k = keyword.lower()
    if _CJK.search(k):
        return k in text
    return re.search(r"\b" + re.escape(k) + r"\b", text) is not None


def map_tickers(text, keywords):
    low = (text or "").lower()
    return sorted(t for t, spec in keywords.items() if any(keyword_hit(k, low) for k in _words(spec)))


DEFAULT_SNR_THRESHOLD = 0.4
DEFAULT_HIGH_ENGAGEMENT = 500


def summarize(posts, keywords, min_chars=DEFAULT_MIN_CHARS,
              snr_threshold=DEFAULT_SNR_THRESHOLD, high_engagement=DEFAULT_HIGH_ENGAGEMENT,
              market=None):
    """Per ticker: first-hand count/engagement, total related count/engagement, snr, flag.

    snr = first_hand_posts / total_posts (posts of any type mapped to the ticker).
    consensus_noise = snr < snr_threshold and total_engagement >= high_engagement.
    """
    keywords = filter_market(keywords, market)
    out = {t: {"market": market_of(keywords[t]), "first_hand_posts": 0, "engagement": 0,
               "bystander_original": 0, "total_posts": 0, "total_engagement": 0} for t in keywords}
    for p in posts:
        fh = is_first_hand(p, min_chars)
        by = is_bystander_original(p, min_chars)
        for t in map_tickers(p["text"], keywords):
            r = out[t]
            r["total_posts"] += 1
            r["total_engagement"] += int(p["likes"])
            if by:
                r["bystander_original"] += 1
            if fh:
                r["first_hand_posts"] += 1
                r["engagement"] += int(p["likes"])
    for r in out.values():
        r["snr"] = round(r["first_hand_posts"] / r["total_posts"], 3) if r["total_posts"] else 0.0
        r["consensus_noise"] = (r["total_posts"] > 0 and r["snr"] < snr_threshold
                                and r["total_engagement"] >= high_engagement)
    return out


def render(summary):
    """中文短句输出。"""
    lines = [NOTICE + "。"]
    if not summary:
        lines.append("这个市场没有示例标的。")
    for t, r in summary.items():
        by = r.get("bystander_original", 0)
        noise = r["total_posts"] - r["first_hand_posts"] - by
        tag = f"[{MARKET_NAMES.get(r['market'], r['market'])}]" if r.get("market") else ""
        line = f"信号：{t}{tag}，{r['first_hand_posts']} 条一手。路人原创：{by} 条，不算一手。噪声：{noise} 条，扔了。信噪比 {r['snr']:.2f}。"
        if r["consensus_noise"]:
            line += f"互动 {r['total_engagement']}，热闹全是转的。共识噪声，别追。"
        lines.append(line)
    return "\n".join(lines)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="x_signal_demo（" + NOTICE + "）")
    ap.add_argument("--market", choices=MARKETS, help="只看某个市场")
    ap.add_argument("--data", default=str(Path(__file__).resolve().parent.parent / "data" / "示例数据_x_posts.json"))
    a = ap.parse_args(argv)
    d = load_demo(a.data)
    out = render(summarize(d["posts"], d["keywords"], market=a.market))
    print(out)
    return out


if __name__ == "__main__":
    main()
