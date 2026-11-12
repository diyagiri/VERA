"""Bounded, deterministic tool orchestration. No model key or network required.

The browser executes generated decision tables from this same Python rule code.
Each event records an actual operation, never simulated model activity.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from time import perf_counter
from typing import Any

from models import Facts, TriState, StatusCategory, QUESTIONS, facts_from_dict, to_dict
from sources import search_sources, route_goal
from rules import check_rules, affected_programs, EVALUATORS, load_rules
from actions import prepare_guidance

TOOL_SCHEMAS = [
    {"name": "search_sources", "description": "Retrieve bounded official-source records for the goal.", "input_schema": {"type": "object", "properties": {"goal": {"type": "string", "maxLength": 600}}, "required": ["goal"], "additionalProperties": False}},
    {"name": "check_rules", "description": "Evaluate versioned rules; independent approval gates cannot be bypassed.", "input_schema": {"type": "object", "properties": {"program_id": {"enum": ["STU-01", "NEW-02", "NEW-03"]}}, "required": ["program_id"], "additionalProperties": False}},
    {"name": "ask_question", "description": "Ask one relevant category question; skipping is allowed.", "input_schema": {"type": "object", "properties": {"field": {"enum": list(QUESTIONS)}}, "required": ["field"], "additionalProperties": False}},
    {"name": "prepare_plan", "description": "Prepare an editable checklist and unsent enquiry.", "input_schema": {"type": "object", "properties": {}, "additionalProperties": False}},
]

MAX_CALLS = 12
MAX_EVENTS = 80

@dataclass
class Navigator:
    facts: Facts = field(default_factory=Facts)
    as_of: date = field(default_factory=date.today)
    results: dict = field(default_factory=dict)
    events: list = field(default_factory=list)
    skipped: set = field(default_factory=set)
    retrieval: dict = field(default_factory=dict)
    plan: dict = field(default_factory=dict)
    changes: list = field(default_factory=list)
    _calls: int = 0

    def _call(self, tool, label, function):
        if self._calls >= MAX_CALLS:
            raise RuntimeError("Tool limit reached. Continue with the official sources.")
        self._calls += 1
        start = perf_counter()
        result = function()
        self.events.append({"tool": tool, "detail": label, "fact_version": self.facts.version,
                            "duration_ms": round((perf_counter()-start)*1000, 3)})
        self.events = self.events[-MAX_EVENTS:]
        return result

    def start(self, goal: str):
        if not isinstance(goal, str) or not goal.strip() or len(goal) > 600:
            raise ValueError("Enter a goal between 1 and 600 characters.")
        self._calls = 0
        self.facts.goal = goal.strip()
        self.retrieval = self._call("search_sources", "Retrieve relevant catalog records", lambda: search_sources(goal))
        self.results = {pid: self._call("check_rules", pid, lambda pid=pid: check_rules(pid, self.facts, self.as_of))
                        for pid in self.retrieval['program_ids']}
        self._plan()
        return self

    def next_question(self):
        if not self.results or self.facts.bc_resident == TriState.NO:
            return None
        fields = ["bc_resident", "status_category"]
        for r in load_rules():
            if r.program_id in self.results:
                fields += EVALUATORS[r.rule_id](self.facts, self.as_of)[2]
        for name in dict.fromkeys(fields):
            value = getattr(self.facts, name)
            missing = value is None or value == TriState.UNKNOWN or value == StatusCategory.PREFER_NOT_TO_SAY
            if missing and name not in self.skipped:
                self._calls = 0
                return self._call("ask_question", name, lambda: {"field": name, "question": QUESTIONS[name]})
        return None

    def answer(self, name: str, value: Any):
        if name not in QUESTIONS:
            raise ValueError("Unsupported fact field.")
        self._calls = 0
        candidate = to_dict(self.facts)
        candidate[name] = value
        # Status corrections invalidate conditional facts and any old draft.
        old_status = self.facts.status_category.value if self.facts.status_category else None
        if name == 'status_category' and old_status != value:
            for f in ['naturalized_citizen','is_post_secondary_student','institution_offers_service','federal_exception','pr_class','pr_landing_date']:
                candidate[f] = None
                self.skipped.discard(f)
        if name == 'is_post_secondary_student' and value != 'yes':
            candidate['institution_offers_service'] = None
            self.skipped.discard('institution_offers_service')
        if name == 'pr_class' and value != 'economic':
            candidate['pr_landing_date'] = None
        if name == 'pr_class' and value not in [None,'economic','family','refugee','other']:
            raise ValueError('Unknown permanent residence class.')
        updated = facts_from_dict(candidate, self.facts.goal)
        if updated.pr_landing_date and updated.pr_landing_date > self.as_of:
            raise ValueError('The PR date cannot be later than the assessment date.')
        updated.version = self.facts.version + 1
        self.facts = updated
        if value in [None,'unknown','prefer_not_to_say']:
            self.skipped.add(name)
        else:
            self.skipped.discard(name)
        affected = affected_programs(name)
        if name == 'status_category':
            affected = list(self.results)
        self.changes = []
        for pid in affected:
            if pid not in self.results:
                continue
            before = to_dict(self.results[pid])
            self.results[pid] = self._call('check_rules', f'{pid}: corrected {name}', lambda pid=pid: check_rules(pid,self.facts,self.as_of))
            after = to_dict(self.results[pid])
            self.changes.append({'program_id':pid,'field':name,'before':before['state'],'after':after['state'],
                                 'criteria_changed':before['rule_outcomes'] != after['rule_outcomes']})
        self._plan()
        return self

    def _plan(self):
        self.plan = self._call('prepare_plan', 'Regenerate checklist and enquiry from current answers',
                              lambda: prepare_guidance(self.results,self.facts,self.as_of.isoformat(),self.retrieval.get('handoff')))

    def export(self):
        return {'facts':to_dict(self.facts),'results':{k:to_dict(v) for k,v in self.results.items()},
                'plan':self.plan,'events':self.events,'changes':self.changes,'as_of_date':self.as_of.isoformat()}
