import json
from pathlib import Path

import pytest

import models as m
from extract import find_span, snapshot_text

ROOT = Path(__file__).resolve().parent.parent
RULES = m.load_rules()
MANIFEST = {s["source_id"]: s for s in json.loads((ROOT / "data/manifest.json").read_text())["sources"]}


def test_eight_rules_load_with_unique_ids():
    ids = [r.rule_id for r in RULES]
    assert len(ids) == 8 and len(set(ids)) == 8


def test_source_version_matches_manifest_hash():
    for r in RULES:
        assert r.source_version == MANIFEST[r.source_id]["sha256"], r.rule_id


def _snapshot_available(source_id):
    p = MANIFEST[source_id]["snapshot_path"]
    return bool(p) and (ROOT / p).exists()


def test_evidence_span_and_exceptions_found_in_snapshot():
    missing = sorted({r.source_id for r in RULES if not _snapshot_available(r.source_id)})
    if missing:
        pytest.skip(f"Snapshots not on this machine ({missing}); run capture_sources.ps1 first")
    for r in RULES:
        text = snapshot_text(r.source_id)
        assert find_span(text, r.evidence_span), f"{r.rule_id} span not in {r.source_id}"
        for e in r.exceptions:
            assert find_span(text, e), f"{r.rule_id} exception not verbatim: {e[:50]}"


def test_no_self_approved_rules():
    for r in RULES:
        if r.approval_state == m.ApprovalState.RULE_APPROVED.value:
            assert r.reviewer and r.reviewer != r.author, r.rule_id


def test_required_inputs_are_known_facts():
    allowed = set(m.Facts.__dataclass_fields__) | {"as_of_date"}
    for r in RULES:
        assert set(r.required_inputs) <= allowed, r.rule_id


def test_rules_reference_known_programs():
    for r in RULES:
        assert r.program_id in {p.value for p in m.ProgramId}, r.rule_id
