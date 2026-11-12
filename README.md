# VERA — your next step in BC

A bilingual financial and settlement **preparation guide** for newcomers across British Columbia, including students.

**[Open the public website](https://vera-newcomer-guide.fondfoam.chatgpt.site)** · [Project presentation](https://chatgpt.com/space/page_d14459ce272081919fc31ab5d7062b42) · [Implementation status](docs/RELEASE.md)

Choose one or more needs, confirm relevant details, and leave with a source-backed plan and editable, unsent enquiries. Coverage includes **settlement, education funding, banking, newcomer taxes and benefits**. English and French preserve the same facts and task progress. Specific institution records cover SFU and UBC Vancouver; other institutions receive an explicit handoff.

## Use it now — offline guidance

Python 3.11+; no packages, API key or sign-in required:

```bash
python run.py
```

Open `http://127.0.0.1:8000`. Use `--port 8080` for another port, or `py run.py` on Windows. The public website uses this offline browser workflow. It does **not** run a live AI service.

- Select multiple topics and a priority; only relevant optional details appear.
- Edit a fact without losing unrelated completed tasks or personal notes. Changed work is flagged for review.
- Inspect 19 official source records and their original summaries, locators and review status.
- Edit tasks and enquiries; nothing is sent or submitted.
- Download a readable Markdown plan, or a version 2 JSON file to resume later. Import validates fields, known sources and official destinations, then checks current catalog versions and age.
- Answers stay in page memory. No analytics, automatic local storage, accounts or document uploads. A refresh clears the page unless you exported your plan.

## Optional AI API — setup and limitations

The new Python API is included, but a **real provider smoke test has not passed: credentials were unavailable**. Public Sites hosting currently serves static files and cannot run this Python API. Online public use requires a separately hosted, same-origin Python application over HTTPS. Do not put a key in the frontend or configure an arbitrary browser-side provider URL.

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-api.txt
python scripts/build_web.py
# Export ANTHROPIC_API_KEY and VERA_MODEL securely in your environment.
# VERA_ORIGIN must exactly match your browser origin.
python -m uvicorn server:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
```

The frontend discovers the API and offers an explicit consent choice only when a model and key are configured. The Anthropic adapter can interpret new wording, select bounded retrieval/catalog tools, propose facts for confirmation, and return cited explanations. A separate model support check rejects unsupported output; it is **not independent policy verification**. Tool events describe operations actually executed. Failure preserves the plan and offers offline guidance.

Single-process, cookie-bound sessions expire after 60 idle minutes. Mutations enforce origin, size, rate, version and schema checks. Provider requests have repetition, tool-count, request-count, conservative token-reservation and timeout limits. Configure `.env.example` values in the environment; the app does not automatically load that file. See [API and deployment](docs/API.md).

Test a configured provider with fictional data before enabling it for visitors:

```bash
python scripts/smoke_live.py --output reports/my_live_smoke.json
```

## Verify and maintain sources

```bash
python -m pip install -r requirements-dev.txt
python scripts/build_web.py
python -m pytest -q
node --test tests/*.test.mjs
python scripts/audit_release.py
python scripts/evaluate_v2.py --output reports/my_v2_scores.json
python scripts/check_sources.py --output reports/my_source_status.json
python scripts/build_index.py
```

Current build: **123 Python tests and 29 JavaScript tests passed**; 30 v2 Python/browser plan comparisons matched. Required evidence appeared in the top five results for 20 English and 20 French development queries with a selected-topic filter. These are author-written regression checks on a small corpus, not held-out accuracy, language certification or a user study. See `reports/v2_development_01.json` and `reports/verification_latest.json`.

Retrieval currently uses Unicode-aware lexical ranking over curated bilingual summaries. No embedding model or full-document semantic index has been installed or evaluated. `scripts/build_index.py` creates an auditable SQLite copy of those summaries. The original evidence engine and rules remain available; full source snapshots are excluded pending reuse review. Three inherited integrity tests skip on fresh checkouts until exact snapshots are restored.

```bash
# Optional, allowlisted source capture for a NEW review; never silently changes approvals:
python scripts/ingest_sources.py --ids D09 D11 --output reports/new_capture.json
# Restore exact inherited snapshots where available:
python scripts/restore_snapshots.py
```

A capture is not a policy review. New source bytes need extraction, reconciliation and review before editing catalog records. Builds do not update inspection dates or invent validation metrics.

## Project map

| Area | Files |
|---|---|
| Browser, bilingual UI and offline plans | `web/app.js`, `web/navigator.js`, `web/locales/` |
| Strict v2 contracts, stable tasks and corrections | `api_contracts.py`, `catalog.py`, `planning.py` |
| Optional API and bounded model conversation | `server.py`, `sessions.py`, `settings.py`, `conversation.py`, `grounding.py` |
| Curated official evidence and lexical retrieval | `data/catalog/navigation.json`, `retrieval.py` |
| Original deterministic rules and source integrity | `models.py`, `rules.py`, `agent.py`, `sources.py` |
| Original browser demo | `web/legacy.html`, `web/engine.js` |
| Original optional Streamlit planner | `app.py`, `model_agent.py` |
| Plan and release evidence | `docs/PLAN.md`, `docs/RELEASE.md`, `reports/` |
| Preserved inherited prototype | `baseline/` |

The Streamlit interface remains optional: use a separate environment with `requirements-streamlit.lock`, then `python -m streamlit run app.py`.

## Boundaries and attribution

All eight inherited policy rules remain `RULE_DRAFT`. VERA does not establish eligibility, tax residency, funding amounts, bank acceptance or appointment availability, and it does not file taxes or submit applications. English/French text is implemented but has not received human language review. Chinese, semantic embeddings, a fresh independent evaluation, human studies and policy sign-off remain future work. The slide deck linked above describes the earlier three-pathway release; its ChatGPT access depends on sharing settings.

Built on [Diya Giri’s VERA](https://github.com/diyagiri/VERA). Kopal Chaudhary’s inherited thesis/prototype remains unchanged under `baseline/`. See `NOTICE.md` and `docs/new_work.md`. No new blanket license is asserted over third-party work.
