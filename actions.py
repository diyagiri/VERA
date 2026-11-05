"""Turn screening results into a checklist and an editable provider enquiry.

Every line records the facts it depends on and the evidence it rests on, so a
correction can remove exactly the affected lines. Nothing here sends anything.
"""
from __future__ import annotations

from typing import Optional

from models import (AggregateState, Facts, Plan, PlanLine, ProgramResult, QUESTIONS,
                    StatusCategory, TriState, load_rules)

A = AggregateState
PROGRAM_ORDER = ["STU-01", "NEW-02", "NEW-03"]
ANSWER_PREFIX = "Answer: "
RULES_INPUTS = "__program_rules__"   # placeholder: union of that program's required_inputs
MISSING = "__missing__"              # placeholder: one "Answer:" task per missing fact

# (program, state) -> {"tasks": [...], "questions": [...], "depends_on": [...]}
TEMPLATES: dict[tuple[str, AggregateState], dict] = {
    ("STU-01", A.BLOCKER_FOUND): {
        "tasks": ["Review the StudentAid BC status criterion on the official page.",
                  "Ask your school's financial aid office which funding options apply to your status."],
        "questions": [], "depends_on": ["status_category"]},
    ("STU-01", A.NEEDS_INFORMATION): {"tasks": [MISSING], "questions": [], "depends_on": [MISSING]},
    ("STU-01", A.NEEDS_OFFICIAL_REVIEW): {
        "tasks": ["Check the remaining StudentAid BC criteria on the official page before applying. "
                  "VERA does not estimate funding."],
        "questions": [], "depends_on": [RULES_INPUTS]},
    ("STU-01", A.NO_BLOCKER_IN_CHECKED): {
        "tasks": ["Start the official StudentAid BC application. VERA did not estimate any amount."],
        "questions": [], "depends_on": [RULES_INPUTS]},

    ("NEW-02", A.BLOCKER_FOUND): {
        "tasks": ["Contact your institution's newcomer or international student services first."],
        "questions": [], "depends_on": ["institution_offers_service", "status_category"]},
    ("NEW-02", A.NEEDS_INFORMATION): {"tasks": [MISSING], "questions": [], "depends_on": [MISSING]},
    ("NEW-02", A.NEEDS_OFFICIAL_REVIEW): {
        "tasks": ["Open the BC NSP provider directory and ask a provider to confirm whether you qualify."],
        "questions": ["Could you confirm whether I can use BC NSP services in my situation?"],
        "depends_on": ["status_category"]},
    ("NEW-02", A.NO_BLOCKER_IN_CHECKED): {
        "tasks": ["Choose a provider from the BC NSP 'Find a service provider' directory and contact them."],
        "questions": ["__STUDY_PERMIT_ONLY__Can I use BC NSP services as an international post-secondary "
                      "student whose institution does not offer these services?",
                      "Which of your services can help me (for example English practice or help with finding a job)?",
                      "Are services available online or in person, and in which languages?",
                      "What should I bring to a first appointment?"],
        "depends_on": ["status_category", "institution_offers_service"]},

    ("NEW-03", A.BLOCKER_FOUND): {
        "tasks": ["Federal settlement services are not a general route for your status. If you think a "
                  "listed program or pathway applies to you, ask a provider."],
        "questions": [], "depends_on": ["status_category"]},
    ("NEW-03", A.NEEDS_INFORMATION): {"tasks": [MISSING], "questions": [], "depends_on": [MISSING]},
    ("NEW-03", A.NEEDS_OFFICIAL_REVIEW): {
        "tasks": ["Use the IRCC service finder and ask a provider to confirm your eligibility period."],
        "questions": ["How long can I use your services, based on the date I became a permanent resident?"],
        "depends_on": ["pr_class", "pr_landing_date"]},
    ("NEW-03", A.NO_BLOCKER_IN_CHECKED): {
        "tasks": ["Use the IRCC service finder to choose a provider near you. Do not enter a full address."],
        "questions": ["Which services can you offer me?"],
        "depends_on": ["status_category", "pr_class"]},
}
STUDY_PERMIT_ONLY = "__STUDY_PERMIT_ONLY__"

STATUS_WORDS = {
    StatusCategory.STUDY_PERMIT: "I am currently in Canada on a study permit.",
    StatusCategory.WORK_PERMIT: "I am currently in Canada on a work permit.",
    StatusCategory.PERMANENT_RESIDENT: "I am a permanent resident of Canada.",
    StatusCategory.PROTECTED_PERSON: "I am a protected person in Canada.",
    StatusCategory.CITIZEN: "I am a Canadian citizen.",
}

LIMITS = ("VERA screened only the criteria listed above, using official pages captured on the dates shown. "
          "The official program or provider decides. Nothing was sent to anyone. "
          "VERA does not keep your answers after this session.")

