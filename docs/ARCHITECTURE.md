# VERA architecture

## Public offline mode

`web/app.js` renders the existing VERA visual system with `web/locales/en.json` and `fr.json`. `web/navigator.js` owns browser-memory facts and stable preparation tasks. `data/catalog/navigation.json` is the shared versioned catalog; `scripts/build_web.py` copies it and the UI into `dist/` and emits `runtime.json` with `api_available: false` for static hosting.

`buildPlan` and Python `planning.build_plan` consume the same records. A 30-case comparison verifies complete plan equality. Each task stores fact dependencies and source versions, separates readiness from completion and retains user edits. Import validates known route IDs, destinations and schema, then rebuilds against the current catalog. Locale changes preserve facts/IDs and render the same underlying task meaning. Page memory is the only implicit persistence.

## Optional online mode

FastAPI `server.py` serves the same files and overrides `runtime.json` to advertise the API. The browser checks capabilities, requests explicit consent and uses cookie-bound sessions. `conversation.py` invokes Anthropic only when configured, executes bounded catalog/retrieval tools and validates a structured turn. Proposed facts are displayed for user confirmation before entering the shared planner. Source references are restricted to current evidence retrieved in that turn. A second model support review is a diagnostic, not independent validation.

The API uses the canonical Python planner, while static guidance uses its tested browser equivalent. The current retrieval implementation reads the small curated corpus in memory and ranks Unicode lexical matches across English/French. `scripts/build_index.py` creates a SQLite audit/index artifact; no hosted vector service or embedding model is used. Capture and indexing are separate from runtime. New captures cannot change policy approvals or inspection dates automatically.

## Preserved legacy layer

`rules.py`, `models.py`, `agent.py`, `actions.py`, `sources.py`, `model_agent.py`, the Streamlit interface and `baseline/` remain intact. `scripts/build_web.py` still compiles the original eight evaluator tables for `legacy.html`. No original rule was promoted beyond `RULE_DRAFT`. See `docs/RELEASE_v1.md` for its historical checks.

## Hosting boundary

The current public Sites deployment is static. Python API hosting is separate work requiring infrastructure and model configuration; it is not silently replaced with browser-side credentials. The public site remains accessible without ChatGPT sign-in. The existing native slide deck has separate ChatGPT sharing settings and describes the earlier release.
