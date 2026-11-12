"""Deterministic screening engine. No LLM, no network.

Each rule_id has one evaluator returning (outcome, reason, missing_inputs).
check_rules() applies the approval gate: a rule that is not RULE_APPROVED is
displayed as review_required unless allow_draft=True (used by fixture tests).
None of the outputs mean approved, entitled or guaranteed access.
"""
from __future__ import annotations

from datetime import date
from typing import Callable, Optional

from models import (AggregateState, ApprovalState, Facts, ProgramId, ProgramResult,
                    RuleOutcome, RuleRecord, RuleResult, StatusCategory, TriState,
                    load_rules)

O = RuleOutcome
S = StatusCategory
Eval = Callable[[Facts, date], tuple[RuleOutcome, str, list[str]]]

PERMITS = {S.STUDY_PERMIT, S.WORK_PERMIT}


def _status(f: Facts) -> Optional[StatusCategory]:
    return None if f.status_category in (None, S.PREFER_NOT_TO_SAY) else f.status_category


def _unknown_status():
    return O.UNKNOWN, "Status category not provided.", ["status_category"]


# ---------- STU-01 StudentAid BC ----------

def stu01_r1(f: Facts, as_of: date):
    st = _status(f)
    if st is None:
        return _unknown_status()
    if st in {S.CITIZEN, S.PERMANENT_RESIDENT, S.PROTECTED_PERSON}:
        return O.PASS, "Status category is one listed in the StudentAid BC basic criteria.", []
    if st in PERMITS:
        return O.FAIL, "A permit alone does not meet the StudentAid BC status criterion.", []
    return O.REVIEW_REQUIRED, "Status category not covered by reviewed logic.", []


def stu01_r2(f: Facts, as_of: date):
    return O.REVIEW_REQUIRED, "Residency definition not reviewed; StudentAid BC decides residency.", []


def stu01_r3(f: Facts, as_of: date):
    return (O.REVIEW_REQUIRED,
            "Program, financial need and academic progress are assessed by StudentAid BC.", [])


# ---------- NEW-02 BC Newcomer Services Program ----------

def new02_r1(f: Facts, as_of: date):
    st = _status(f)
    if st is None:
        return _unknown_status()
    if st in PERMITS:
        return O.PASS, "Permit category is listed for BC NSP.", []
    if st == S.CITIZEN:
        if f.naturalized_citizen == TriState.YES:
            return O.PASS, "Naturalized Canadian citizens are listed for BC NSP.", []
        if f.naturalized_citizen == TriState.NO:
            return O.FAIL, "BC NSP lists naturalized citizens only.", []
        return O.UNKNOWN, "Whether the citizen is naturalized is not known.", ["naturalized_citizen"]
    if st in {S.PERMANENT_RESIDENT, S.PROTECTED_PERSON}:
        return O.FAIL, "Not a listed BC NSP category; see federal settlement services.", []
    return (O.REVIEW_REQUIRED,
            "May be a listed category not modeled (provincial nominee, CUAET, refugee claimant).", [])


def new02_r2(f: Facts, as_of: date):
    if _status(f) != S.STUDY_PERMIT:
        return O.PASS, "Not applicable: not on a study permit.", []
    if f.is_post_secondary_student == TriState.UNKNOWN:
        return O.UNKNOWN, "Whether you are a post-secondary student is not known.", ["is_post_secondary_student"]
    if f.is_post_secondary_student == TriState.NO:
        return O.REVIEW_REQUIRED, "Study permit holder who is not post-secondary: not a listed category.", []
    if f.institution_offers_service == TriState.YES:
        return O.FAIL, "Your institution offers this service; BC NSP lists students only when it does not.", []
    if f.institution_offers_service == TriState.NO:
        return O.PASS, "Your institution does not offer this service.", []
    return (O.UNKNOWN, "Whether your institution offers this service is not known.",
            ["institution_offers_service"])


# ---------- NEW-03 Federal settlement services ----------

def new03_r1(f: Facts, as_of: date):
    st = _status(f)
    if st is None:
        return _unknown_status()
    if st in {S.PERMANENT_RESIDENT, S.PROTECTED_PERSON}:
        return O.PASS, "Status category is listed for IRCC settlement services.", []
    if st in PERMITS:
        if f.federal_exception == TriState.UNKNOWN:
            return O.UNKNOWN, "Some temporary residents have special pathways. Confirm with IRCC or a provider if one applies.", ["federal_exception"]
        if f.federal_exception == TriState.YES:
            return O.REVIEW_REQUIRED, "A special pathway may apply; its conditions need provider confirmation.", []
        return O.FAIL, "A permit alone is not a general route; you reported that no special pathway applies.", []
    if st == S.CITIZEN:
        return (O.FAIL, "Not a general IRCC settlement route; listed programs and pathways were not checked.", [])
    return O.REVIEW_REQUIRED, "Status category not covered by reviewed logic.", []


