"""Source catalog: load/save manifest, capture versioned snapshots, verify hashes.

Retrieval (search_sources) is added in Step 6.
Human-recorded fields (checked_on, page_modified_on, effective_period) are never
changed by code.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from models import SourceRecord

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "data" / "manifest.json"
SNAPSHOT_DIR = ROOT / "data" / "snapshots"
# canada.ca stalls requests without browser-standard headers, so we send them,
# while still identifying the project in the User-Agent.
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) VERA-hackathon-research/0.1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-CA,en;q=0.9",
}
TIMEOUT_S = 45
RETRIES = 3
BACKOFF_S = 5


def load_manifest(path: Path | str = MANIFEST) -> list[SourceRecord]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [SourceRecord(**s) for s in data["sources"]]


def save_manifest(records: list[SourceRecord], path: Path | str = MANIFEST) -> None:
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))  # keep manifest_version, note
    data["sources"] = [asdict(r) for r in records]
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _fetch(url: str, retries: int = RETRIES, backoff_s: float = BACKOFF_S) -> bytes:
    """GET url with retries on timeouts/network errors. HTTP 4xx is not retried."""
    last: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if 400 <= e.code < 500:
                raise
            last = e
        except (TimeoutError, urllib.error.URLError, ConnectionError) as e:
            last = e
        if attempt < retries:
            print(f"  attempt {attempt} failed ({last}); retrying in {backoff_s * attempt:.0f}s")
            time.sleep(backoff_s * attempt)
    raise RuntimeError(f"Fetch failed after {retries} attempts: {url} ({last})")


def import_snapshot(source_id: str, url: str, saved_file: Path | str,
                    path: Path | str = MANIFEST, out_dir: Path | str = SNAPSHOT_DIR) -> SourceRecord:
    """Fallback: register a page saved manually from a browser (Ctrl+S, 'HTML only')."""
    body = Path(saved_file).read_bytes()
    original = _fetch
    globals()["_fetch"] = lambda _u, **_k: body
    try:
        return record_capture(source_id, url, path, out_dir)
    finally:
        globals()["_fetch"] = original


def capture_snapshot(source_id: str, url: str, out_dir: Path | str = SNAPSHOT_DIR) -> tuple[str, str]:
    """Fetch url, save raw bytes under a new timestamped name, return (relative_path, sha256)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    body = _fetch(url)
    digest = hashlib.sha256(body).hexdigest()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = out_dir / f"{source_id}_{stamp}.html"
    n = 1
    while target.exists():  # never overwrite an earlier snapshot
        target = out_dir / f"{source_id}_{stamp}_{n}.html"
        n += 1
    target.write_bytes(body)
    try:
        rel = target.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        rel = target.as_posix()
    return rel, digest


def record_capture(source_id: str, url: str, path: Path | str = MANIFEST,
                   out_dir: Path | str = SNAPSHOT_DIR) -> SourceRecord:
    records = load_manifest(path)
    rec = next((r for r in records if r.source_id == source_id), None)
    if rec is None:
        raise KeyError(f"Unknown source_id {source_id}")
    snap, digest = capture_snapshot(source_id, url, out_dir)
    rec.canonical_url = url
    rec.snapshot_path = snap
    rec.sha256 = digest
    save_manifest(records, path)
    return rec


def verify_snapshot(rec: SourceRecord) -> bool:
    if not rec.snapshot_path or not rec.sha256:
        return False
    p = Path(rec.snapshot_path)
    if not p.is_absolute():
        p = ROOT / p
    if not p.exists():
        return False
    return hashlib.sha256(p.read_bytes()).hexdigest() == rec.sha256


def _cli(argv: list[str]) -> int:
    if len(argv) >= 3 and argv[0] == "capture":
        rec = record_capture(argv[1], argv[2])
        print(f"{rec.source_id} captured -> {rec.snapshot_path}\n  sha256 {rec.sha256}")
        return 0
    if len(argv) >= 4 and argv[0] == "import":
        rec = import_snapshot(argv[1], argv[2], argv[3])
        print(f"{rec.source_id} imported -> {rec.snapshot_path}\n  sha256 {rec.sha256}")
        return 0
    if argv and argv[0] == "verify":
        bad = 0
        for r in load_manifest():
            ok = verify_snapshot(r)
            bad += not ok
            print(f"{'PASS' if ok else 'FAIL'} {r.source_id} {r.snapshot_path}")
        return 1 if bad else 0
    print("usage: python sources.py capture <ID> <URL> | import <ID> <URL> <saved.html> | verify")
    return 2


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
