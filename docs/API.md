> Local Python API (Anthropic). The hosted site runs the Worker in `worker/`, which also uses Anthropic since 2026-11-12. To run this server, see "Online with Claude, on your own computer" in the root README.

# VERA v2 API and operating modes

The public `vera-newcomer-guide.fondfoam.chatgpt.site` deployment is static and stays in explicitly labelled offline guidance mode. Python hosting and a provider credential are required for the new optional conversation. No production environment key was available during implementation; `reports/v2_live_provider_01.json` records the blocked smoke test.

## Configuration

Install `requirements-api.txt`, build with `python scripts/build_web.py`, export a model ID available in your Anthropic account and `ANTHROPIC_API_KEY`, then run `uvicorn server:app` with **one worker**. Bind to loopback locally. Hosted deployments require HTTPS and `VERA_ORIGIN` equal to the complete public origin (without a trailing slash). HTTPS origins cause Secure cookies. Origin enforcement intentionally rejects localhost aliases unless configured to match. Configure a reverse proxy deliberately; no wildcard CORS is enabled.

The current server owns ephemeral memory, so scaling to several workers or containers requires a shared session and budget design. Restarting clears sessions and resets process-wide budgets. This is a bounded prototype, not a production multi-tenant AI service. Set provider-side account spending limits as well; monetary estimates are not available without configured pricing.

| Setting | Default |
|---|---|
| `VERA_MODEL` | Unset: AI unavailable |
| `ANTHROPIC_API_KEY` | Unset: AI unavailable |
| `VERA_ORIGIN` | `http://127.0.0.1:8000` |
| `VERA_SESSION_REQUEST_LIMIT` | 30 provider requests |
| `VERA_GLOBAL_REQUEST_LIMIT` | 200 provider requests per process lifetime |
| `VERA_SESSION_TOKEN_LIMIT` | 100,000 conservatively reserved tokens |
| `VERA_GLOBAL_TOKEN_LIMIT` | 200,000 conservatively reserved tokens |

Each turn permits two planning requests and one support-review request, eight tool calls, 1,600 maximum output tokens per request, and a 45-second wall-clock budget. A repeated tool signature stops the turn. Conservative reservations use bounded serialized input byte counts plus output allowance; they are not billed-token measurements. Actual provider-reported usage is returned separately when a turn succeeds.

## Endpoints

All `/api/v1` mutations require `Origin: <VERA_ORIGIN>`, `X-VERA-Client: browser-v2` and JSON content. Requests are bounded to 100 KB. At most 60 mutations per minute are accepted in a short-lived, keyed client-IP bucket; raw IP addresses are not retained by application state. Up to 100 active sessions are supported. Session cookies are HttpOnly, SameSite=Strict and scoped to `/api/v1`; the server deletes an old cookie session when starting a new one.

| Method and path | Behavior |
|---|---|
| `GET /health` | Liveness and safe online capability flag |
| `GET /runtime.json` | Lets the browser discover a same-origin API |
| `GET /api/v1/capabilities` | Locales, topic/campus coverage, model availability and no-screening flag |
| `POST /api/v1/sessions` | Create session with explicit `consent` and `locale` |
| `POST /api/v1/sessions/current/messages` | Bounded message, locale, expected versions and idempotency key |
| `PATCH /api/v1/sessions/current/profile` | Confirm/correct profile; regenerate affected work |
| `PATCH /api/v1/sessions/current/tasks/{id}` | Edit text, completion or accept a reviewed revision |
| `PATCH /api/v1/sessions/current/plan` | Save notes or an unsent enquiry |
| `GET /api/v1/sessions/current/plan` | Current plan, revalidated across BC calendar-day changes |
| `POST /api/v1/sessions/current/import` | Strict import; revalidation; AI consent disabled |
| `GET /api/v1/sources/{id}` | Curated metadata and allowed short summaries; accepts legacy aliases |
| `DELETE /api/v1/sessions/current` | Clear server session and cookie |

Mutations carry `profile_version` and `plan_version`. A mismatch returns 409. Facts get new versions only when their value/state changes. A locale switch changes rendered language without changing the fact version. Retries with the same message idempotency key and body reuse the result; reuse with a different body is rejected. Import data cannot set AI consent, add unknown program/source IDs, change official destinations, restore system instructions or create arbitrary deadlines.

## Privacy and validation

Only the requested message, selected relevant profile fields and two recent messages are included in conversation context. Proposed facts stay unconfirmed. Unknown/declined fields remain explicit. Catalog text is untrusted data. Tools accept known topic/program IDs and bounded query text; they do not execute code or arbitrary URLs. Citations must have been retrieved in the turn, source versions must be current, and school-specific material is filtered by confirmed campus scope.

No model can approve policy rules, confirm a user fact, send an enquiry, open an account, make a payment, file a return, or submit an application. Numeric amounts, dates and URLs are excluded from generated explanation prose. Structural validation and a second model support check are diagnostics; semantic support and adversarial robustness remain unverified against a real provider.

The app does not write transcripts or profile data to disk. Disable HTTP access logging where appropriate and configure host logs intentionally. Provider retention depends on your service/account. Clearing a VERA session cannot delete provider-retained data or exported files. Never promise zero provider retention without checking the actual account configuration.
