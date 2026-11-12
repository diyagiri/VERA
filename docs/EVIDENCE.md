# Versioned preparation evidence

VERA's v2 evidence corpus is a small, auditable preparation reference. It is not a complete program-policy database and cannot approve eligibility rules. The canonical program/navigation catalog remains `data/catalog/navigation.json`; the evidence registry extends its D01–D19 records with D20 (CCB conditions) and D21 (CRA residency guidance). Existing S1–S5 aliases are preserved.

## Reproduce the capture and index

The ingestion and index commands need only Python's standard library. A fresh capture requires internet access to the fixed official hosts. Run from the repository root:

```bash
python scripts/ingest_sources.py --output data/evidence/capture-YYYY-MM-DD.json
python scripts/build_index.py --capture-report data/evidence/capture-YYYY-MM-DD.json
python scripts/build_index.py --capture-report data/evidence/capture-YYYY-MM-DD.json --sqlite data/index/navigation.sqlite
```

Use a new capture-report filename each time; existing capture reports are immutable. `--ids D09 D11` and `--locales en fr` allow bounded refreshes. An HTTP failure is recorded and the ingestion command exits nonzero. The builder excludes failed, unparsed and PDF-only records rather than reporting them as usable evidence. To rebuild the complete corpus, supply a complete capture report, not a partial refresh.

For the shipped corpus use `--capture-report data/evidence/capture-2026-11-12-v2.json`. The original capture recorded 35 successful downloads. The v2 report reparsed the same verified bytes with improved nested-heading handling; it did not change retrieval times. To repeat extraction locally, use `python scripts/ingest_sources.py --reextract-report data/evidence/capture-2026-11-12.json --output data/evidence/capture-new-extraction.json`. Re-extraction requires the ignored local captures and verifies their hashes before parsing. A fresh public checkout can rebuild the portable index from the committed report without those raw captures.

The source registry contains exact URLs selected from official pages. Runtime users and models cannot add URLs. Fetches use HTTPS, a fixed host allowlist, bounded redirects, at most two attempts, a 20-second network timeout, a 15 MB response limit and a named user agent. Access denials and rate limits are reported without bypassing them. No application, login or user document is fetched.

## Saved files and contract

- `data/evidence/registry.json`: selected original URLs, official French alternatives, publisher, scope, original bilingual summaries, related sources and reuse policy.
- `data/evidence/capture-*.json`: immutable retrieval timestamps, actual resolved URLs, raw-byte SHA-256, extracted-text hash where available, detected publication metadata, heading locators and failures. Download time never becomes a human review or policy-effective date.
- `data/evidence/index.json`: portable JSON for the Worker or Python retriever, with document metadata and versioned chunks.
- `data/evidence/quality-report.json`: actual coverage counts and missing dates, parse failures or withheld text.
- `data/snapshots/v2/`: ignored local source bytes, excluded from public packages. The full website bodies and PDFs are never included in the index.

The index has `schema_version: 2`, `corpus_version`, `generated_at`, `aliases`, `documents`, `chunks`, `coverage` and `limitations`. Each chunk has a stable ID such as `D09.en.preparation`, canonical `source_id`, language-specific `document_id`, actual `source_version` SHA-256, locale, topic, jurisdiction, institution/campus, section, URL/locator, source attribution, reuse metadata, retrieval/check times and related chunk IDs. The corpus hash covers the indexed text and source versions, not a build timestamp.

`text` is an original VERA preparation paraphrase with an optional complete short source sentence. `verbatim_excerpt` distinguishes source text from VERA prose. Excerpts remain in their original official language; French VERA summaries are machine drafts with no human language review. `context_limit` explicitly warns that the chunk is not the entire policy or its full exceptions. Related source IDs preserve application/condition/residency context rather than treating every hit as a stand-alone rule. Runtime code should retrieve related chunks when relevant, validate citations against the actual returned versions, and hand off when the available context cannot support the answer.

The lexical token list is Unicode-aware and accent-normalized. No embeddings, semantic-search model, model revision or retrieval-quality threshold is claimed. Scores measure ranking only. The structured navigation catalog's `curated_summary_sha256` and the evidence corpus's actual source-byte SHA-256 are different version types; do not interchange them.

`localized_summary` and `search_terms` include both English and French preparation wording, allowing a French query to find an English-only institutional source. The official document's `locale` remains unchanged. A translated summary does not establish the existence of an official French institutional document.

The shipped report records 21 canonical sources, 35 downloaded language-specific documents, 33 indexed preparation chunks and 23 brief official excerpts. Two PDFs are captured but withheld from the index. The quality report lists unknown publisher dates and deliberate excerpt gaps. Command-line checks verified all 35 raw hashes, aliases, topic coverage, section locators, redirect/URL restrictions, nested heading extraction and the reuse/excerpt gates. These are regression checks, not evidence of independent policy accuracy or multilingual answer quality.

## Reuse and review boundaries

Canada.ca's [terms](https://www.canada.ca/en/transparency/terms.html), checked during this implementation, allow non-commercial reproduction with accuracy, title/author attribution and identification of the source version. The index includes only brief attributed excerpts, never logos, wordmarks or full federal pages. Commercial redistribution and third-party content require a separate rights review; this corpus is not a blanket licence.

BC and university records contain only original VERA paraphrases and links. The inherited [BC reuse review](reuse_terms.md) remains in force. [UBC's terms](https://www.ubc.ca/site/legal.html) limit reproduction, and no public redistribution permission has been obtained. [SFU's terms page](https://www.sfu.ca/contact/terms-conditions.html) did not establish a general redistribution grant in this review. Fetch success does not resolve licensing. No new permission request has been sent.

PDFs are hashed and recorded, but their text is withheld pending page-level visual extraction review. Do not describe a captured StudentAid BC manual or translated WelcomeBC guide as a fully indexed or reviewed PDF. The original StudentAid/BC NSP draft rules remain unchanged and unapproved.

The default freshness interval remains 30 days and is an engineering setting. A byte change flags a source version change; it does not establish a policy change or approve an interpretation. Unknown publisher dates and effective periods remain null. Rebuilding the index does not refresh the check date. A fresh capture does not automatically validate an older paraphrase: summaries and applicable conditions still require review. A stale or disputed record must lead to an official-source handoff.

Current scope remains five preparation topics, with limited SFU and UBC Vancouver institution coverage. The corpus does not infer tax residency, custody, awards, benefit amounts or application deadlines. No independent policy review, human language validation or participant research was performed by these scripts.
