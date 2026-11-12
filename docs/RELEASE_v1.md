# Release record — 11 November 2026 (America/Vancouver)

## Delivered

- Complete goal → questions → evidence-linked guidance → correction → editable checklist and unsent enquiry → Markdown/text/JSON download workflow.
- Three-pathway coverage with named exclusions from scope; no benefits dashboard or account system.
- Primary browser app and Streamlit adapter; no mandatory model service.
- Python-backed browser rule tables, approval/freshness gates, real event traces and bounded orchestration.
- Official source capture and byte hashes. S2 and S3 matched upstream bytes exactly; S1, S4 and S5 differed at byte level. All existing supporting spans were still present. Updated version pointers remain drafts; no independent approval was manufactured.
- Verified baseline directory unchanged against upstream `f7ea6b9`; upstream history and baseline tag retained.
- Frozen evaluation outputs and failure history, automated tests and a one-command local launcher.

## Measured verification

Final build: 93 Python tests pass without skips on the build machine; 12 Node tests pass, including 252 individual evaluator parity checks. Development screening cases pass 20/20; the author-written held-out-labelled partition passes 10/10. Scripted journeys pass 7/7 and 3/3. Release gating produced zero positive results over 90 program screens, which is not a policy-accuracy or population-risk guarantee.

The first journey evaluation failed J04, J08 and J09 because the routing dictionary omitted “settlement” from BC NSP. That routing defect was corrected and the same frozen-input scenarios rerun. Held-out-labelled journeys were exposed during debugging; the final numbers are regression results, not a held-out generalization estimate. Earlier frozen outputs and scores remain in `reports/`.

Local deterministic journey latency is recorded in `reports/evaluation_release.json`. It excludes user reading time, browser time and provider latency. No manual-navigation comparison, retrieval-chatbot study, consenting-participant study, live model call or real-world impact claim was made.

Browser checks covered goal submission, contextual questions, keyboard activation of answer controls, fictional correction and changed result, stale enquiry removal, normal-mode review states, editable enquiry, checked tasks and download completion. The desktop layout was visually inspected. Mobile media queries are implemented; device-specific browser and screen-reader audits remain unperformed. No application-origin console errors were observed; the browser's extension emitted unrelated metadata errors.

## External release gates

1. Independent policy reviewer sign-off for each exact rule and source version. Eight of eight are still drafts.
2. Source reuse review before redistributing snapshots. Full snapshots are local and excluded from the source ZIP and Git.
3. Confirmation of the hackathon rubric, preparation policy, attribution and submission format.
4. Optional model credentials, selected model and live-provider smoke test if the team enables that mode.
5. Independent held-out fixtures and blinded human evidence-support review before claiming policy correctness. Fresh usability research before claiming reduced effort or impact.

These gates do not block the delivered guidance workflow. They prevent it being represented as approved live eligibility screening.
