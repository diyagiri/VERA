# Implementation architecture

`rules.py` is the policy logic source of truth. `scripts/build_web.py` enumerates each rule's finite input domain into a browser decision table. The browser does not maintain a separate handwritten set of eligibility rules. 252 exact comparisons cover every individual rule-input combination, including PR-date presence. The federal date calculator remains disabled, so it has no date arithmetic to compile.

The hosted UI is a static HTML/CSS/ES-module app. Goals route to the bounded catalog; questions are derived from relevant missing inputs; each actual search/check/question/plan operation enters a capped in-memory event list. No simulated LLM activity appears. Twelve tool calls per operation and 80 retained events bound execution.

The Python `Navigator` provides the same orchestration to Streamlit and evaluation. Optional Anthropic planning is local-only, explicit-consent, and tool-constrained. Arbitrary tools/arguments and repetitions stop the loop. Provider text never becomes eligibility advice. A timeout or invalid result falls back to the existing deterministic plan.

## Correction contract

An answer increments the fact version. Only dependent programs rerun. A status change also clears status-dependent facts; leaving the student category clears institutional assumptions; changing away from economic PR clears the date. Every correction regenerates the checklist and enquiry, removing stale claims and replacing any prior user edits. The UI explains this before saving. Unaffected results retain their own fact version.

## Review gate

Release screening requires a genuine different author/reviewer, review date, test IDs, coverage limits, compatible effective dates, a matching source hash, a present snapshot, supported excerpt, and a source check no older than 30 days. Thirty days is a conservative project maintenance policy, not a government rule. The browser also applies freshness and effective-date checks at runtime. Its build-time integrity proof is immutable metadata, not a live fetch.

All current rules are drafts. Fictional examples bypass the approval gate only to illustrate proposed logic and remain visibly labelled. Unknown federal exception applicability asks a question; a possible exception routes to review. A general permit exclusion requires an explicit answer that no exception applies and still cannot be used live while the rule is draft.

## Evidence and data

Current captures contain full publisher bytes locally. SHA-256 is calculated over the bytes; `captured_at`, `checked_on`, displayed page-modified dates and policy effective dates are separate. Null effective dates remain unknown. The source catalog includes 37 exact spans; the public interface shows paraphrases and links instead of republishing the full excerpts. Source capture invalidates a different-version rule's approval; changing a source does not update its rule interpretation automatically.

The interface neither stores nor sends session facts. It creates downloads in the browser on demand. It never sends an enquiry, applies to a portal, uploads a document, promises a provider appointment, or performs a benefit calculation. External official links have their own privacy practices.
