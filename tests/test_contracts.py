import json, pathlib
from datetime import date
import pytest
import models as m

ROOT = pathlib.Path(__file__).resolve().parent.parent


def test_manifest_loads_and_has_five_sources():
    data = json.loads((ROOT / "data/manifest.json").read_text())
    recs = [m.SourceRecord(**s) for s in data["sources"]]
    assert [r.source_id for r in recs] == ["S1", "S2", "S3", "S4", "S5"]


def test_manifest_does_not_invent_hashes_or_snapshots():
    data = json.loads((ROOT / "data/manifest.json").read_text())
    for s in data["sources"]:
        if s["sha256"] is not None:
            assert s["snapshot_path"], f"{s['source_id']} has hash but no snapshot"


def test_new_rule_defaults_to_draft():
    r = m.RuleRecord(rule_id="X", program_id="STU-01", condition="c",
                     required_inputs=[], source_id="S1", source_version=None, evidence_span=None)
    assert r.approval_state == m.ApprovalState.RULE_DRAFT.value


def test_fact_update_bumps_version():
    f = m.Facts()
    f.update("institution_offers_service", m.TriState.NO)
    assert f.version == 2


def test_fact_update_rejects_unknown_field():
    with pytest.raises(ValueError):
        m.Facts().update("sin_number", "123")


def test_to_dict_serialises_enums_and_dates():
    f = m.Facts(status_category=m.StatusCategory.STUDY_PERMIT, pr_landing_date=date(2021, 6, 21))
    d = m.to_dict(f)
    assert d["status_category"] == "study_permit" and d["pr_landing_date"] == "2021-06-21"
    json.dumps(d)


def test_personas_use_only_known_fact_fields():
    personas = json.loads((ROOT / "data/fixtures/personas.json").read_text())["personas"]
    allowed = set(m.Facts.__dataclass_fields__) - {"version", "goal"}
    for p in personas:
        assert set(p["facts"]) <= allowed, p["persona_id"]
