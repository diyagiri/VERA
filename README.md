# VERA — your next step in BC

A complete runnable **guidance prototype** for newcomers in British Columbia, extending [diyagiri/VERA](https://github.com/diyagiri/VERA) at `f7ea6b9`.

State a goal, answer relevant questions, inspect official sources, correct answers, and leave with an editable checklist and provider enquiry. Three pathways: BC Newcomer Services Program, federal settlement services, and StudentAid BC.

**Release boundary:** all 8 policy rules remain `RULE_DRAFT`. The app provides preparation guidance and official handoffs. Fictional demos expose draft outcomes with prominent labels. No rule has been independently approved, and no eligibility, funding amount, appointment availability or federal service end date is promised.

## Run in one command

Python 3.11 or newer, no packages or API keys required:

```bash
python run.py
```

Open `http://127.0.0.1:8000`. On Windows, use `py run.py` if `python` is unavailable. This builds and serves the polished web interface locally. `--port 8080` chooses another port. Stop with Ctrl+C.

The hosted browser version performs all guidance locally. It has no analytics, transcripts, local storage, database or external model calls. A page refresh clears the session. Downloaded files remain on the user's device.

## Python / Streamlit interface

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-streamlit.lock
python -m streamlit run app.py
```

The Streamlit adapter uses the same Python engine and stores answers in session memory. It offers an **optional** model planner. Export `ANTHROPIC_API_KEY` and `VERA_MODEL` in your environment; select a model available in your account. Explicitly consent in the local UI before sending selected goal/category facts and source metadata to Anthropic. `.env.example` is a reference, not an automatically loaded file. Provider access was not available during this build; the live adapter is unverified. Mock-provider safety tests pass. No secret belongs in the frontend.

## What is included

| Part | Entry point |
|---|---|
| Responsive web interface, editable tasks, downloads, sources, demos | `web/` |
| Canonical deterministic rule evaluators and approval/freshness gates | `rules.py` |
| Shared facts, evidence and result contracts | `models.py` |
| Bounded orchestration, question selection, correction propagation | `agent.py` |
| Optional model tool planner with timeout and repetition limits | `model_agent.py` |
| Checklist, self-reported context, unsent enquiry generation | `actions.py` |
| Source capture, SHA-256 integrity, retrieval and provenance | `sources.py`, `extract.py`, `build_evidence.py` |
| Browser decision tables generated directly from Python evaluators | `scripts/build_web.py` |
| Frozen-output evaluation, screening cases and scripted journeys | `evaluate.py`, `data/fixtures/`, `reports/` |
| Unmodified inherited prototype | `baseline/` |

## Verify

Node 18+ is needed only for JavaScript tests, not for running the app.

```bash
python -m pip install -r requirements-dev.txt
python scripts/build_web.py
python -m pytest -q
node --test tests/web.test.mjs
python scripts/audit_release.py
```

Build-machine results: **93 Python tests, 12 JavaScript tests, 252 Python/browser parity comparisons, 30/30 screening cases and 10/10 scripted journeys**. Full source snapshots were fetched locally and all 37 catalog excerpts validated. These are functional/regression checks, not independent policy validation. The held-out-labelled cases were author-written and exposed during debugging; they are not an unbiased held-out study.

Snapshots are deliberately excluded from distribution pending reuse review. On a fresh checkout, three integrity tests skip until exact snapshots are restored. Restore using `python scripts/restore_snapshots.py`; it fails clearly if fetched bytes differ and never silently changes versions. New captures require explicit evidence reconciliation and independent rule sign-off.

```bash
python evaluate.py freeze --output reports/my_frozen_run.json
python evaluate.py score --input reports/my_frozen_run.json --output reports/my_scores.json
```

Frozen outputs are never overwritten. `reports/evaluation_release.json` is the final measured report. Earlier failed/regression runs are preserved for transparency. Manual-navigation, retrieval-chatbot, and usability comparisons have **not** been performed.

## Before enabling real screening

See `docs/RELEASE.md`. Independent contributors must verify exact source versions, interpretation, exceptions, limits and tests. Populate authentic reviewer information; do not copy test reviewer identities. Source byte integrity alone does not establish policy accuracy or reuse permission. `python scripts/audit_release.py --require-screening` intentionally exits nonzero for this release.

Full snapshots, model keys, transcripts, identity documents and the employer handbook are excluded. The event rubric, inherited-code policy and submission rules still require organizer confirmation. No claims of multilingual validation or measured social impact are made.

## Attribution

Diya Giri's VERA repository supplies the starting catalog, contracts, rules and action groundwork. Kopal Chaudhary's supplied thesis/prototype remains unchanged under `baseline/`, retaining the upstream `baseline-v0` tag in repository history. See `NOTICE.md` and `docs/new_work.md`. No new blanket license is asserted over third-party work.
