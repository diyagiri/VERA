# Submission checklist

## Done in the repository

- [x] Hybrid journey: program screening for StudentAid BC, BC NSP and federal settlement services inside the five-topic plan
- [x] AI provider: Anthropic (hosted Worker and local Python server)
- [x] Evaluation with n/N results and stated limits: `docs/EVALUATION.md`, `reports/hybrid_evaluation.json`
- [x] Accessibility check of the screening section
- [x] Demo video: `docs/demo/VERA_demo.mp4` (90 s, offline mode, fictional persona)
- [x] README written for judges, with run instructions
- [x] Attribution: `NOTICE.md`, `docs/new_work.md`; inherited prototype unchanged in `baseline/` (tag `baseline-v0`)
- [x] No secrets in the repository; `.env` is git-ignored

## Still needs a person

- [ ] Push `main` to github.com/diyagiri/VERA and make the repository public
- [ ] Fan: pull `main`, `npm ci`, `npm run build`, redeploy the site
- [ ] Site owner: add the `ANTHROPIC_API_KEY` secret, redeploy, run the `/setup` check
- [ ] Run `npm test` once after `npm run build`; the bundled-Worker test needs the build
- [ ] Run `python -m pytest -q` once with `requirements-api.txt` installed; `tests/test_v2.py` needs FastAPI
- [ ] Optional: a teammate who did not write the rules reviews them (`data/rules/rules.json`) and the three disputed held-out cases (`docs/fixture_review.md`)
- [ ] Fill in the hackathon's required fields (team, links, video) from this README

## Known limits to state honestly

- All eight rules are unreviewed drafts; live screening shows "Needs official review".
- Live model quality has not been evaluated.
- Data files quote short passages from BC government pages; BC permission was not obtained (`docs/reuse_terms.md`).
- French text is machine-drafted.
