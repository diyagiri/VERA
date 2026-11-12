# Hosted OpenAI preparation release — verification pending

Prepared 12 November 2026 (America/Vancouver). This release adapts the supplied plan to ChatGPT Sites' JavaScript Worker runtime while preserving the Python/offline project and attribution.

Implemented: free-text online entry, combined fact proposals, one-at-a-time questions, confirmation, real OpenAI Responses API adapter (`gpt-6.1-sol`, medium), bounded function-call retrieval, separate support checking, editable plans, correction-aware merge, English/French, explicit offline fallback, secure server-only secrets, encrypted expiring sessions, usage ceilings and owner setup controls.

Evidence: 35 successful document captures, 33 preparation chunks, 21 canonical sources, five topics, English/French. Two PDFs are excluded pending visual extraction review. Source-byte versions now invalidate dependent plans. Captures and paraphrases remain distinct from policy approval. Semantic retrieval uses hosted OpenAI embeddings instead of a local E5 model; it is not yet live-evaluated.

Baseline before edits: 123 Python tests and 29 JavaScript tests passed. Current measured verification is in `reports/verification_latest.json`; fixture provider tests do not establish real provider/model access.

**Live completion remains blocked:** the owner must privately save `OPENAI_API_KEY` in Sites settings, then the saved version must be redeployed and the setup check must succeed. No successful live-provider request, semantic benchmark, participant test, human French review or independent policy approval is claimed. Online capability remains false until a real structured extraction, bounded tool call and grounded response test passes for the configured key/model/corpus.

The release does not implement Chinese, speech, document uploads, applications, payment calculations or formal eligibility decisions. All eight inherited rules remain drafts. A source handoff is used when available evidence is insufficient.

See README for secure point-and-click owner setup. No key belongs in chat, frontend fields, exports, logs, repository files or build artifacts.
