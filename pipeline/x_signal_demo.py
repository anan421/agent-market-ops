"""x_signal_demo: 社交帖子一手信源筛选演示。

示例数据，不构成建议。仅演示方法；帖子、作者与标的 DEMO-X / DEMO-Y 均为虚构。
只用标准库。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

NOTICE = "示例数据，不构成建议"
DEFAULT_MIN_CHARS = 10
VALID_TYPES = {"original", "reply", "quote", "repost"}
REQUIRED = ("id", "author", "type", "text", "ts", "likes")
_WORD = re.compile(r"[A-Za-z0-9\u4e00-\u9fff]")


def load_demo(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if NOTICE not in data.get("_notice", ""):
        raise ValueError("demo data must carry the notice: " + NOTICE)
    for p in data["posts"]:
        missing = [k for k in REQUIRED if k not in p]
        if missing:
            raise ValueError(f"post {p.get('id')} missing {missing}")
        if p["type"] not in VALID_TYPES:
            raise ValueError(f"post {p['id']} bad type {p['type']}")
    return data


def is_low_effort(text, min_chars=DEFAULT_MIN_CHARS):
    """Emoji-only, punctuation-only, or shorter than min_chars meaningful chars."""
    meaningful = _WORD.findall(text or "")
    return len(meaningful) < min_chars


def is_first_hand(post, min_chars=DEFAULT_MIN_CHARS):
    """original / quote with real new content = first hand; repost/replies/low-effort = noise."""
    if post["type"] not in ("original", "quote"):
        return False
    return not is_low_effort(post["text"], min_chars)


def map_tickers(text, keywords):
    low = (text or "").lower()
    return sorted(t for t, kws in keywords.items() if any(k.lower() in low for k in kws))


def summarize(posts, keywords, min_chars=DEFAULT_MIN_CHARS):
    out = {t: {"first_hand_posts": 0, "engagement": 0} for t in keywords}
    for p in posts:
        if not is_first_hand(p, min_chars):
            continue
        for t in map_tickers(p["text"], keywords):
            out[t]["first_hand_posts"] += 1
            out[t]["engagement"] += int(p["likes"])
    return out


if __name__ == "__main__":
    src = Path(__file__).resolve().parent.parent / "data" / "示例数据_x_posts.json"
    d = load_demo(src)
    print(NOTICE)
    print(json.dumps(summarize(d["posts"], d["keywords"]), ensure_ascii=False, indent=2))
