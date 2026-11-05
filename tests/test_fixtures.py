"""Development fixtures only. Held-out cases are deliberately NOT run here."""
import json
from datetime import date
from pathlib import Path

import pytest

import models as m
import rules as r
from tests.fixture_runner import load_cases, run_case

ROOT = Path(__file__).resolve().parent.parent
DEV = load_cases("dev")
BOUNDS = json.loads((ROOT / "data/fixtures/date_boundaries.json").read_text(encoding="utf-8"))["boundaries"]


@pytest.mark.parametrize("case", DEV, ids=[c["case_id"] for c in DEV])
def test_dev_case(case):
    out = run_case(case)
    bad = {k: v for k, v in out.items() if not v["pass"]}
    assert not bad, bad


def test_case_counts_and_ids():
    all_cases = load_cases()
    ids = [c["case_id"] for c in all_cases]
    assert len(ids) == 30 and len(set(ids)) == 30
    assert len(load_cases("dev")) == 20 and len(load_cases("heldout")) == 10


def test_all_case_facts_load():
    for c in load_cases():
        m.facts_from_dict(c["facts"])
        date.fromisoformat(c["as_of_date"])


def test_expected_states_are_valid_and_cover_all_programs():
    valid = {s.value for s in m.AggregateState}
    progs = {p.value for p in m.ProgramId}
    for c in load_cases():
        assert set(c["expected"]) == progs, c["case_id"]
        assert set(c["expected"].values()) <= valid, c["case_id"]


@pytest.mark.parametrize("b", BOUNDS, ids=[b["boundary_id"] for b in BOUNDS])
def test_date_boundary_currently_review_required(b):
    facts = m.Facts(status_category=m.StatusCategory.PERMANENT_RESIDENT, pr_class=b["pr_class"],
                    pr_landing_date=date.fromisoformat(b["pr_landing_date"]))
    res = r.check_rules("NEW-03", facts, date.fromisoformat(b["as_of_date"]), allow_draft=True)
    r2 = next(x for x in res.rule_outcomes if x.rule_id == "NEW-03-R2")
    assert r2.outcome.value == b["expected_now"]
