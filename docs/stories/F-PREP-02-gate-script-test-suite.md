# F-PREP-02 — Test suite for the gate scripts

## Header  *(Charter — PM lane)*
- **Story ID:** F-PREP-02
- **Epic:** EPIC-PREP — Make the gates real
- **Intent element(s):** IE-2 (falsifiable), IE-3 (scripts own decidable checks), IE-6 (real evidence)
- **Type:** feature (code)
- **Security-sensitive?** **Yes** — `secret_scan.py` is a Guarantee #7 control, and a false
  negative in it is a security failure. F-016 found exactly that defect.
- **Routing:** Forge → Crucible → Sentinel

## Mandatory Reads
- [ ] `scripts/gates/check_lanes.py`, `check_tdd.py`, `secret_scan.py`
- [ ] `scripts/README.md`
- [ ] `CLAUDE.md` §3.4 (what each gate proves), §4.1 (TDD), §4.2 (quality criteria)
- [ ] `docs/QUALITY_GATE.md`

## User Story
As the operator, I want the gate scripts to have a committed, reproducible test suite, so
that the layer enforcing TDD is not itself the only untested code in the repository.

## Why this matters
F-016 verified these scripts with ad-hoc shell probes that **died with that session**. The
scripts that enforce Guarantee #3 currently have no test of their own — and three of the six
defects found were bypasses of the very guarantee the script exists to enforce. Every check
a script owns reliably is a check the 24 GB local model never has to be trusted with, so the
deterministic layer is load-bearing for the whole Track-C design. Untested, it is a claim.

## Acceptance Criteria  *(each maps by name to ≥1 test)*
- **AC-1 — Suite exists and is stdlib-only.** Runs via `python -m unittest` (or equivalent)
  with **no third-party dependency**, per the air-gap constraint. → `test_suite_runs`
- **AC-2 — Every script exit path is covered.** For each of the three scripts: exit 0
  (clean), exit 1 (finding), exit 2 (usage/config error). Conflating 1 and 2 is a defect
  class F-016 already fixed; the suite must lock it. → `test_exit_codes_*`
- **AC-3 — Each gate is proven to FAIL.** Not "can be argued to fail" — an asserted failing
  case per check: impl-without-tests, tests-after-impl, the remediation-commit ordering
  bypass, blatant secrets, forbidden paths, out-of-lane files. → `test_falsifiable_*`
- **AC-4 — The F-016 regressions are pinned.** A named regression test for each of the six
  defects, so none can silently return: unicode output, prose-disguised secrets, the
  last-impl-commit bypass, `fnmatch` case sensitivity, exit-code conflation, the python-shim
  probe. → `test_regression_f016_*`
- **AC-5 — No false positives on the real repo.** The suite asserts `secret_scan.py` exits 0
  across all tracked files, so a tightened pattern that breaks the repo fails loudly.
  → `test_repo_sweep_clean`
- **AC-6 — Platform determinism is asserted, not assumed.** Tests that would differ by host
  OS (path case, line endings, console encoding) assert the OS-independent result.
  → `test_platform_deterministic_*`
- **AC-7 — Git fixtures are hermetic.** Tests needing history build a throwaway repo in a
  temp dir; the suite never depends on this repository's real history. → `test_fixture_isolation`
- **AC-8 — Wired into the gate.** `scripts/README.md` documents how to run it, and the
  quality gate for engine work requires it green.

## SHALL NOT constraints
- **SHALL NOT** add a third-party test dependency. Air-gapped targets get no package index.
- **SHALL NOT** assert on exact prose of a message where asserting on the exit code and the
  presence of the finding would do — brittle tests get deleted, and a deleted test is a
  removed gate.
- **SHALL NOT** weaken a check to make a test pass. If a check is wrong, that is a finding
  and a separate fix, recorded.
- **SHALL NOT** mark this story done without the two-commit TDD sequence in `git log`. This
  story enforcing TDD while skipping TDD would be the epic's most embarrassing failure.

## Endpoints touched
N/A — no application endpoints.

## Negative authorization tests planned
N/A at the HTTP layer. The **equivalent** obligation for this story is AC-3: every gate
must be shown rejecting bad input, not merely accepting good input. That is the same
principle as Guarantee #8, applied to gates instead of endpoints.

## TDD Red-Phase Evidence  *(Forge — paste before the impl commit)*
Commit (tests only): `<hash>` → `[F-PREP-02/tests] failing tests for gate-script suite`
```
<first 20–30 lines of the failing run>
```

## Implementation note  *(Forge)*
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