def new03_r2(f: Facts, as_of: date):
    if _status(f) != S.PERMANENT_RESIDENT:
        return O.PASS, "Not applicable: not a permanent resident.", []
    if f.pr_class is None:
        return O.UNKNOWN, "PR class not provided.", ["pr_class"]
    if f.pr_class != "economic":
        return O.PASS, "Not applicable: not an economic-class PR.", []
    if f.pr_landing_date is None:
        return O.UNKNOWN, "Date you became a PR not provided.", ["pr_landing_date"]
    return (O.REVIEW_REQUIRED,
            "Economic-class time limit applies; date calculator not approved. Check official guidance.", [])


def new03_r3(f: Facts, as_of: date):
    if _status(f) != S.PERMANENT_RESIDENT:
        return O.PASS, "Not applicable: not a permanent resident.", []
    if f.pr_class is None:
        return O.UNKNOWN, "PR class not provided.", ["pr_class"]
    if f.pr_class in {"family", "refugee"}:
        return O.PASS, "No time limit listed for this PR class.", []
    if f.pr_class == "economic":
        return O.PASS, "Covered by NEW-03-R2.", []
    return O.REVIEW_REQUIRED, "PR class not covered by reviewed logic.", []


EVALUATORS: dict[str, Eval] = {
    "STU-01-R1": stu01_r1, "STU-01-R2": stu01_r2, "STU-01-R3": stu01_r3,
    "NEW-02-R1": new02_r1, "NEW-02-R2": new02_r2,
    "NEW-03-R1": new03_r1, "NEW-03-R2": new03_r2, "NEW-03-R3": new03_r3,
}

NEXT_ACTION: dict[AggregateState, str] = {
    AggregateState.BLOCKER_FOUND:
        "A checked criterion is not met. Review the reason and the official page, and consider the other routes shown.",
    AggregateState.NEEDS_INFORMATION:
        "Answer the missing question to continue screening, or skip it and contact the official source.",
    AggregateState.NEEDS_OFFICIAL_REVIEW:
        "VERA cannot screen this reliably. Use the official page or contact a provider to confirm.",
    AggregateState.NO_BLOCKER_IN_CHECKED:
        "No blocker was found in the criteria VERA checked. The official assessment still decides; prepare your questions for the provider.",
}


def aggregate(outcomes: list[RuleOutcome]) -> AggregateState:
    if O.FAIL in outcomes:
        return AggregateState.BLOCKER_FOUND
    if O.UNKNOWN in outcomes:
        return AggregateState.NEEDS_INFORMATION
    if O.REVIEW_REQUIRED in outcomes:
        return AggregateState.NEEDS_OFFICIAL_REVIEW
    return AggregateState.NO_BLOCKER_IN_CHECKED


_SPAN_IDS: Optional[dict[str, str]] = None


def _rule_span_ids() -> dict[str, str]:
    """rule_id -> evidence_id of that rule's verbatim span in data/evidence.json."""
    global _SPAN_IDS
    if _SPAN_IDS is None:
        try:
            from sources import load_evidence
            _SPAN_IDS = {e["rule_id"]: e["evidence_id"] for e in load_evidence() if e["kind"] == "rule_span"}
        except FileNotFoundError:
            _SPAN_IDS = {}
    return _SPAN_IDS


def _evidence_id(r: RuleRecord) -> str:
    """Cite the exact catalog record; fall back to source@version if the catalog lacks it."""
    return _rule_span_ids().get(r.rule_id) or f"{r.source_id}@{(r.source_version or 'unversioned')[:8]}"


