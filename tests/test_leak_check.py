from scripts import leak_check as lc

FAKE = {"sk": "sk-" + "a" * 24, "ghp": "ghp_" + "b" * 36, "aws": "AKIA" + "C" * 16,
        "slack": "xoxb-" + "1" * 12, "pem": "-----BEGIN RSA " + "PRIVATE KEY-----"}

def test_repo_clean():
    assert lc.main([]) == 0

def test_secrets_detected():
    for v in FAKE.values():
        assert lc.scan_text("notes.md", f"x {v} y")

def test_ashare_code_in_data_only():
    code = "60" + "0519"
    assert lc.scan_text("examples/x.csv", f"sym\n{code}\n")
    assert not lc.scan_text("README.md", code)
    assert not lc.scan_text("examples/x.csv", "DEMO1,100.50,12000")

def test_allowlist(monkeypatch):
    code = "30" + "0001"
    monkeypatch.setattr(lc, "CODE_ALLOWLIST", {code})
    assert not lc.scan_text("a.csv", code)

def test_paths():
    assert lc.scan_path(".env")
    assert lc.scan_path("config/.env.local")
    assert not lc.scan_path(".env.example")
    for p in ("quant/x.py", "briefs/a.md", "data/pnl_ledger.csv"):
        assert lc.scan_path(p)

def test_scan_tmp(tmp_path):
    (tmp_path / ".env").write_text("A=1")
    assert lc.main([str(tmp_path)]) == 1

def test_exchange_prefixed_codes():
    for pre in ("SH", "SZ", "sz"):
        assert lc.scan_text("a.csv", pre + "60" + "0519")

def test_binary_data_file_fails_closed(tmp_path):
    (tmp_path / "x.parquet").write_bytes(b"\xff\xfe\x00binary")
    assert lc.main([str(tmp_path)]) == 1

def test_self_files_are_scanned(tmp_path):
    d = tmp_path / "scripts"; d.mkdir()
    (d / "leak_check.py").write_text("k = '" + FAKE["ghp"] + "'")
    assert lc.main([str(tmp_path)]) == 1
