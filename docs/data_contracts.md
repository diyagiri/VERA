# Data-contract additions

The upstream dataclasses remain the shared contract. This implementation adds:

- `SourceRecord.captured_at`: UTC capture timestamp; distinct from source check date and page-modified date.
- `Facts.federal_exception`: `yes | no | unknown`, a category-level assertion for applicable federal exception pathways. No document or identifier is collected.
- `Navigator` session: facts, as-of date, per-program results, capped actual operation events, skipped fields, correction summaries and generated guidance.
- Guidance object: `as_of_date`, `fact_version`, editable `tasks` (stable session ID, program, text, URL, source, completion), editable `enquiry`, `limits`.
- Browser catalog: source provenance/paraphrases, rule decision tables, original approval metadata and fail-closed review reasons. Full snapshots and verbatim evidence catalog are not part of the browser payload.

Future schema changes must preserve separation between user facts, draft logic, approved screening and unverified provider availability. Date-sensitive calculations remain `review_required` until reviewed. Official page modification is not assumed to be the policy effective date.
