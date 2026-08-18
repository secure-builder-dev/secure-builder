# F-PREP-04 — Completeness script: every referenced path exists

## Header  *(Charter — PM lane)*
- **Story ID:** F-PREP-04
- **Epic:** EPIC-PREP — Make the gates real
- **Intent element(s):** IE-1 (executable), IE-3 (script-decidable), IE-6 (real evidence)
- **Type:** feature (code)
- **Security-sensitive?** No
- **Routing:** Forge → Crucible → Sentinel

## Mandatory Reads
- [ ] `CLAUDE.md` §10 — the three path categories (a) exists / (b) per-app / (c) not yet written
- [ ] `CLAUDE.md` §3.2 — the mandatory-read table
- [ ] `agents/manifest.json` — `mandatory_reads` as data
- [ ] `docs/security/corpus/MANIFEST.md` — the corpus's own honesty ledger

## User Story
As the operator, I want a script that verifies every file path referenced in the governance
docs actually exists, so that citing a document that was never written is caught mechanically
instead of by someone noticing.

## Why this matters
`CLAUDE.md` §10 already warns that citing a category-(c) path as if it existed is a §9
over-claim. Today the only thing preventing that is attention. Worse, **a mandatory read
that does not exist is a gate that cannot run** — `agents/manifest.json` sends Bastion to
`docs/architecture/DEVSECOPS_SPEC.md`, which is not in the repo. That is a silent hole in
the §3.2 protocol, and it is exactly the kind of drift a script should own rather than a
model (IE-3).

## Acceptance Criteria
- **AC-1 — Extracts referenced paths.** Finds path-like references in tracked `.md` files
  and `agents/manifest.json` (backticked paths, markdown links, manifest `mandatory_reads`
  and `owned_globs`). → `test_extracts_paths`
- **AC-2 — Classifies against §10, does not just fail.** Each reference resolves to
  **(a) exists**, **(b) per-app — expected absent here**, or **(c) declared-but-absent**. A
  flat "file not found" would flag every legitimate category-(b) path and be ignored within a
  week. → `test_classifies_abc`
- **AC-3 — Category (c) is reported, and reported honestly.** Declared-but-absent paths are
  listed with the file and line that cites them. → `test_reports_category_c`
- **AC-4 — Mandatory-read gaps are escalated.** A path that is *both* category (c) *and* a
  `mandatory_reads` entry is reported as **blocking**, separately from ordinary (c) drift —
  it breaks a gate, not just a doc. → `test_mandatory_read_gap_is_blocking`
- **AC-5 — Exit codes follow the house contract.** 0 = clean, 1 = finding, 2 = usage/config
  error. → `test_exit_codes`
- **AC-6 — Stdlib-only and platform-deterministic.** No third-party dependency; identical
  verdict on Linux and Windows. → `test_no_third_party`, `test_platform_deterministic`
- **AC-7 — The category-(b) allowlist is data, not a regex buried in code.** Reviewable and
  editable without reading Python (§5.1 rule 4). → `test_allowlist_is_data`
- **AC-8 — TDD sequence present** — test-only commit precedes implementation in `git log`.

## SHALL NOT constraints
- **SHALL NOT** auto-create a missing file to make itself pass. Reporting the gap is the
  whole job; writing an empty stub converts an honest absence into a §9 over-claim.
- **SHALL NOT** classify a path as category (b) merely because it is missing. Category (b)
  is an explicit, reviewed list.
- **SHALL NOT** be wired into `pre-commit` as fail-closed in the same story that introduces
  it — the repo has known category-(c) paths today and would be unable to commit. Wiring is
  F-PREP-10's exit condition, after those gaps close.

## Endpoints touched
N/A.

## Negative authorization tests planned
N/A at the HTTP layer. Equivalent obligation: AC-3 and AC-4 require demonstrated findings.

## TDD Red-Phase Evidence
Commit (tests only): `<hash>` → `[F-PREP-04/tests] failing tests for completeness script`
```
<failing run output>
```

## Implementation note
_TBD_

---

## Gate Results

### Quality Gate — Crucible
```
QUALITY GATE VERDICT [ ]
```

### Security Gate — Sentinel
```
GATE VERDICT [ ] | SECURITY_TIER [IL4]
open findings: [ ]   blocking findings: [ ]
```

### Manual Security Review
- Verdict: [ ]

### Human Approval
- **APPROVED by:** _pending_
