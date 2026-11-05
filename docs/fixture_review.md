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
