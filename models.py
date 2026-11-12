"""VERA data contracts (Source Registry v2, section 4).

Stdlib only so rules and tests run without an LLM or network.
Every record mirrors a schema from the registry; do not add fields
without updating docs/data_contracts.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date
from enum import Enum
from typing import Optional


# ---------- enums ----------

class ProgramId(str, Enum):
    STU_01 = "STU-01"   # StudentAid BC
    NEW_02 = "NEW-02"   # BC Newcomer Services Program
    NEW_03 = "NEW-03"   # Federal settlement services


class ReviewStatus(str, Enum):
    """Source readiness."""
    SOURCE_CHECKED = "SOURCE_CHECKED"


class ApprovalState(str, Enum):
    """Rule readiness. Live screening requires RULE_APPROVED."""
    RULE_DRAFT = "RULE_DRAFT"
    RULE_APPROVED = "RULE_APPROVED"


class RuleOutcome(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"
    REVIEW_REQUIRED = "review_required"


class AggregateState(str, Enum):
    BLOCKER_FOUND = "blocker_found"
    NO_BLOCKER_IN_CHECKED = "no_blocker_in_checked_criteria"
    NEEDS_INFORMATION = "needs_information"
    NEEDS_OFFICIAL_REVIEW = "needs_official_review"


class StatusCategory(str, Enum):
    """Asked as a category -- never collect SIN, permit or PR card numbers."""
    STUDY_PERMIT = "study_permit"
    WORK_PERMIT = "work_permit"
    PERMANENT_RESIDENT = "permanent_resident"
    PROTECTED_PERSON = "protected_person"
    CITIZEN = "citizen"
    OTHER = "other"
    PREFER_NOT_TO_SAY = "prefer_not_to_say"


class TriState(str, Enum):
    YES = "yes"
    NO = "no"
    UNKNOWN = "unknown"


# ---------- records ----------

@dataclass
class SourceRecord:
    source_id: str                      # "S1".."S5"
    program_id: Optional[str]           # None for CONTEXT (S5)
    publisher: str
    canonical_url: Optional[str]        # null until copied from Source Registry v2
    title: str
    evidence_section: str
    checked_on: Optional[str]           # ISO date the team inspected it
    page_modified_on: Optional[str]     # as displayed on page; null if not shown
    effective_period: Optional[str]     # policy period; NOT the same as page_modified_on
    snapshot_path: Optional[str]
    sha256: Optional[str]
    reuse_status: str = "unreviewed"
    review_status: str = ReviewStatus.SOURCE_CHECKED.value
    captured_at: Optional[str] = None


@dataclass
class RuleRecord:
    rule_id: str
    program_id: str
    condition: str                      # plain-language condition
    required_inputs: list[str]
    source_id: str
    source_version: Optional[str]       # sha256 of snapshot once captured
    evidence_span: Optional[str]        # exact supporting text from snapshot
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    exceptions: list[str] = field(default_factory=list)
    coverage_limit: str = ""
    reviewer: Optional[str] = None      # second contributor, never the author
    reviewed_on: Optional[str] = None
    test_ids: list[str] = field(default_factory=list)
    approval_state: str = ApprovalState.RULE_DRAFT.value
    author: Optional[str] = None


@dataclass
class RuleResult:
    rule_id: str
    outcome: RuleOutcome              # what is displayed (after the approval gate)
    reason: str
    missing_inputs: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    logic_outcome: Optional[RuleOutcome] = None   # what the rule logic says, before gating
    gated: bool = False               # True when a non-approved rule was forced to review_required
    fact_version: int = 0


@dataclass
class ProgramResult:
    program_id: str
    as_of_date: str
    fact_version: int
    state: AggregateState
    rule_outcomes: list[RuleResult]
    missing_inputs: list[str]
    evidence_ids: list[str]
    unresolved_exceptions: list[str]
    next_action: str


@dataclass
class ProviderLead:
    provider_name: str
    directory_source: str
    locality: Optional[str]
    linked_url: Optional[str]
    last_checked: Optional[str]
    service_verified: bool = False
    availability_status: str = "unconfirmed"


@dataclass
class Facts:
    """Session-only user facts. Bumping version invalidates dependent results."""
    status_category: Optional[StatusCategory] = None
    naturalized_citizen: TriState = TriState.UNKNOWN   # S2: NSP covers naturalized citizens only
    is_post_secondary_student: TriState = TriState.UNKNOWN
    institution_offers_service: TriState = TriState.UNKNOWN
    pr_class: Optional[str] = None           # "economic" | "family" | "refugee" | "other" | None=unknown
    pr_landing_date: Optional[date] = None   # month precision is enough
    bc_resident: TriState = TriState.UNKNOWN
    goal: str = ""
    version: int = 1
    federal_exception: TriState = TriState.UNKNOWN

    def update(self, field_name: str, value) -> "Facts":
        if not hasattr(self, field_name) or field_name == "version":
            raise ValueError(f"Unknown fact field: {field_name}")
        setattr(self, field_name, value)
        self.version += 1
        return self


def to_dict(obj) -> dict:
    """JSON-safe dict for dataclasses containing enums/dates."""
    def conv(v):
        if isinstance(v, Enum):
            return v.value
        if isinstance(v, date):
            return v.isoformat()
        if isinstance(v, list):
            return [conv(x) for x in v]
        if isinstance(v, dict):
            return {k: conv(x) for k, x in v.items()}
        return v
    return conv(asdict(obj))


RULES_PATH = "data/rules/rules.json"


def load_rules(path: str = RULES_PATH) -> list[RuleRecord]:
    import json
    from pathlib import Path
    p = Path(path)
    if not p.is_absolute():
        p = Path(__file__).resolve().parent / p
    data = json.loads(p.read_text(encoding="utf-8"))
    return [RuleRecord(**r) for r in data["rules"]]


def facts_from_dict(d: dict, goal: str = "") -> Facts:
    """Build Facts from fixture/UI JSON (string values)."""
    def tri(v):
        return TriState(v) if v else TriState.UNKNOWN
    return Facts(
        status_category=StatusCategory(d["status_category"]) if d.get("status_category") else None,
        naturalized_citizen=tri(d.get("naturalized_citizen")),
        is_post_secondary_student=tri(d.get("is_post_secondary_student")),
        institution_offers_service=tri(d.get("institution_offers_service")),
        pr_class=d.get("pr_class"),
        pr_landing_date=date.fromisoformat(d["pr_landing_date"]) if d.get("pr_landing_date") else None,
        bc_resident=tri(d.get("bc_resident")),
        federal_exception=tri(d.get("federal_exception")),
        goal=goal,
    )


# ---------- plan (Step 7) ----------

@dataclass
class PlanLine:
    line_id: str
    program_id: Optional[str]
    kind: str                      # "task" | "enquiry_context" | "enquiry_question" | "handoff"
    text: str
    depends_on: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    fact_version: int = 0


@dataclass
class Plan:
    as_of_date: str
    fact_version: int
    lines: list[PlanLine]
    removed: list[str] = field(default_factory=list)
    stale: bool = False


# One question per fact. Categories only; never ask for identifying numbers.
QUESTIONS: dict[str, str] = {
    "status_category": "Which best describes your current status in Canada? (study permit, work permit, "
                       "permanent resident, protected person, Canadian citizen, other, prefer not to say)",
    "naturalized_citizen": "Did you become a Canadian citizen after immigrating (naturalized)?",
    "is_post_secondary_student": "Are you a student at a college or university in B.C.?",
    "institution_offers_service": "Does your college or university offer newcomer or settlement services "
                                  "to international students? (yes / no / not sure)",
    "pr_class": "Which kind of program made you a permanent resident? (economic, family, refugee, other)",
    "pr_landing_date": "In which month and year did you become a permanent resident?",
    "bc_resident": "Do you currently live in British Columbia?",
    "federal_exception": "Could an IRCC exception or special pathway apply to you? (yes / no / not sure)",
}
