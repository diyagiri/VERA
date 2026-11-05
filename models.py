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
    outcome: RuleOutcome
    reason: str
    missing_inputs: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)


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
    is_post_secondary_student: TriState = TriState.UNKNOWN
    institution_offers_service: TriState = TriState.UNKNOWN
    pr_class: Optional[str] = None           # "economic" | "family" | "refugee" | "other" | None=unknown
    pr_landing_date: Optional[date] = None   # month precision is enough
    bc_resident: TriState = TriState.UNKNOWN
    goal: str = ""
    version: int = 1

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
