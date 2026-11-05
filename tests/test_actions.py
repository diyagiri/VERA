import json
import re
from datetime import date
from pathlib import Path

import pytest

import actions as a
import models as m
import rules as r

ROOT = Path(__file__).resolve().parent.parent
MEI = json.loads((ROOT / "data/fixtures/personas.json").read_text(encoding="utf-8"))["personas"][0]
AS_OF = date.fromisoformat(MEI["as_of_date"])
INST_Q = m.QUESTIONS["institution_offers_service"]
STUDY_Q = ("Can I use BC NSP services as an international post-secondary student whose institution "
           "does not offer these services?")


def _snapshots_here():
    man = json.loads((ROOT / "data/manifest.json").read_text())["sources"]
    return all(x["snapshot_path"] and (ROOT / x["snapshot_path"]).exists() for x in man)


def _mei():
    facts = m.facts_from_dict(MEI["facts"], MEI["goal"])
    return facts, r.check_all(facts, AS_OF, allow_draft=True)


def _texts(plan, kind=None, pid=None):
    return [l.text for l in plan.lines if (kind is None or l.kind == kind) and (pid is None or l.program_id == pid)]


def test_mei_initial_plan():
    facts, res = _mei()
    plan = a.prepare_plan(res, facts)
    assert a.ANSWER_PREFIX + INST_Q in _texts(plan, "task", "NEW-02")
    assert "Review the StudentAid BC status criterion on the official page." in _texts(plan, "task", "STU-01")
    assert _texts(plan, "enquiry_question", "NEW-02") == []


def test_mei_correction_replan_adds_provider_questions():
    facts, res = _mei()
    facts.update("institution_offers_service", m.TriState.NO)
    res, _ = r.rerun_affected(res, facts, "institution_offers_service", AS_OF, allow_draft=True)
    plan = a.prepare_plan(res, facts)
    qs = _texts(plan, "enquiry_question", "NEW-02")
    assert STUDY_Q in qs and len(qs) == 4
    assert not any(t.startswith(a.ANSWER_PREFIX) for t in _texts(plan, "task", "NEW-02"))
    assert all(l.fact_version == 2 for l in plan.lines)


def test_invalidate_removes_dependent_lines():
    facts, res = _mei()
    facts.update("institution_offers_service", m.TriState.NO)
    res, _ = r.rerun_affected(res, facts, "institution_offers_service", AS_OF, allow_draft=True)
    plan = a.prepare_plan(res, facts)
    dependent = {l.line_id for l in plan.lines if "institution_offers_service" in l.depends_on}
    keep = {l.line_id for l in plan.lines} - dependent
    assert dependent
    plan = a.invalidate(plan, "institution_offers_service")
    assert {l.line_id for l in plan.lines} == keep and plan.stale


def test_templates_avoid_forbidden_words():
    texts = [t for tpl in a.TEMPLATES.values() for t in tpl["tasks"] + tpl["questions"]]
    texts += list(m.QUESTIONS.values()) + list(a.STATUS_WORDS.values()) + [a.LIMITS]
    for t in texts:
        low = t.lower()
        assert not any(re.search(rf"\b{w}\b", low) for w in a.FORBIDDEN_WORDS), t


def test_describe_facts_empty_for_unknown_facts():
    assert a.describe_facts(m.Facts()) == []


def test_support_check_removes_unsupported_line():
    if not _snapshots_here():
        pytest.skip("Snapshots not on this machine")
    facts, res = _mei()
    plan = a.prepare_plan(res, facts)
    plan.lines.append(m.PlanLine("FAKE-task-0", "STU-01", "task", "Unsupported claim.",
                                 evidence_ids=["S9@deadbeef#00"]))
    plan = a.support_check(plan)
    assert "Unsupported claim." in plan.removed
    assert "Unsupported claim." not in _texts(plan)
    assert a.ANSWER_PREFIX + INST_Q in _texts(plan)   # Answer: tasks need no evidence


def test_render_markdown_structure_and_no_stray_numbers():
    facts, res = _mei()
    facts.update("institution_offers_service", m.TriState.NO)
    res, _ = r.rerun_affected(res, facts, "institution_offers_service", AS_OF, allow_draft=True)
    md = a.render_markdown(a.prepare_plan(res, facts))
    for h in ("# VERA plan", "## Checklist", "## Draft enquiry to a provider", "## Limits"):
        assert h in md
    assert "Nothing was sent" in md
    stripped = md.replace(MEI["as_of_date"], "")
    stripped = re.sub(r"(?m)^\d+\. ", "", stripped)
    assert not re.search(r"\d", stripped), re.findall(r".*\d.*", stripped)


def test_gated_plan_uses_official_review_templates_only():
    facts = m.facts_from_dict(MEI["facts"], MEI["goal"])
    res = r.check_all(facts, AS_OF)          # default: gated
    plan = a.prepare_plan(res, facts)
    for pid in a.PROGRAM_ORDER:
        expected = a.TEMPLATES[(pid, m.AggregateState.NEEDS_OFFICIAL_REVIEW)]["tasks"]
        assert _texts(plan, "task", pid) == expected


def test_edited_enquiry_replaces_generated_text():
    facts, res = _mei()
    md = a.render_markdown(a.prepare_plan(res, facts), edited_enquiry="My own words.")
    assert "My own words." in md
