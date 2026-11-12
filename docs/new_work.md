# Attribution and new-work list

## Inherited work
- Thesis and prototype code by Kopal Chaudhary (supplied). Kept unchanged in `baseline/`, tag `baseline-v0`.
- All 8 inherited files (app.py, chatbot.py, ingest.py, ingest_fixed.py, evaluate.py, ingest_paragraph.py, requirements.txt, README.txt) were copied unchanged from the Claude Project files on 2026-11-05. The plan's note that the last three were missing was wrong; they were found in the Project.
- handbook.pdf (employer handbook) is excluded from the repository until reuse rights are confirmed.

## New work in this repository (update as you build)
- models.py - data contracts (2026-11-05)
- data/manifest.json - source catalog draft (2026-11-05)
- data/fixtures/personas.json - fictional personas (2026-11-05)
- sources.py - manifest load/save, versioned snapshot capture, SHA-256 verify (2026-11-05)
- tests/test_sources.py - capture/verify tests with no network (2026-11-05)
- capture_sources.ps1 - one-shot capture of S1-S5 (2026-11-05)
- extract.py - HTML snapshot to text; exact evidence-span matching (2026-11-05)
- data/rules/rules.json - 8 RULE_DRAFT rules with verbatim evidence spans and source hashes (2026-11-05)
- models.py - added naturalized_citizen fact (S2) and load_rules() (2026-11-05)
- tests/test_rules_data.py - rule/evidence integrity tests (2026-11-05)
- docs/reuse_terms.md - per-source reuse terms and handling (2026-11-05)
- rules.py - deterministic evaluators for 8 rules, approval gate, aggregation, correction re-run (2026-11-05)
- models.py - RuleResult.logic_outcome/gated/fact_version; facts_from_dict() (2026-11-05)
- tests/test_rules_engine.py - persona, correction, gating and wording tests (2026-11-05)
- demo_rules.py - terminal demo of a persona journey without an LLM (2026-11-05)
- data/fixtures/screening_cases.json - 30 screening cases, 20 dev / 10 held-out (2026-11-05)
- data/fixtures/date_boundaries.json - 10 S4 date-boundary targets; calculator disabled (2026-11-05)
- tests/fixture_runner.py, tests/test_fixtures.py - fixture runner (n/N reporting) and dev-only tests (2026-11-05)
- build_evidence.py, data/evidence.json - 37 verbatim evidence records (8 rule spans, 20 exceptions, 9 context) (2026-11-05)
- sources.py - route_goal, search_sources, resolve/validate evidence, untrusted-excerpt wrapping (2026-11-05)
- tests/test_retrieval.py - routing, out-of-scope handoff, stale version, prompt-injection wrapping (2026-11-05)
- actions.py - checklist + editable enquiry templates, dependency tracking, support check, markdown export (2026-11-05)
- models.py - PlanLine, Plan, QUESTIONS (2026-11-05)
- rules.py - results now cite exact evidence.json records (2026-11-05)
- tests/test_actions.py - plan, correction, invalidation, wording and export tests (2026-11-05)

## Completed application work — 2026-11-11

- `web/`, `scripts/build_web.py`, `run.py`: responsive dependency-free UI, generated Python rule tables, questions/corrections, source provenance, fictional demos, editable tasks, downloads and actual event trace.
- `agent.py`, `app.py`, `model_agent.py`: bounded deterministic orchestration, Streamlit adapter and optional consent-based model tool planner. No live model connection claimed.
- `rules.py`, `models.py`: complete approval/freshness gates, federal-exception category, corrected dependencies and source capture timestamp.
- `actions.py`: safe source-linked handoff tasks and self-reported enquiry context, including useful output while rules remain draft.
- `sources.py`: settlement routing fix and invalidation on changed captures. `build_evidence.py`: current captures and supporting spans reconciled while preserving draft status.
- `evaluate.py`, `tests/`, `reports/`: frozen evaluations, 10 scripted journeys, browser/core parity, validation limits and preserved failure history.
- `docs/`: setup, architecture, demo, contract changes and explicit release gates. `baseline/` remains unchanged.
