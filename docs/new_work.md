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