FORBIDDEN_WORDS = ("eligible", "approved", "entitled", "guaranteed")


def _program_inputs(program_id: str) -> list[str]:
    return sorted({i for r in load_rules() if r.program_id == program_id for i in r.required_inputs})


def describe_facts(facts: Facts) -> list[PlanLine]:
    """Context sentences for the enquiry, only from facts the user actually gave."""
    lines: list[PlanLine] = []

    def add(text, dep):
        lines.append(PlanLine(line_id=f"CTX-enquiry_context-{len(lines)}", program_id=None,
                              kind="enquiry_context", text=text, depends_on=[dep],
                              fact_version=facts.version))

    if facts.status_category in STATUS_WORDS:
        add(STATUS_WORDS[facts.status_category], "status_category")
    if facts.is_post_secondary_student == TriState.YES:
        add("I am a post-secondary student in B.C.", "is_post_secondary_student")
    if facts.institution_offers_service == TriState.NO:
        add("My institution does not offer newcomer services to international students.",
            "institution_offers_service")
    return lines


def prepare_plan(results: dict[str, ProgramResult], facts: Facts,
                 as_of_date: Optional[str] = None) -> Plan:
    lines: list[PlanLine] = []
    for pid in PROGRAM_ORDER:
        res = results.get(pid)
        if res is None:
            continue
        tpl = TEMPLATES[(pid, res.state)]
        deps = tpl["depends_on"]
        if deps == [RULES_INPUTS]:
            deps = _program_inputs(pid)
        n = 0
        for task in tpl["tasks"]:
            if task == MISSING:
                for f in res.missing_inputs:
                    lines.append(PlanLine(f"{pid}-task-{n}", pid, "task", ANSWER_PREFIX + QUESTIONS[f],
                                          depends_on=[f], evidence_ids=[], fact_version=facts.version))
                    n += 1
            else:
                lines.append(PlanLine(f"{pid}-task-{n}", pid, "task", task, depends_on=list(deps),
                                      evidence_ids=list(res.evidence_ids), fact_version=facts.version))
                n += 1
        q = 0
        for question in tpl["questions"]:
            if question.startswith(STUDY_PERMIT_ONLY):
                if facts.status_category != StatusCategory.STUDY_PERMIT:
                    continue
                question = question[len(STUDY_PERMIT_ONLY):]
            lines.append(PlanLine(f"{pid}-enquiry_question-{q}", pid, "enquiry_question", question,
                                  depends_on=list(deps), evidence_ids=list(res.evidence_ids),
                                  fact_version=facts.version))
            q += 1
    if any(l.kind == "enquiry_question" for l in lines):
        lines = describe_facts(facts) + lines
    as_of = as_of_date or next((r.as_of_date for r in results.values()), "")
    return Plan(as_of_date=as_of, fact_version=facts.version, lines=lines)


def support_check(plan: Plan) -> Plan:
    """Drop any line whose cited evidence does not resolve to the current approved version."""
    from sources import validate_evidence
    cache: dict[str, bool] = {}
    kept: list[PlanLine] = []
    for line in plan.lines:
        exempt = line.text.startswith(ANSWER_PREFIX) or line.kind == "enquiry_context"
        if not exempt:
            if not line.evidence_ids:
                plan.removed.append(line.text)
                continue
            ok = all(cache.setdefault(i, validate_evidence(i)[0]) for i in line.evidence_ids)
            if not ok:
                plan.removed.append(line.text)
                continue
        kept.append(line)
    plan.lines = kept
    return plan


def invalidate(plan: Plan, changed_field: str) -> Plan:
    plan.lines = [l for l in plan.lines if changed_field not in l.depends_on]
    plan.stale = True
    return plan


def enquiry_text(plan: Plan) -> str:
    ctx = [l.text for l in plan.lines if l.kind == "enquiry_context"]
    qs = [l.text for l in plan.lines if l.kind == "enquiry_question"]
    if not qs:
        return ""
    body = ["Hello,", ""]
    if ctx:
        body += [" ".join(ctx), ""]
    body.append("I would like to ask:")
    body += [f"{i}. {q}" for i, q in enumerate(qs, 1)]
    body += ["", "Thank you,", "[Your name]"]
    return "\n".join(body)


def render_markdown(plan: Plan, edited_enquiry: Optional[str] = None) -> str:
    tasks = [l.text for l in plan.lines if l.kind == "task"]
    enquiry = edited_enquiry if edited_enquiry is not None else enquiry_text(plan)
    out = [f"# VERA plan (as of {plan.as_of_date})", "", "## Checklist"]
    out += [f"- [ ] {t}" for t in tasks] or ["- [ ] No tasks yet."]
    out += ["", "## Draft enquiry to a provider", "",
            enquiry or "No provider questions yet. Answer the open questions above first."]
    out += ["", "## Limits", "", LIMITS, ""]
    return "\n".join(out)
