"""Smoke test for the self-contained A-share on-call router demo."""
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "router-on-call"
HTML = DEMO / "index.html"
README = DEMO / "README.md"


class _Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[str] = []
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs) -> None:
        self.tags.append(tag)
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data


def test_demo_files_exist():
    assert HTML.is_file()
    assert README.is_file()


def test_html_parses_and_carries_sample_day():
    text = HTML.read_text(encoding="utf-8")
    parser = _Parser()
    parser.feed(text)
    parser.close()
    assert "html" in parser.tags
    assert "canvas" in parser.tags
    assert "A股值班路由" in parser.title
    assert "A股值班路由" in text
    for token in ("TRIAGE", "FIXER", "REVIEWER", "WRITER", "GUARD", "今天不做"):
        assert token in text
    for source in ("X预窗口", "公告", "证伪", "GitHub"):
        assert source in text
    assert "events_in" in text
    assert ">151<" in text
    assert ">142<" in text
    assert ">9<" in text
    assert text.count(">0<") >= 1
    assert "2026-10-23" in text
    assert "Grok" not in text and "GrokBot" not in text
    assert "sk-" not in text


def test_readme_marks_numbers_illustrative():
    text = README.read_text(encoding="utf-8")
    assert "illustrative" in text.lower() or "示例" in text
    assert "151" in text and "142" in text and "今天不做" in text
    assert "drafts" in text
    assert "MIT" in text