def approval_problem(rule: RuleRecord, as_of_date: date) -> str | None:
    """Fail closed on incomplete sign-off or missing/stale supporting evidence."""
    from sources import load_manifest, verify_snapshot, validate_evidence
    if rule.approval_state != ApprovalState.RULE_APPROVED.value:
        return "Rule awaiting independent review."
    if not rule.author or not rule.reviewer or rule.author.casefold() == rule.reviewer.casefold():
        return "Independent reviewer sign-off is missing."
    if not rule.reviewed_on or not rule.test_ids or not rule.coverage_limit:
        return "Review date, signed-off tests or coverage limits are missing."
    try:
        if date.fromisoformat(rule.reviewed_on) > as_of_date:
            return "Review is later than the requested assessment date."
        if rule.effective_from and as_of_date < date.fromisoformat(rule.effective_from):
            return "Rule is not effective on the requested date."
        if rule.effective_to and as_of_date > date.fromisoformat(rule.effective_to):
            return "Rule has expired."
    except ValueError:
        return "Invalid rule review or effective date."
    src = next((s for s in load_manifest() if s.source_id == rule.source_id), None)
    if not src or src.sha256 != rule.source_version or not verify_snapshot(src):
        return "Source snapshot is unavailable, changed or unverifiable."
    try:
        age = (as_of_date - date.fromisoformat(src.checked_on or "")).days
        if age < 0 or age > 30:
            return "Source needs a fresh review for this date (30-day release policy)."
    except ValueError:
        return "Source review date is missing."
    if not validate_evidence(_evidence_id(rule))[0]:
        return "Supporting excerpt does not match the current source version."
    return None


def check_rules(program_id: str, facts: Facts, as_of_date: date,
                rules: Optional[list[RuleRecord]] = None,
                allow_draft: bool = False) -> ProgramResult:
    rules = load_rules() if rules is None else rules
    prog = [r for r in rules if r.program_id == program_id]
    results: list[RuleResult] = []
    for r in prog:
        fn = EVALUATORS.get(r.rule_id)
        if fn is None:
            logic, reason, missing = O.REVIEW_REQUIRED, "No reviewed logic for this rule.", []
        else:
            logic, reason, missing = fn(facts, as_of_date)
        problem = approval_problem(r, as_of_date)
        gated = bool(problem) and not allow_draft
        shown = O.REVIEW_REQUIRED if gated else logic
        if gated:
            reason = f"{problem} (Draft logic: {reason})"
        results.append(RuleResult(rule_id=r.rule_id, outcome=shown, reason=reason,
                                  missing_inputs=[] if gated else missing,
                                  evidence_ids=[_evidence_id(r)], logic_outcome=logic,
                                  gated=gated, fact_version=facts.version))
    if not prog:
        results.append(RuleResult(rule_id=f"{program_id}-NONE", outcome=O.REVIEW_REQUIRED,
                                  reason="No rules encoded for this program.", fact_version=facts.version))
    state = aggregate([x.outcome for x in results])
    missing = sorted({m for x in results for m in x.missing_inputs})
    unresolved = [e for r in prog if r.exceptions for e in r.exceptions] if state == AggregateState.BLOCKER_FOUND else []
    return ProgramResult(program_id=program_id, as_of_date=as_of_date.isoformat(),
                         fact_version=facts.version, state=state, rule_outcomes=results,
                         missing_inputs=missing,
                         evidence_ids=sorted({e for x in results for e in x.evidence_ids}),
                         unresolved_exceptions=unresolved, next_action=NEXT_ACTION[state])


def check_all(facts: Facts, as_of_date: date, allow_draft: bool = False,
              rules: Optional[list[RuleRecord]] = None) -> dict[str, ProgramResult]:
    rules = load_rules() if rules is None else rules
    return {p.value: check_rules(p.value, facts, as_of_date, rules, allow_draft) for p in ProgramId}


def affected_programs(changed_field: str, rules: Optional[list[RuleRecord]] = None) -> list[str]:
    rules = load_rules() if rules is None else rules
    if changed_field == "as_of_date":
        return [p.value for p in ProgramId]
    return sorted({r.program_id for r in rules if changed_field in r.required_inputs})


def rerun_affected(previous: dict[str, ProgramResult], facts: Facts, changed_field: str,
                   as_of_date: date, allow_draft: bool = False,
                   rules: Optional[list[RuleRecord]] = None) -> tuple[dict[str, ProgramResult], list[str]]:
    """Re-run only programs whose rules depend on changed_field.
    Returns (new results, program_ids whose aggregate state changed)."""
    rules = load_rules() if rules is None else rules
    new = dict(previous)
    for pid in affected_programs(changed_field, rules):
        new[pid] = check_rules(pid, facts, as_of_date, rules, allow_draft)
    changed = sorted(pid for pid in new if pid in previous and new[pid].state != previous[pid].state)
    return new, changed
