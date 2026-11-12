# Fixture review checklist (Contributor A)

Held-out cases C21-C30 were drafted by the rules author on 2026-11-05 and are NOT yet independent.

For each held-out case, without opening rules.py:
1. Read the facts and the S1-S4 .txt snapshots.
2. Write the expected state for STU-01, NEW-02, NEW-03 yourself.
3. If you disagree with the file, change the file (not the code) and note why below.
4. Set "author" to your name and "reviewer" to the rules author.
5. Then run: python tests/fixture_runner.py heldout   and report n/N.

For date_boundaries.json: confirm or correct every row with needs_verification=true.

| Case | Agree? | Note |
|---|---|---|

## 2026-11-12 — held-out disagreement to resolve (hybrid branch)

Commit 185e545 changed NEW-03-R1 to ask whether a special IRCC pathway applies (`federal_exception`) and, in the same
commit, edited the expected NEW-03 result of held-out cases C21, C22 and C27 from `blocker_found` to `needs_information`.
Held-out cases must not be edited by whoever changes the rules, so the hybrid branch restores the original expectations.

Current result: `python tests/fixture_runner.py heldout` → 7/10. The three misses are exactly C21, C22, C27 (NEW-03).

The reviewer (not the rule author) decides, using the S3 snapshot text only:
- [ ] Is "a permit alone, special pathway unknown" a *blocker* or *needs information* under S3?
- [ ] Update C21, C22, C27 accordingly, record your name in `author`, and note the reason in the table above.
