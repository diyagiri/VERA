# VERA — your next step in BC

VERA helps newcomers in British Columbia prepare for settlement, education funding, banking, tax and benefit questions. English and French share the same confirmed facts and plan progress. SFU and UBC Vancouver have limited institution-specific coverage; other institutions receive an honest official-office handoff.

**[Open VERA](https://vera-newcomer-guide.fondfoam.chatgpt.site)** · [Presentation](https://chatgpt.com/space/page_d14459ce272081919fc31ab5d7062b42) · [Release status](docs/RELEASE.md) · [Evidence](docs/EVIDENCE.md)

## For the site owner: no terminal or configuration files

The hosted backend and its runtime settings are prepared in ChatGPT Sites. The only credential you need to enter is your own OpenAI API key. Online AI remains unavailable until a real setup check succeeds. A saved key by itself does not count as a successful integration.

1. Open **[ChatGPT Sites](https://chatgpt.com/sites)** while signed in to the account that owns VERA.
2. Find **VERA · Your next step in BC**.
3. Open its **More actions** menu and select **Settings**.
4. In the hosted environment variables/secrets controls, add an entry named exactly **`OPENAI_API_KEY`**.
5. Mark the entry as a **secret** and paste the key only into its private value field. Save the entry. Follow the controls shown in your Settings screen; do not put the key in the chat, website, README or GitHub.
6. Return to the ChatGPT conversation and say **“The key is saved; redeploy VERA and run the setup check.”** Do not include the key. ChatGPT can apply the environment revision and test the backend.

Sites' documented navigation is **More actions → Settings**; labels inside the environment editor can vary. [Official instructions](https://learn.chatgpt.com/docs/sites/managing-a-site). Saving or changing a hosted secret requires redeploying a saved version to apply it.

The owner-only [setup page](https://vera-newcomer-guide.fondfoam.chatgpt.site/setup) can also run the check after deployment. Sign in with the owning ChatGPT account, then select **Run setup check**. It never asks for or displays a key. It creates the evidence vectors and runs a fictional multi-topic request with the configured model. The test checks extraction, a provider function call, citations and a support-review pass; it is not proof of general financial accuracy. It uses the owner's OpenAI API quota and may incur API charges. Public visitors can use the site without ChatGPT sign-in; only owner setup requires sign-in.

The key and the session-encryption/setup credentials are held in Sites' built-in secret storage. The model, limits and other non-secret settings are already configured. You do not need to create an `.env` file or edit the hosting manifest.

## How to use VERA

Start by writing your situation in your own words. Optional example buttons only fill the text box; they do not restrict the kinds of requests accepted.

When online AI is available, the site explains what is sent to OpenAI and asks for consent. It extracts several relevant needs and tentative facts together. Review the compact summary, correct it if needed, and select **Confirm and build my plan**. Follow-up questions are limited to one at a time. Facts are not treated as confirmed just because a model proposed them.

Your plan groups preparation, next actions and questions for an official provider. Open the source links, mark tasks complete, edit an unsent enquiry, and keep your own notes. Corrections revise dependent tasks and flag affected user edits while preserving unrelated progress. Language changes preserve task IDs and completion. Download readable Markdown or JSON for resuming. Import validates the file, rechecks source versions and dates, and never imports AI consent or executable instructions. Use **Start over** to clear the active session; downloaded files remain yours.

Offline guidance is an explicit alternative. It uses local matching and reviewed preparation templates rather than an LLM. It should not be described as the completed online release. Missing or failing AI configuration never creates simulated model output.

### Fictional prompts to try

| Prompt or action | What to look for |
| --- | --- |
| “I'm an international student at SFU in Burnaby. My family can't send money this month. I need help with tuition and finding settlement support.” | Several needs and facts proposed together; no repeated school question or inferred permit category. Confirm the summary and inspect the official destinations. |
| “I moved to Vancouver for work two months ago. I need to open a bank account and understand what to prepare for taxes.” | Banking and tax preparation without a student questionnaire or a personal tax-residency decision. Mark one banking step complete. |
| “We recently moved to BC with two children. What support should we investigate, and where do we start?” | Bounded family-support information and official next steps without promised payments. |
| “Je viens d'arriver à Vancouver pour travailler. Comment ouvrir un compte bancaire et préparer mes démarches fiscales ?” | French guidance using the same source and confirmation requirements. Human French review is still unavailable. |
| “Correction: I study at UBC, not SFU. Keep my completed banking checklist.” | A proposed school correction and campus clarification where necessary; unrelated banking progress preserved. |
| “My college isn't listed. Can you still help me find settlement and funding information?” | BC/federal guidance plus a truthful school-office handoff, without fabricated awards. |
| Export JSON, clear the session, import it and switch to French. | Validated restoration, rechecked evidence and unchanged task IDs; new consent required before another provider call. |

## What is implemented, and what is not yet verified

The hosted implementation includes a same-origin Cloudflare Worker API, the official OpenAI JavaScript SDK, the Responses API, strict structured outputs, a bounded function-call exchange, claim-support checks, encrypted short-lived sessions, version checks, idempotency, request/token ceilings and an owner-only setup check. The browser never makes a privileged provider request.

The selected conversation model is **`gpt-6.1-sol`**, with **medium** reasoning, `store:false` and an 8,192-token output cap. The model is configurable only on the server; no model is silently substituted. The earlier standalone `gpt-4.1-mini` success does not verify this model. The live release remains **blocked pending the private key and successful setup test**; fixture tests are not live-provider evidence.

This is a hosting adaptation of the supplied Python plan. Sites runs JavaScript Workers, so the production backend uses the official JavaScript SDK instead of FastAPI/AsyncOpenAI. The existing Python core, offline launcher and optional legacy Anthropic development adapter are retained with attribution. They are not the production online path. To avoid loading a local E5 model into a 128 MB Worker, hosted semantic search uses configurable **`text-embedding-3-small`**, 256 dimensions, fused with Unicode lexical ranking. This embedding model is a disclosed adaptation, not a substitution of the selected conversation model. Embeddings are generated on the server only after the key is saved; no semantic-quality result is claimed before evaluation.

## Privacy and limits

Offline answers remain in the current tab unless explicitly exported. Online mode sends only the selected profile context, current request, recent dialogue and relevant public evidence to OpenAI after consent. Do not enter names, SINs, account numbers, credentials or identity documents. The client never stores a secret or silently saves a profile in local storage.

Production sessions are encrypted with AES-GCM before being stored in the platform's D1 database. The cookie contains an unpredictable opaque session ID and is Secure, HttpOnly and SameSite=Strict. Sessions become inaccessible after one hour of inactivity and expired rows are purged on subsequent requests; **Start over** deletes the active row immediately. Hosting backups and provider retention can still apply. This replaces process-local memory because Workers may run in multiple isolates. There is no account-based cross-device history.

All eight inherited eligibility rules remain drafts. VERA prepares questions and next steps; official providers decide eligibility and funding. It does not file taxes, calculate payments, open bank accounts, send enquiries or submit applications. French is implemented and automatically checked, not human reviewed. Chinese remains deferred. No participant impact study or independent policy approval is claimed.

## Runtime settings

All production values are managed in **Sites → VERA → More actions → Settings**. Only listed values change during updates; other secrets are preserved. Never store values in `.openai/hosting.json`. That manifest contains only project identity and storage bindings.

| Key | Default / purpose |
| --- | --- |
| `OPENAI_API_KEY` | Required private secret for online AI. Entered by the owner. |
| `VERA_MODEL` | `gpt-6.1-sol`; no automatic fallback. |
| `VERA_REASONING_EFFORT` | `medium`. |
| `VERA_EMBEDDING_MODEL` | `text-embedding-3-small`; vectors use 256 dimensions. |
| `VERA_MAX_OUTPUT_TOKENS` | `8192`; reasoning shares this output budget. |
| `VERA_DAILY_REQUEST_LIMIT` | `100` provider requests per Vancouver calendar day, including setup and embedding requests. |
| `VERA_DAILY_TOKEN_LIMIT` | `1000000` conservative reserved token units per day. Reservations are not a dollar-spend estimate. |
| `VERA_SESSION_REQUEST_LIMIT` | `30` requests per online session. |
| `VERA_SESSION_TOKEN_LIMIT` | `300000` conservative reserved token units per session. |
| `VERA_SESSION_SECRET` | Automatically configured secret for session encryption; rotating it invalidates old sessions. |
| `VERA_SETUP_TOKEN` | Automatically configured secret for owner-authorized deployment checks. Never put it in a URL or browser bundle. |
| `VERA_OWNER_EMAIL` | Private owner authorization value for setup; no public display. |

Each turn permits at most six provider requests, one bounded retrieval function execution in the current pipeline, 60 seconds per provider request and 180 seconds total. Normal turns use four Responses requests plus one query-embedding request. SDK retries are disabled. An explicit retry after a network error uses the same idempotency key. API errors preserve the last valid plan. Bounds can be adjusted by the owner; there is no implied dollar allowance or unlimited usage.

## Troubleshooting

| What you see | What to do |
| --- | --- |
| Missing key / offline guidance | Save `OPENAI_API_KEY` as a Sites secret, then ask ChatGPT to redeploy and run setup. |
| `invalid_api_key` / HTTP 401 from OpenAI | Replace a revoked/incorrect key privately in Sites settings, redeploy and rerun setup. Never share the key. |
| `model_access` / OpenAI 403 or 404 | Check the configured model and project access. VERA will not change models silently. |
| `quota_exhausted` | Check the API project's billing/quota. A ChatGPT subscription is not proof of available API quota. |
| `provider_rate_limit` or `budget_exhausted` | Retry later or ask the owner to inspect the documented limits. Previous work remains available. |
| Timeout, refusal, incomplete or unsupported answer | Keep the prior plan; retry a clearer request or switch to offline guidance. Diagnostics contain safe codes only. |
| `index_not_ready` | Run the owner setup check after deployment; it builds the versioned vectors. |
| Frontend opens but AI is unavailable | Check owner setup status. The browser being visible does not prove provider access. |
| Session expired | Resume an explicitly downloaded JSON plan and grant fresh AI consent if wanted. |
| `stale_version` | Reload the current session before editing; another request changed the version. |
| Owner setup is denied | Sign in with the owning ChatGPT account. Public visitors cannot run setup. |

## For contributors: reproducible local checks

End users do not need these steps. Development was checked on Linux with Python 3.12 and Node 24; no Windows production-hosting support is claimed. Python dependencies are pinned in `requirements-dev.txt`/`requirements-api.txt`, and JavaScript dependencies are pinned in `package.json` and `package-lock.json`.

```bash
npm ci
python -m pip install -r requirements-dev.txt
python scripts/build_index.py --capture-report data/evidence/capture-2026-11-12-v2.json
npm run build
python scripts/verify.py
python scripts/evaluate_v2.py --output reports/local_legacy_retrieval.json
python scripts/audit_release.py
```

`npm run build` compiles the existing offline core, bundles the Worker and embeds only an explicit allowlist of frontend assets. It never reads `.env` files or uses API credentials as build inputs. `npm run dev -- --host 127.0.0.1 --port 4173` runs an offline-only local preview with an in-memory SQLite test adapter; it never reads production secrets. The original `python run.py` offline launcher remains available on port 8000. The legacy Python API setup is in [docs/API.md](docs/API.md); it is separate from the hosted OpenAI backend and does not load the hosted settings.

The repository includes a reproducible public corpus: **35 captured documents, 33 indexed preparation chunks, 21 source IDs and five topics**. Twenty-three chunks include brief official excerpts; others use original preparation paraphrases with official links. Two captured PDFs are excluded from runtime text pending visual extraction review. See [docs/EVIDENCE.md](docs/EVIDENCE.md) for acquisition, allowlist, source terms, source-change handling and exact reproduction commands. A capture is not a human policy review. The existing 40-case retrieval report concerns the older summary catalog and must not be cited as measured semantic retrieval performance for this corpus.

The owner setup flow performs the live check; it cannot pass without real credentials and actual Responses/function/embedding calls. Its report records the returned model, timing, usage, corpus version and scope without a key or transcript. Tests in `tests/worker.test.mjs` use fixtures for predictable failure cases and are explicitly not live evaluations.

## Architecture and attribution

Browser → same-origin Worker → strict context extraction → bounded evidence tool → lexical/semantic retrieval → structured explanation → citation and support checks → user confirmation → stable preparation plan. D1 holds encrypted expiring sessions, public evidence vectors and safe setup/usage metadata. The user controls export/import; no enquiry is sent.

Main files: `worker/index.js` (API and owner controls), `worker/provider.js` (official SDK and bounded pipeline), `worker/contracts.js`, `worker/storage.js`, `worker/retrieval.js`, `worker/corpus.js`, `web/app.js`, `web/navigator.js`, `scripts/build_worker.mjs`, and `db/schema.ts`. Database migrations are generated and applied by Sites publication. The platform serves the Worker at `dist/server/index.js`; it does not execute the Python server.

Built on [diyagiri/VERA](https://github.com/diyagiri/VERA), preserving `baseline/`, [NOTICE.md](NOTICE.md), existing source provenance and draft-rule gates. Current repository: [Fan-0215/VERA](https://github.com/Fan-0215/VERA). The supplied plan's reviewed commit was `185e545`; implementation preserved the subsequent `57cf5a1` work rather than replacing it.
