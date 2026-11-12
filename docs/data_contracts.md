# Data-contract additions

The upstream dataclasses remain the shared contract. This implementation adds:

- `SourceRecord.captured_at`: UTC capture timestamp; distinct from source check date and page-modified date.
- `Facts.federal_exception`: `yes | no | unknown`, a category-level assertion for applicable federal exception pathways. No document or identifier is collected.
- `Navigator` session: facts, as-of date, per-program results, capped actual operation events, skipped fields, correction summaries and generated guidance.
- Guidance object: `as_of_date`, `fact_version`, editable `tasks` (stable session ID, program, text, URL, source, completion), editable `enquiry`, `limits`.
- Browser catalog: source provenance/paraphrases, rule decision tables, original approval metadata and fail-closed review reasons. Full snapshots and verbatim evidence catalog are not part of the browser payload.

Future schema changes must preserve separation between user facts, draft logic, approved screening and unverified provider availability. Date-sensitive calculations remain `review_required` until reviewed. Official page modification is not assumed to be the policy effective date.

## V2 financial navigator contracts

`api_contracts.py` adds strict, versioned Pydantic schemas, separate from the retained legacy dataclasses. Unknown fields and unsupported fact values are rejected. Profiles distinguish proposed facts from confirmed facts and support multiple topics, priority, language and campus. Plans preserve stable task IDs, completion, user edits, notes and unsent enquiries; changes to relevant facts or sources mark dependent work for review. Unaffected work survives corrections.

`PortablePlan` is the validated JSON export/import format used by Python and `web/navigator.js`. Imports are previewed before replacement and never enable AI consent. Text from imports remains user data. The browser and API share `data/catalog/navigation.json`; task sources cite curated summary versions rather than claiming full publisher snapshots.

API mutations carry a session version and request ID. Sessions are bound to a cookie, expire after inactivity, and have bounded retry history. Online model turns may propose facts and bounded source-linked next steps; they cannot confirm facts or submit enquiries. See [API.md](API.md) for endpoints, consent, budgets and deployment constraints.
