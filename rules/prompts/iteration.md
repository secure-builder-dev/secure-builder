© 2026 Casey Houle. All rights reserved. Human-owned; in the build's governance set.

Read ledger.tsv. Pick the lowest-ordered requirement with status `todo` whose
stage prerequisites are all `done`. Ordering: spec number, then requirement
number within the spec, compared numerically component by component
(01/REQ-1.1.1 < 01/REQ-1.1.2 < 01/REQ-1.2.1 < 02/REQ-1.1). Set it to `doing`
and commit that.

Read the requirement AND its rationale from specs/. If the requirement is
ambiguous, do not guess: write the question to .journal/questions and pick the
next requirement instead.

If a requirement is WRONG rather than ambiguous, do not implement it and do not
reinterpret it. Write the case to .journal/amendments-proposed and move on.
Amendments are decided by the human, never by the loop.

Implement it. Write the test first, watch it fail, then make it pass.

Mutate: break the property with a property-level edit to the implementation
(never delete, rename or remove the subject), capture the failing output,
restore, capture the passing output. Write receipts/<spec>-<req>.txt in the
schema tools/progress.py enforces. If the mutation does NOT produce a failure,
the test is wrong. Fix the test, not the code, and do not mark done.

Run `python -m engine check`. If red, fix before continuing. Never commit past
a red check.

Update the ledger row to `done` with the impl pointer and receipt path. Commit.

Every authored file carries the header: © 2026 Casey Houle. All rights reserved.
Commits are authored and signed as Casey Houle only. No other attribution, ever.

Append three lines to .build-log.md. Stop.
