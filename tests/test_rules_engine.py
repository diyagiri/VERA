import json
from datetime import date
from pathlib import Path

import models as m
import rules as r

ROOT = Path(__file__).resolve().parent.parent
PERSONAS = {p["persona_id"]: p for p in
            json.loads((ROOT / "data/fixtures/personas.json").read_text(encoding="utf-8"))["personas"]}
FORBIDDEN = ("eligible", "approved", "entitled", "guaranteed")


def _load(pid):
    p = PERSONAS[pid]
    return m.facts_from_dict(p["facts"], p["goal"]), date.fromisoformat(p["as_of_date"]), p


def test_mei_matches_expected_states():
    facts, as_of, p = _load("P1-MEI")
    res = r.check_all(facts, as_of, allow_draft=True)
    for prog, exp in p["expected"].items():
        assert res[prog].state.value == exp["state"], prog
        if "missing" in exp:
            assert res[prog].missing_inputs == exp["missing"], prog


def test_mei_correction_updates_only_nsp():
    facts, as_of, p = _load("P1-MEI")
    before = r.check_all(facts, as_of, allow_draft=True)
    c = p["correction"]
    facts.update(c["field"], m.TriState(c["new_value"]))
    after, changed = r.rerun_affected(before, facts, c["field"], as_of, allow_draft=True)
    assert changed == ["NEW-02"]
    assert after["NEW-02"].state.value == c["expected_after"]["NEW-02"]["state"]
    assert after["NEW-02"].fact_version == facts.version == 2
    for prog in c["unaffected"]:
        assert after[prog] is before[prog], f"{prog} should not have been re-run"


def test_tomas_needs_official_review():
    facts, as_of, p = _load("P2-TOMAS")
    res = r.check_rules("NEW-03", facts, as_of, allow_draft=True)
    assert res.state.value == p["expected"]["NEW-03"]["state"]


def test_default_gate_blocks_draft_rules():
    facts, as_of, _ = _load("P1-MEI")
    for res in r.check_all(facts, as_of).values():
        assert res.state == m.AggregateState.NEEDS_OFFICIAL_REVIEW
        assert all(x.gated and x.outcome == m.RuleOutcome.REVIEW_REQUIRED for x in res.rule_outcomes)
        assert all(x.logic_outcome is not None for x in res.rule_outcomes)


def test_approved_rule_is_not_gated():
    facts, as_of, _ = _load("P1-MEI")
    rules = m.load_rules()
    for x in rules:
        if x.rule_id == "STU-01-R1":
            x.approval_state, x.reviewer = m.ApprovalState.RULE_APPROVED.value, "Reviewer B"
    res = r.check_rules("STU-01", facts, as_of, rules=rules)
    r1 = next(x for x in res.rule_outcomes if x.rule_id == "STU-01-R1")
    assert not r1.gated and r1.outcome == m.RuleOutcome.FAIL
    assert res.state == m.AggregateState.BLOCKER_FOUND


def test_next_action_text_avoids_forbidden_words():
    for text in r.NEXT_ACTION.values():
        assert not any(w in text.lower() for w in FORBIDDEN), text


def test_naturalized_citizen_rule():
    as_of = date(2026, 11, 5)
    yes = m.Facts(status_category=m.StatusCategory.CITIZEN, naturalized_citizen=m.TriState.YES)
    no = m.Facts(status_category=m.StatusCategory.CITIZEN, naturalized_citizen=m.TriState.NO)
    unk = m.Facts(status_category=m.StatusCategory.CITIZEN)
    assert r.new02_r1(yes, as_of)[0] == m.RuleOutcome.PASS
    assert r.new02_r1(no, as_of)[0] == m.RuleOutcome.FAIL
    assert r.new02_r1(unk, as_of)[2] == ["naturalized_citizen"]


def test_prefer_not_to_say_is_unknown_for_status_rules():
    f = m.Facts(status_category=m.StatusCategory.PREFER_NOT_TO_SAY)
    for fn in (r.stu01_r1, r.new02_r1, r.new03_r1):
        out, _, missing = fn(f, date(2026, 11, 5))
        assert out == m.RuleOutcome.UNKNOWN and missing == ["status_category"]


def test_every_rule_has_an_evaluator():
    assert {x.rule_id for x in m.load_rules()} == set(r.EVALUATORS)


def test_institution_offers_service_blocks_nsp_for_student():
    f = m.Facts(status_category=m.StatusCategory.STUDY_PERMIT,
                is_post_secondary_student=m.TriState.YES,
                institution_offers_service=m.TriState.YES)
    res = r.check_rules("NEW-02", f, date(2026, 11, 5), allow_draft=True)
    assert res.state == m.AggregateState.BLOCKER_FOUND
