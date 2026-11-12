# Evaluation (hybrid release, 2026-11-12)

All cases are fictional and written by the team, so these results show the software behaves as designed. They do not prove policy accuracy or that real newcomers benefit. Results are reported as n/N because the samples are small. Machine-readable version: `reports/hybrid_evaluation.json`.

## Results

| What was checked | Result | How to reproduce |
|---|---|---|
| Screening cases, development split | 20/20 | `python tests/fixture_runner.py dev` |
| Screening cases, held-out split | 7/10 | `python tests/fixture_runner.py heldout` |
| End-to-end journeys (dev / held-out) | 7/7 · 3/3 | `python evaluate.py freeze …` then `score …` |
| Positive eligibility claims in gated mode | 0 in 90 screens | same |
| Evidence retrieval, expected source in top 5 (EN / FR) | 20/20 · 20/20 | `python scripts/evaluate_v2.py --output …` |
| Browser and Python planners give the same plan | 30/30 | same |
| Screening journey tests (Mei, Tomás, corrections, gating) | 11/11 | `node --test tests/screening.test.mjs` |
| Browser walk-through: desktop, 390 px phone, French, banking-only, legacy page | all pass, 0 console errors | manual + Playwright |

## The three held-out misses

C21, C22 and C27 are permit holders asked about federal settlement services (NEW-03). The rule was later changed to ask whether a special IRCC pathway applies, so it now returns "Needs information" where the original held-out expectation was "Blocker found". The held-out expectations were deliberately not edited to match the new rule; an independent reviewer decides which is right (`docs/fixture_review.md`).

## Accessibility (program screening section)

Checked 2026-11-12 in Chromium at 1280 px and 390 px. No automated audit tool was available; checks were scripted by hand.

| Check | Result |
|---|---|
| Whole screening journey with the keyboard only | Pass: answers are one Tab stop (arrow keys choose), then Save, then Skip; focus returns to the section heading after each answer |
| Every input has a visible label; question uses fieldset and legend | Pass |
| Result tables have a caption and column/row headers | Pass |
| "What changed" panel announced to screen readers (`role="status"`) | Pass |
| Status shown in words, never colour alone | Pass |
| Text contrast of new elements (WCAG AA 4.5:1) | Pass, lowest 4.72:1 |
| No sideways scrolling at 390 px | Pass |

Not checked: full-site audit with a screen reader, zoom to 400 %, and Fan's pre-existing pages.

## Not measured

- Live Anthropic model quality across many cases. One fictional journey ran end to end with Claude on 2026-11-12 (`docs/demo/VERA_demo_ai.mp4`) after the local server was given its writing rules up front, corrective retries and a 60-second timeout.
- Comparison with manual navigation and a basic retrieval chatbot.
- Independent policy review of the eight rules; all remain drafts.
- Usability with real newcomers, and human review of the French text.
