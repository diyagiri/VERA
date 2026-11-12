"""Strict v2 API and portable-plan contracts; legacy models remain unchanged."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Topic = Literal['settlement', 'education', 'banking', 'taxes', 'benefits']
Locale = Literal['en', 'fr']
Completion = Literal['todo', 'done', 'dismissed']
Readiness = Literal['ready', 'needs_information', 'needs_official_confirmation', 'stale']
FACTS = {
    'province': ['BC', 'other', 'unknown', 'declined'],
    'city': None,
    'student': ['yes', 'no', 'unknown', 'declined'],
    'institution': ['sfu', 'ubc_vancouver', 'ubc_okanagan', 'other', 'unknown', 'declined'],
    'institution_service': ['yes', 'no', 'unknown', 'declined'],
    'status': ['study_permit', 'work_permit', 'permanent_resident', 'protected_person', 'citizen', 'other', 'unknown', 'declined'],
    'children': ['yes', 'no', 'unknown', 'declined'],
}

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)

class Fact(Strict):
    value: str = Field(max_length=80)
    state: Literal['unknown', 'declined', 'proposed', 'confirmed'] = 'confirmed'
    version: int = Field(default=1, ge=0)
    confirmed_at: str | None = None

class Profile(Strict):
    facts: dict[str, Fact] = Field(default_factory=dict)
    goals: list[Topic] = Field(default_factory=list, max_length=5)
    priority: Topic | None = None

    @model_validator(mode='after')
    def check_profile(self):
        if len(set(self.goals)) != len(self.goals):
            raise ValueError('Duplicate goals')
        if self.priority and self.priority not in self.goals:
            raise ValueError('Priority must be a selected goal')
        for key, fact in self.facts.items():
            if key not in FACTS or (FACTS[key] is not None and fact.value not in FACTS[key]):
                raise ValueError('Unknown fact or value')
            if key == 'city' and any(c.isdigit() for c in fact.value):
                raise ValueError('Use a city name, not an address')
            if fact.value in ('unknown', 'declined') and fact.state != fact.value:
                raise ValueError('Unknown and declined facts must retain their state')
        return self

class ActionTask(Strict):
    id: str = Field(max_length=100)
    program_id: str = Field(max_length=60)
    topic: Topic
    group: Literal['prepare', 'act', 'ask']
    text: str = Field(max_length=1600)
    destination: str = Field(max_length=500)
    evidence: list[str] = Field(max_length=8)
    dependencies: list[str] = Field(max_length=8)
    dependency_values: dict[str, str] = Field(default_factory=dict)
    source_versions: dict[str, str] = Field(default_factory=dict)
    readiness: Readiness = 'needs_official_confirmation'
    completion: Completion = 'todo'
    user_text: str | None = Field(default=None, max_length=1600)
    review_reason: Literal['facts_changed', 'source_changed', 'source_stale', 'route_removed'] | None = None
    due_date: None = None  # No cataloged deadlines in this release.

class Enquiry(Strict):
    program_id: str
    text: str = Field(max_length=4000)
    user_text: str | None = Field(default=None, max_length=4000)
    dependencies: list[str]
    dependency_values: dict[str, str]
    source_versions: dict[str, str]
    needs_review: bool = False

class Plan(Strict):
    schema_version: Literal[2] = 2
    profile_version: int = Field(default=0, ge=0)
    plan_version: int = Field(default=0, ge=0)
    as_of: str
    locale: Locale = 'en'
    tasks: list[ActionTask] = Field(default_factory=list, max_length=100)
    enquiries: list[Enquiry] = Field(default_factory=list, max_length=20)
    source_versions: dict[str, str] = Field(default_factory=dict)
    notes: str = Field(default='', max_length=4000)

class PortablePlan(Strict):
    schema_version: Literal[2] = 2
    goal: str = Field(default='', max_length=2000)
    profile: Profile
    plan: Plan

class Versions(Strict):
    profile_version: int = Field(ge=0)
    plan_version: int = Field(ge=0)

class SessionCreate(Strict):
    consent: bool = False
    locale: Locale = 'en'
    portable: PortablePlan | None = None

class Message(Versions):
    message: str = Field(min_length=1, max_length=2000)
    locale: Locale = 'en'
    idempotency_key: str = Field(min_length=8, max_length=100, pattern=r'^[A-Za-z0-9_-]+$')

class ProfilePatch(Versions):
    profile: Profile
    locale: Locale = 'en'

class TaskPatch(Versions):
    completion: Completion | None = None
    user_text: str | None = Field(default=None, max_length=1600)
    accept_revision: bool = False

class PlanPatch(Versions):
    notes: str | None = Field(default=None, max_length=4000)
    enquiry_id: str | None = None
    enquiry_text: str | None = Field(default=None, max_length=4000)

class ImportRequest(Versions):
    portable: PortablePlan

class ProposedFact(Strict):
    field: str
    value: str = Field(max_length=80)

class GroundedBlock(Strict):
    text: str = Field(min_length=1, max_length=1200)
    citations: list[str] = Field(min_length=1, max_length=8)

class ModelTurn(Strict):
    topics: list[Topic] = Field(max_length=5)
    proposed_facts: list[ProposedFact] = Field(max_length=8)
    blocks: list[GroundedBlock] = Field(max_length=4)
    questions: list[str] = Field(max_length=2)
    program_ids: list[str] = Field(max_length=12)
