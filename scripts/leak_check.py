"""Fail on secrets, real-looking A-share codes in data files, private paths, .env files."""
from __future__ import annotations
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SECRET_PATTERNS = {
    "openai_key": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    "github_token": re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    "aws_key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "slack_token": re.compile(r"xox[abprs]-[A-Za-z0-9-]{10,}"),
    "private_key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
}
ASHARE = re.compile(r"(?<![0-9A-Za-z])(?:SH|SZ|sh|sz)?(?:00[0-3]|30[01]|60[0135]|68[89])[0-9]{3}(?![0-9])")
DATA_EXT = {".csv", ".json", ".jsonl", ".parquet", ".tsv"}
CODE_ALLOWLIST: set[str] = set()   # explicitly allowed codes (none by default)
FORBIDDEN_DIRS = ("quant/", "briefs/", "pnl_ledger")
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules"}

def scan_text(rel: str, text: str) -> list[str]:
    out = []
    for name, pat in SECRET_PATTERNS.items():
        if pat.search(text): out.append(f"{rel}: {name}")
    if Path(rel).suffix.lower() in DATA_EXT:
        for m in ASHARE.finditer(text):
            if m.group(0)[-6:] not in CODE_ALLOWLIST:
                out.append(f"{rel}: A-share-like code {m.group(0)}"); break
    return out

def scan_path(rel: str) -> list[str]:
    out = []
    name = Path(rel).name
    if name == ".env" or (name.startswith(".env.") and name != ".env.example"):
        out.append(f"{rel}: .env file")
    if any(d in rel for d in FORBIDDEN_DIRS):
        out.append(f"{rel}: forbidden path")
    return out

def scan(root: Path) -> list[str]:
    out = []
    for p in sorted(root.rglob("*")):
        if not p.is_file() or any(part in SKIP_DIRS for part in p.relative_to(root).parts): continue
        rel = p.relative_to(root).as_posix()
        out += scan_path(rel)
        try: text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            if p.suffix.lower() in DATA_EXT:
                out.append(f"{rel}: undecodable data file (cannot scan; fail closed)")
            continue
        out += scan_text(rel, text)
    return out

def main(argv=None) -> int:
    root = Path(argv[0]) if argv else ROOT
    hits = scan(root)
    for h in hits: print("LEAK", h)
    print("leak_check: OK" if not hits else f"leak_check: {len(hits)} finding(s)")
    return 1 if hits else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
