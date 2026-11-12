"""Source catalog, versioned snapshots, and curated evidence retrieval.

Retrieved excerpts are untrusted data: they are wrapped before any model sees them
and can never grant permissions or change tool policy.
Human-recorded fields (checked_on, page_modified_on, effective_period) are never
changed by code.
"""
from __future__ import annotations

import hashlib
import html as _html
import re
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
    # Capturing new bytes does not silently roll an approved interpretation forward.
    if Path(path).resolve() == MANIFEST.resolve():
        rule_path = ROOT / "data/rules/rules.json"
        data = json.loads(rule_path.read_text(encoding="utf-8"))
        for rule in data["rules"]:
            if rule["source_id"] == source_id and rule["source_version"] != digest:
                rule["approval_state"] = "RULE_DRAFT"
                rule["reviewer"] = None
                rule["reviewed_on"] = None
                rule["test_ids"] = []
        rule_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
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


# ---------- retrieval (Step 6) ----------

EVIDENCE_PATH = ROOT / "data" / "evidence.json"
S5_HANDOFF_URL = "https://www.canada.ca/en/services/benefits/finder.html"

PROGRAM_KEYWORDS: dict[str, list[str]] = {
    "STU-01": ["funding", "loan", "loans", "grant", "student aid", "tuition", "pay for school",
               "financial aid", "studentaid"],
    "NEW-02": ["settle", "settling", "settlement", "newcomer", "services", "job", "work", "english",
               "community", "counselling", "adjust"],
    "NEW-03": ["settle", "settling", "newcomer", "settlement", "permanent resident", "pr",
               "job", "english", "refugee"],
}
OUT_OF_SCOPE_KEYWORDS = ["tax", "rent", "housing", "child benefit", "ccb", "dental", "cdcp",
                         "workers benefit", "cwb", "safer", "immigration application", "visa",
                         "citizenship test"]
STOPWORDS = {"a", "an", "the", "i", "to", "and", "or", "for", "of", "in", "my", "me", "is",
             "it", "can", "do", "help", "want", "need"}
KIND_RANK = {"rule_span": 0, "context": 1, "exception": 2}


def tokenize(s: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", s.lower()) if t and t not in STOPWORDS]


def _matches(tokens: list[str], keyword: str) -> bool:
    kw = tokenize(keyword) if " " in keyword else [keyword]
    if len(kw) == 1:
        return kw[0] in tokens
    joined = " " + " ".join(tokens) + " "
    return " " + " ".join(kw) + " " in joined


def route_goal(goal: str) -> dict:
    tokens = tokenize(goal)
    matched = {pid: sorted(k for k in kws if _matches(tokens, k)) for pid, kws in PROGRAM_KEYWORDS.items()}
    program_ids = sorted(pid for pid, ks in matched.items() if ks)
    oos = sorted(k for k in OUT_OF_SCOPE_KEYWORDS if _matches(tokens, k))
    if not program_ids and not oos:
        program_ids = sorted(PROGRAM_KEYWORDS)
    return {"program_ids": program_ids, "out_of_scope_terms": oos,
            "matched_keywords": {k: v for k, v in matched.items() if v}}


def load_evidence(path: Path | str = EVIDENCE_PATH) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["evidence"]


def wrap_untrusted(excerpt: str) -> str:
    """Mark retrieved text as data. Angle brackets and ampersands are escaped."""
    return f"<source_excerpt>{_html.escape(excerpt, quote=False)}</source_excerpt>"


def search_sources(goal: str, program_ids: list[str] | None = None, k: int = 5,
                   evidence: list[dict] | None = None) -> dict:
    route = route_goal(goal)
    program_ids = route["program_ids"] if program_ids is None else sorted(program_ids)
    evidence = load_evidence() if evidence is None else evidence
    goal_tokens = set(tokenize(goal))
    results = []
    for pid in program_ids:
        scored = []
        for rec in evidence:
            if rec["program_id"] != pid:
                continue
            overlap = goal_tokens & set(tokenize(rec["excerpt"]))
            score = 2 * len(overlap) + (3 if rec["kind"] == "rule_span" else 1 if rec["kind"] == "context" else 0)
            scored.append((score, rec))
        scored.sort(key=lambda t: (-t[0], KIND_RANK[t[1]["kind"]], t[1]["evidence_id"]))
        for score, rec in scored[:k]:
            results.append({"evidence_id": rec["evidence_id"], "program_id": pid,
                            "source_id": rec["source_id"], "kind": rec["kind"], "rule_id": rec["rule_id"],
                            "excerpt": wrap_untrusted(rec["excerpt"]), "title": rec["title"],
                            "canonical_url": rec["canonical_url"], "score": score})
    oos = route["out_of_scope_terms"]
    return {"goal": goal, "program_ids": program_ids, "results": results,
            "out_of_scope_terms": oos, "handoff": S5_HANDOFF_URL if oos else None}


def resolve_evidence(evidence_id: str, evidence: list[dict] | None = None) -> dict | None:
    evidence = load_evidence() if evidence is None else evidence
    return next((e for e in evidence if e["evidence_id"] == evidence_id), None)


def validate_record(rec: dict | None) -> tuple[bool, str]:
    """True only if the record points at the current approved snapshot and the excerpt is in it."""
    from extract import find_span, snapshot_text  # local import: extract imports this module
    if rec is None:
        return False, "unknown evidence id"
    src = next((r for r in load_manifest() if r.source_id == rec["source_id"]), None)
    if src is None:
        return False, "unknown source"
    if rec["source_version"] != src.sha256:
        return False, "stale version"
    if not verify_snapshot(src):
        return False, "snapshot missing or hash mismatch"
    if not find_span(snapshot_text(rec["source_id"]), rec["excerpt"]):
        return False, "excerpt not found in snapshot"
    return True, "ok"


def validate_evidence(evidence_id: str, evidence: list[dict] | None = None) -> tuple[bool, str]:
    return validate_record(resolve_evidence(evidence_id, evidence))


def _cli(argv: list[str]) -> int:
    if len(argv) >= 3 and argv[0] == "capture":
        rec = record_capture(argv[1], argv[2])
        print(f"{rec.source_id} captured -> {rec.snapshot_path}\n  sha256 {rec.sha256}")
        return 0
    if len(argv) >= 4 and argv[0] == "import":
        rec = import_snapshot(argv[1], argv[2], argv[3])
        print(f"{rec.source_id} imported -> {rec.snapshot_path}\n  sha256 {rec.sha256}")
        return 0
    if len(argv) >= 2 and argv[0] == "search":
        out = search_sources(" ".join(argv[1:]))
        print(f"programs: {out['program_ids']}  out_of_scope: {out['out_of_scope_terms']}")
        for x in out["results"]:
            print(f"  [{x['score']}] {x['evidence_id']} {x['kind']:9} {x['excerpt'][16:-17][:80]}")
        if out["handoff"]:
            print(f"  handoff: {out['handoff']}")
        return 0
    if argv and argv[0] == "verify":
        bad = 0
        for r in load_manifest():
            ok = verify_snapshot(r)
            bad += not ok
            print(f"{'PASS' if ok else 'FAIL'} {r.source_id} {r.snapshot_path}")
        return 1 if bad else 0
    print("usage: python sources.py capture <ID> <URL> | import <ID> <URL> <saved.html> | verify | search <goal>")
    return 2


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
