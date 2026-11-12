# VERA public project plan

This document describes the product scope and remaining work. For implemented behavior and measured checks, see [RELEASE.md](RELEASE.md). Requirements below are not claims of completed validation.

## Product scope

VERA helps newcomers across British Columbia turn official information into practical preparation steps. It supports settlement, education, banking, taxes and benefits. Institutional support is a conditional layer with explicitly limited coverage; it does not define the entire audience.

The interface should remain concise, readable and useful without an account. English and French are the core interface languages. Simplified Chinese is a later extension requiring its own dictionaries, evaluation and clearly stated review status.

## Required journeys

- A student combines settlement and education goals, confirms suggested details, selects an institution and receives source-linked tasks and an editable, unsent enquiry.
- A newcomer explores banking and taxes without having to complete an unrelated student questionnaire.
- A household explores official benefit pathways without duplicate application instructions, payment estimates or promised eligibility.
- A person changes language or corrects a fact while preserving unrelated completed tasks and personal notes.
- A person exports a plan and explicitly imports it later; the system validates the format and rechecks source freshness.
- Missing evidence, unsupported institutions and model failures result in an honest explanation and useful official handoff.

## Implementation requirements

- Keep proposed facts separate from confirmed facts. Ask relevant questions and allow unknown answers.
- Use stable task identifiers and fact/source dependencies so corrections affect only related work.
- Provide JSON export/import and Markdown export. Preview imported information before replacing a plan. Imported data never authorizes AI use.
- Keep offline guidance available and clearly labelled. Do not simulate a live model connection or tool activity.
- For optional online mode, use a same-origin Python API, server-side credentials, explicit consent, isolated expiring sessions, strict schemas and bounded model/tool usage.
- Keep source URLs, applicability, language and inspection metadata visible. Treat curated summaries as summaries, not complete publisher snapshots.
- Preserve inherited code, attribution and all original policy approval gates. Draft rules cannot become eligibility decisions through model output.
- Do not open accounts, file taxes, submit applications, calculate benefits or send enquiries on the user's behalf.

## Release evidence and remaining work

The release record must distinguish implementation, automated regression checks, manual interface checks, actual provider calls and independent human review.

Outstanding work includes configuring and testing a real model provider, deploying a compatible backend for public online mode, broader evidence retrieval, independent policy and language review, and mobile/accessibility audits. Full-document semantic retrieval and additional languages should be introduced only with matching evidence and tests.

See [API.md](API.md), [ARCHITECTURE.md](ARCHITECTURE.md), [DEMO.md](DEMO.md) and [data_contracts.md](data_contracts.md) for the current implementation.
