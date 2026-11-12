# VERA — your next step in BC

VERA helps newcomers in British Columbia turn official information into a justified next step. It screens three support programs with written rules, explains every result with its official source, updates when an answer is corrected, and builds a practical plan with an editable, unsent enquiry. English and French.

**[Demo with Claude (1 min 43 s)](docs/demo/VERA_demo_ai.mp4)** · [Offline demo (90 s)](docs/demo/VERA_demo.mp4) · [Evaluation](docs/EVALUATION.md) · [Architecture](docs/ARCHITECTURE.md) · [Evidence and sources](docs/EVIDENCE.md)

> Prototype for a hackathon. Not legal, immigration or financial advice. Official programs make every decision.

## What it does

1. **You describe your goal** in your own words, for example *"I just arrived for my master's at SFU. I want help settling in and to know if I can get student funding."*
2. **Program screening.** For *Settling in* and *School & funding*, VERA checks published criteria for three programs, asking one question at a time:

   | Program | Official source |
   |---|---|
   | StudentAid BC (STU-01) | studentaidbc.ca basic eligibility requirements |
   | BC Newcomer Services Program (NEW-02) | WelcomeBC BC NSP page |
   | Federal settlement services (NEW-03) | IRCC newcomer services and eligibility pages |

   Each program gets one of four honest results: *Blocker found*, *No blocker in the checked criteria*, *Needs information*, or *Needs official review*. VERA never says "eligible", "approved" or "guaranteed". Each result shows the rule behind it and a link to the official page.
3. **Corrections.** Change an answer and only the affected programs are re-checked; a "What changed" panel shows the difference.
4. **Preparation plan** across five topics (settling in, school and funding, banking, taxes, benefits): source-linked steps, progress tracking, notes, and a draft enquiry to a provider. Nothing is ever sent. Download as Markdown or JSON and resume later.

## How it works: rules decide, AI assists

| Layer | What it does | Where |
|---|---|---|
| Evidence | Official pages captured with SHA-256 fingerprints; every rule cites an exact page version | `data/manifest.json`, `sources.py`, `data/evidence/` |
| Rules | Eight written rules, compiled into the browser; four honest result states; approval gate | `rules.py` → `dist/catalog.json`, `web/engine.js`, `web/screening.js` |
| Plan | Stable steps with fact and source dependencies, so corrections update only what depends on them | `web/navigator.js`, `actions.py` |
| AI (optional) | Anthropic Claude understands free text, proposes topics and facts, runs one bounded evidence search, and writes cited guidance | `worker/provider.js` |
| Interface | One question at a time, result cards, evidence, corrections, download | `web/app.js` |

The AI can only **propose** facts. The person confirms them, and the rules engine decides. The model is told never to state or predict screening results. Citations are checked against the evidence actually retrieved, and a second model pass must find every block supported. Each turn has a call cap, a time limit and session and daily budgets.

**Rule status.** All eight rules are drafts awaiting independent review, so the live site shows *Needs official review* for every program. A clearly labelled switch, *Show draft rule logic (demo only)*, shows what the unreviewed rules would say. Approving a rule needs a named reviewer who is not its author (`data/rules/rules.json`).

## Results

Full details in [docs/EVALUATION.md](docs/EVALUATION.md). All cases are fictional and team-written.

| Check | Result |
|---|---|
| Screening cases, development | 20/20 |
| Screening cases, held-out | 7/10 (3 disputed cases awaiting an independent reviewer) |
| End-to-end journeys | 10/10 |
| Positive eligibility claims in 90 gated screens | 0 |
| Evidence retrieval, expected source in top 5 (EN / FR) | 20/20 · 20/20 |
| Keyboard-only screening journey and contrast (WCAG AA) | Pass |

Online mode was run end to end with Claude on 2026-11-12 (one fictional journey, shown in the demo). Not measured: live model quality across many cases, comparison with a basic chatbot, independent policy review, real-user testing.

## Run it yourself

### 1. Offline, no key needed (any computer with Python)

```
git clone https://github.com/diyagiri/VERA.git
cd VERA
python -m http.server 8000 --directory dist
```

