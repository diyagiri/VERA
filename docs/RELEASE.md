# VERA v2 release — 11 November 2026 (America/Vancouver)

Implemented against the user-supplied `docs/PLAN.md`, starting from GitHub commit `185e545eb77c0c501d16673318d2bba56f278988`. The original local Sites source had the identical tree `403a8cd0d566fe43cebea0727c41014cea721dd2`. No intervening GitHub change was present at inspection. Original release evidence remains in `RELEASE_v1.md` and the existing reports.

## Delivered

- Five-topic BC-wide guidance: settlement, education, banking, taxes and benefits. Students remain included; the app is not limited to one campus or family benefits.
- English/French UI, source summaries, tasks and enquiry drafts. Language switching preserves task IDs, facts, edits and completion; no human language-review claim.
- Multi-topic intake, explicit priority, confirmation of proposed details and optional relevant profile fields.
- SFU and UBC Vancouver records with scope limits; other campuses and institutions receive a truthful handoff. UBC emergency-funding expenses are bounded. CCB/BC family benefit tasks avoid duplicate applications.
- Stable, dependency-aware tasks: unrelated completed work survives corrections; affected edits are retained and flagged; completed work whose meaning changes is reopened for review.
- Editable unsent enquiries, notes, Markdown export, strict JSON export/import, and source-version/age revalidation. No imported AI consent or executable instructions.
- Optional same-origin FastAPI service, strict v2 schemas, cookie-bound ephemeral sessions, version conflicts, idempotent message retries, origin/size/rate/budget controls and session deletion.
- Bounded Anthropic conversation adapter with actual retrieval/catalog tools, citations, fact proposals and a separate model support-check step. Mocked tests exercise tool execution and failure boundaries.
- 19 official source records and short bilingual paraphrases, aliases for S1–S5, allowlisted capture tooling, source-status reporting and an auditable SQLite lexical index builder. Publisher dates, inspection dates, summary versions and snapshot hashes are separate.
- Updated public-site GitHub link and a labelled link to the existing slide deck. Original browser demo and upstream attribution remain available.

## Measured results

- Baseline before edits: 93 Python tests and 12 JavaScript tests passed locally.
- Updated build: 123 Python tests and 29 JavaScript tests passed, with no skips on this build machine. One upstream Starlette/httpx deprecation warning remains.
- 30 v2 Python/browser plan comparisons matched across institutions, service answers and en/fr.
- Retrieval: 20 English and 20 paired French development queries each achieved Recall@5 = 1.0 with a known topic filter over 19 short summaries. This is a small author-written regression set, not a held-out result, semantic-search benchmark or generalization claim.
- All 19 records had required metadata and were within the configured 30-day inspection window when checked. No full v2 publisher snapshots were ingested or cleared for redistribution.
- Desktop browser checks exercised combined goals, institution selection, a correction, preserved banking completion and a French switch. Additional QA details are recorded in `reports/verification_latest.json`.

## Incomplete / blocked

The P0 plan is **not fully complete**. `reports/v2_live_provider_01.json` records a blocked provider test: no key/model configuration was available, and no live provider call was made. The public static host cannot run the Python API; a Python backend host and secure runtime configuration are needed before online AI can be enabled publicly. The public release remains usable offline.

Retrieval is a Unicode lexical baseline over curated summaries. The proposed E5 model, semantic index, longer section-level ingestion, independently reviewed expected-evidence cases and blinded held-out evaluation are not implemented or validated. The capture tool prepares a new review, not automatic approval.

English/French are implemented and automatically checked, but neither has human language certification. Simplified Chinese, voice, cross-device accounts, document processing, live-provider failure testing, human usability studies and broader institution/provider coverage remain deferred. No reduction in effort, improved benefit uptake or population accuracy is claimed.

All eight original rules remain drafts. `audit_release.py --require-screening` intentionally fails. Independent policy and source-reuse review are still required for formal screening and full-snapshot redistribution. The public app offers preparation, education and official handoffs only.
