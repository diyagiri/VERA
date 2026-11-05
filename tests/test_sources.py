import hashlib, json, shutil
from pathlib import Path
import sources

ROOT = Path(__file__).resolve().parent.parent
FAKE = b"<html><body>fixed test page</body></html>"


def _fake_fetch(url):
    return FAKE


def _tmp_manifest(tmp_path):
    p = tmp_path / "manifest.json"
    shutil.copy(ROOT / "data/manifest.json", p)
    return p


def test_capture_hash_matches_file(tmp_path, monkeypatch):
    monkeypatch.setattr(sources, "_fetch", _fake_fetch)
    path, digest = sources.capture_snapshot("S1", "https://x", tmp_path)
    assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest == hashlib.sha256(FAKE).hexdigest()


def test_second_capture_creates_new_file(tmp_path, monkeypatch):
    monkeypatch.setattr(sources, "_fetch", _fake_fetch)
    a, _ = sources.capture_snapshot("S1", "https://x", tmp_path)
    b, _ = sources.capture_snapshot("S1", "https://x", tmp_path)
    assert a != b and Path(a).exists() and Path(b).exists()


def test_verify_fails_after_tamper(tmp_path, monkeypatch):
    monkeypatch.setattr(sources, "_fetch", _fake_fetch)
    m = _tmp_manifest(tmp_path)
    rec = sources.record_capture("S2", "https://x", m, tmp_path)
    assert sources.verify_snapshot(rec)
    p = Path(rec.snapshot_path)
    p.write_bytes(p.read_bytes() + b"!")
    assert not sources.verify_snapshot(rec)


def test_record_capture_keeps_human_fields(tmp_path, monkeypatch):
    monkeypatch.setattr(sources, "_fetch", _fake_fetch)
    m = _tmp_manifest(tmp_path)
    before = {s["source_id"]: s for s in json.loads(m.read_text())["sources"]}
    sources.record_capture("S2", "https://x", m, tmp_path)
    after = {s["source_id"]: s for s in json.loads(m.read_text())["sources"]}
    for f in ("checked_on", "page_modified_on", "effective_period"):
        assert after["S2"][f] == before["S2"][f]
    assert after["S2"]["canonical_url"] == "https://x"
    assert after["S1"] == before["S1"]


def test_fetch_retries_then_succeeds(monkeypatch):
    calls = {"n": 0}

    class Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return FAKE

    def flaky(req, timeout):
        calls["n"] += 1
        if calls["n"] < 3:
            raise TimeoutError("The read operation timed out")
        return Resp()

    monkeypatch.setattr(sources.urllib.request, "urlopen", flaky)
    monkeypatch.setattr(sources.time, "sleep", lambda s: None)
    assert sources._fetch("https://x") == FAKE and calls["n"] == 3


def test_fetch_gives_up_after_retries(monkeypatch):
    def always_timeout(req, timeout):
        raise TimeoutError("timed out")
    monkeypatch.setattr(sources.urllib.request, "urlopen", always_timeout)
    monkeypatch.setattr(sources.time, "sleep", lambda s: None)
    try:
        sources._fetch("https://x")
    except RuntimeError as e:
        assert "after 3 attempts" in str(e)
    else:
        raise AssertionError("expected RuntimeError")


def test_import_snapshot_registers_saved_file(tmp_path):
    saved = tmp_path / "saved.html"
    saved.write_bytes(FAKE)
    m = _tmp_manifest(tmp_path)
    rec = sources.import_snapshot("S5", "https://x", saved, m, tmp_path / "snaps")
    assert rec.sha256 == hashlib.sha256(FAKE).hexdigest() and sources.verify_snapshot(rec)