Open http://localhost:8000. Press Ctrl+C to stop.

### 2. Online with Claude, on your own computer (Python 3.12)

```
python -m pip install -r requirements-api.txt
copy .env.example .env        # Mac/Linux: cp .env.example .env
```

Open `.env` in a text editor and fill in `ANTHROPIC_API_KEY=` with your key from console.anthropic.com. Keep `VERA_MODEL=claude-sonnet-5-5`, or use another model your account can access. Then:

```
python -m uvicorn server:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000, enter a goal, click **Start a conversation**, then **Agree and start AI conversation**. `.env` is git-ignored; never commit it or paste the key anywhere else.

### 3. Optional: host it online

`worker/` is a Cloudflare-style Worker version of the same app (it was first deployed on ChatGPT Sites). After pulling new code:

```
npm ci
npm run build
```

Then redeploy. To turn on online AI, add a hosted **secret** named `ANTHROPIC_API_KEY` in the site settings, redeploy, open `/setup` signed in as the owner, and run the setup check. It makes one real fictional request; online mode turns on only if it passes.

| Setting | Default |
|---|---|
| `ANTHROPIC_API_KEY` | Required secret for online AI |
| `VERA_MODEL` | `claude-sonnet-5-5` |
| `VERA_MAX_OUTPUT_TOKENS` | 8192 |
| `VERA_DAILY_REQUEST_LIMIT` · `VERA_DAILY_TOKEN_LIMIT` | 100 · 1,000,000 |
| `VERA_SESSION_REQUEST_LIMIT` · `VERA_SESSION_TOKEN_LIMIT` | 30 · 300,000 |

| Setup check says | Do this |
|---|---|
| `missing_api_key` | Add the `ANTHROPIC_API_KEY` secret and redeploy |
| `invalid_api_key` | Replace the key, redeploy, run the check again |
| `model_access` | Set `VERA_MODEL` to a model your account can use |
| `quota_exhausted` | Add credit to the Anthropic account |
| `provider_rate_limit` · `budget_exhausted` | Try later or raise the limits |

## Tests

```
python -m pip install -r requirements-dev.txt
npm ci && npm run build
python -m pytest -q
npm test
python tests/fixture_runner.py dev
python tests/fixture_runner.py heldout
```

## Privacy and limits

- VERA asks for categories, never names, ID numbers, documents or account numbers, and rejects messages that look like ID numbers.
- Offline answers stay in the browser tab unless you download them.
- Online mode needs consent and sends your message, confirmed details and relevant public evidence to Anthropic. On the hosted site, sessions are encrypted and expire after one hour of inactivity; the local Python server keeps them in memory only.
- VERA does not file taxes, calculate payments, open accounts, send enquiries or submit applications.
- French text is machine-drafted and has not had human review.

## Repository map

| Path | Contents |
|---|---|
| `web/` | Browser app: `app.js`, `screening.js`, `engine.js`, `navigator.js`, locales |
| `dist/` | Built site served offline and by the Worker |
| `worker/` | Hosted API: Anthropic pipeline, sessions, retrieval, contracts |
| `rules.py`, `models.py`, `sources.py`, `extract.py`, `actions.py` | Python rules engine, data contracts, evidence capture and plan |
| `server.py`, `conversation.py`, `settings.py` | Local Python API with Anthropic |
| `data/` | Source manifest, rules, evidence catalog, navigation catalog, test fixtures |
| `tests/`, `evaluate.py`, `scripts/` | Tests, evaluation and build scripts |
| `reports/` | Evaluation outputs (`hybrid_evaluation.json` is the latest) |
| `docs/` | Evaluation, architecture, evidence, demo, review checklists |
| `baseline/` | Inherited prototype, unchanged (tag `baseline-v0`) |

## Attribution

Built on Kopal Chaudhary's thesis and prototype (kept unchanged in `baseline/`). New work by Diya Giri and Fan, listed in [docs/new_work.md](docs/new_work.md). Government program names and links identify official sources, not endorsement. See [NOTICE.md](NOTICE.md) for rights.
