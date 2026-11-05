# Acceptance journey (Gate for hours 0-4)

Status: DRAFT - all three contributors sign below before Step 3.

## Journey 1 - primary (persona P1-MEI)
1. Mei types her goal (settling in + student funding).
2. VERA calls `search_sources` and shows the real tool event.
3. VERA asks only: status category, post-secondary student (yes/no), whether her
   institution offers the relevant newcomer service (yes/no/unknown). She may skip any.
4. Result cards:
   - STU-01 StudentAid BC -> Blocker found (study permit alone does not meet status). Shows S1 excerpt. No funding amount.
   - NEW-02 BC NSP -> Needs information (institution service unknown). Shows S2 excerpt.
   - NEW-03 Federal settlement -> Blocker found, exceptions listed as unchecked. Shows S3 excerpt.
5. Mei opens the NEW-02 criterion and corrects "institution offers service" to "no".
6. Only NEW-02 re-runs; card changes to "No blocker in checked criteria"; a "What changed" note appears;
   the draft enquiry drops/updates any sentence that depended on the old answer.
7. Mei edits and downloads a checklist + provider enquiry. Nothing is sent.

## Journey 2 - uncertainty (persona P2-TOMAS)
1. Tomas: economic-class PR, landed June 2021, wants settlement help.
2. NEW-03 -> Needs official review (cutoff-dependent; calculator not approved). Official guidance linked.
3. No positive eligibility statement is shown.

## Pass criteria
- Every displayed result traces to a rule_id, source_id and source_version.
- No result card says "eligible", "approved", or "entitled".
- Correction re-runs only dependent programs and updates the draft.

Signed: A ______  B ______  C ______
