# Self-Test Discipline — Behavioral Specification

**Version:** 1.1 · drafted 2026-09-20, hardened after gap analysis
**Part of:** Engine Specification Package
**Status:** specification only — implementation-independent
**Copyright:** © 2026 Casey Houle. All rights reserved. Confidential — not for distribution.

---

## 0. Why this is a specification and not a style guide

The harness is a system whose entire output is assurance. A defect in the harness does not produce a
wrong answer — it produces a **confident** answer that is wrong, and it produces it silently, and it
keeps producing it until someone reads the code.

Every false-green catalogued in the companion specs was written by a competent engineer who believed
the check worked. None were caught by the check's own test suite, because the tests were written by
the same person in the same sitting under the same assumption.

This document specifies the testing discipline that finds those. It is short, and it is the highest
value-per-page in the package.

---

## 1. The governing rule

**REQ-1.1** A check is not evidence until it has been **observed failing** against a deliberately
broken input.

**REQ-1.2** "The tests pass" is not acceptance criteria for a new check. "The tests fail when I break
the thing, and here is the output" is.

**Rationale.** Passing demonstrates the check runs. It does not demonstrate the check discriminates.
A check that always passes runs, passes, and is worthless — and is indistinguishable from a working
one by every signal except deliberate breakage.

---

## 2. Negative fixtures

**REQ-2.1** Every check MUST have at least one fixture that makes it fail, exercised as part of the
self-test suite.

**REQ-2.2** The negative fixture MUST be committed alongside the check, in the same change.

**REQ-2.3** A check whose negative fixture is removed MUST be treated as an untested check.

**REQ-2.4** Fixtures MUST be constructed, not borrowed from production data.

**Rationale.** A borrowed artifact stops exercising the case when production changes, and nobody
notices because it still parses.

---

## 3. Mutation as the acceptance procedure

**REQ-3.1** When a check is added or changed, the author MUST break the property it asserts and
confirm the check fails.

**REQ-3.2** The mutation and its observed result MUST be recorded in the change description.

**REQ-3.3** Where a check has several distinct assertions, **each** MUST be mutated independently.

**Rationale.** A suite of ten assertions where nine are load-bearing and one is vacuous passes
identically to one where all ten are. Only per-assertion mutation separates them.

**REQ-3.4** A mutation that does **not** produce a failure MUST be treated as a finding against the
test, not as evidence that the code is robust.

**Worked example.** A test asserting that an overridden result is marked *unverified* searched the
whole output for that word. Mutating the verdict line to remove the marking left the test passing,
because an earlier warning line also contained the word. The test was rewritten to read the verdict
line alone. Had the mutation not been run, a test that could never fail would have shipped inside a
change whose entire purpose was removing tests that could never fail.

---

## 4. Assertion precision

**REQ-4.1** An assertion MUST be narrow enough that the wrong outcome fails it.

**REQ-4.2** Assertions on process results MUST name the **specific** value that means success, not a
class of values.

**Worked example.** A test asserting a malware scanner "exits non-zero on detection" passed when the
scanner failed to start, because a container-level failure also exits non-zero. Exit code 1 meant
detection; 125 meant the container never ran. The corrected assertion requires exactly the detection
code and reports every other non-zero value as *the scanner fell over*, which is a different result
and must not read as success.

**REQ-4.3** Assertions on output MUST target the specific line carrying the claim, not the whole
transcript.

**REQ-4.4** Where an assertion must match loosely, the test MUST additionally assert the **absence**
of the wrong outcome.

---

## 5. Hermetic fixtures

**REQ-5.1** Tests MUST NOT require a network, a container runtime, a hardware device, a database, or
credentials.

**Rationale.** A test with an environmental dependency is a test that is skipped on most machines,
and a skipped test is an untested check that reports as tested. The skip is usually invisible in
summary output.

**REQ-5.2** External tools MUST be stubbed by placing executables earlier on the search path.

**REQ-5.3** Stubs MUST record their invocations, so a test can assert **what was called** and not
only what was printed.

**Rationale.** Asserting on output tests the message. Asserting on invocations tests the behavior.
Both matter, and the second catches the case where the right message is printed by the wrong path.

**REQ-5.4** Each test case MUST construct a throwaway working tree and remove it afterward.

**REQ-5.5** Tests MUST NOT depend on execution order or on state left by a previous case.

**REQ-5.6** Where a capability genuinely cannot be stubbed, the test MUST **skip visibly**, and the
suite summary MUST report the skip count separately from the pass count.

**Rationale.** A suite reporting "61 passed" when two were skipped is misreporting. "59 passed, 2
skipped" invites the question of what is not being tested, which is the question that should be
invited.

---

## 6. The suite must run where it matters

**REQ-6.1** The self-test suite MUST be wired into the single check command and therefore into CI.

**REQ-6.2** A test suite that exists but is not invoked by any automated path MUST be treated as
absent.

**Rationale — observed, and it is the most common form of this defect.** The reference
implementation carried a fifty-eight-case suite that no command ran. Every regression guard in it
passed permanently, because nothing executed it. Wiring it into the check command took one line and
immediately turned CI red, exposing a scanner that had never worked in any environment with a
container runtime.

The lesson generalizes: **an uninvoked test file is worse than no test file**, because it produces
the appearance of coverage. Auditing for them is worth doing once per codebase — list every test
file, then list every file referenced by an automated path, and diff.

**REQ-6.3** The same command MUST run locally and in CI, with no divergence.

### 6.1 The second tier — where the external tools actually run

**REQ-6.4** A **second, explicitly separate test tier** MUST exist that executes the real external
tools — the actual scanner containers, the actual runtimes — and it MUST pass before a release of
the harness.

**REQ-6.5** The integration tier MUST report which environment it ran in, and that report MUST be
part of the release record.

**REQ-6.6** The hermetic tier (§5) gates every push. The integration tier gates a **version**. The
two MUST NOT be merged, and the hermetic tier MUST NOT be weakened to accommodate the integration
tier.

**REQ-6.7** An integration tier that has never run is equivalent to no integration tier, and the
harness MUST NOT be released on the strength of the hermetic tier alone.

**Rationale, and it is the sharpest consequence of §5's rules.** REQ-5.1 forbids tests that need a
network, a container runtime or a device, for reasons that remain correct: an environmental
dependency produces invisible skips. The consequence, unstated until now, is that **in a harness
whose primary job is orchestrating external scanners, no test ever runs a scanner.** Every
externally-facing code path is exercised only against stubs that were written from the same
assumptions as the code.

This is not hypothetical. In the reference implementation a malware scanner was broken in every
environment with a container runtime — it referenced an image tag that had never existed — and the
hermetic tests were green throughout, because the stub answered exactly as the code expected. The
defect was found by a human reading logs, months later.

The failure is worse in a controlled environment, where the toolchain differs most (mirrored
registries, local package sources, offline detection data) and is hardest to reach for debugging. A
harness whose external paths have never been executed anywhere will fail first in the place where
failure is most expensive to diagnose.

**REQ-6.8** Where the integration tier cannot run in a given environment, that MUST be recorded as
*not verified in this environment* against that release — never as a pass.

---

## 7. The harness's own checks are checks

**REQ-7.1** Everything in this document applies to the harness's verification tooling itself — the
consistency checkers, the reference-integrity checks, the schema validators.

**Rationale — observed.** A consistency checker added to catch document drift contained the same
defect it was written to catch: it read its input from a file that a later restructure emptied,
found nothing to compare, and passed vacuously. It was caught by asking what would happen under the
restructure, before shipping it. Nothing else would have caught it, because it passed.

**REQ-7.2** Any check that iterates over a discovered set MUST fail when that set is empty, unless
emptiness is a legitimate state that is separately named.

**Rationale.** "Found nothing to check, therefore passed" is the single most common shape of a
vacuous pass. It is worth grepping a codebase for loops over discovered sets and auditing each one
for this.

---

## 8. Verification before irreversible action

**REQ-8.1** An automated sequence that runs a verification before an irreversible action MUST branch
on the verification's result.

**REQ-8.2** A sequence MUST NOT continue past a failed verification.

**Worked example.** A change was committed and pushed after its verification had already failed,
because the command chain continued past a non-zero exit. The verification ran, its failure was
displayed, and the sequence proceeded. This is worse than skipping the verification, because the
record shows diligence that did not occur.

**REQ-8.3** Where a sequence is scripted, it MUST be written so that a failure stops it by default
rather than requiring an explicit guard at each step.

---

## 9. Self-test suite structure

**REQ-9.1** The suite SHOULD be organized by the component under test, with a named group per
component.

**REQ-9.2** Each assertion SHOULD print a single line naming what it asserted.

**Rationale.** When a check regresses months later, the failing line should say what property broke
without requiring the reader to open the test.

**REQ-9.3** Failure output MUST include the observed value, not only the expectation.

**REQ-9.4** The suite MUST report pass, fail and skip counts separately and MUST exit non-zero on any
failure.

**REQ-9.5** Where a check's correct behavior depends on project shape, the suite MUST cover **each
shape**, including the shapes where the check does not apply.

**Rationale.** The not-applicable path is the one that silently becomes a false green. It needs a
test at least as much as the applicable path does.

---

## 10. A standing audit

**REQ-10.1** Periodically — at minimum when adopting this spec — the following audit SHOULD be run:

| # | Question | Finds |
|---|---|---|
| 1 | Which test files are not referenced by any automated path? | Dormant suites (§6.2) |
| 2 | Which checks have no negative fixture? | Unproven checks (§2.1) |
| 3 | Which loops over a discovered set pass when the set is empty? | Vacuous passes (§7.2) |
| 4 | Which assertions match a class of values rather than a value? | Imprecise assertions (§4.2) |
| 5 | Which assertions search whole output rather than a specific line? | Wrong-line matches (§4.3) |
| 6 | Which tests require an environment not present in CI? | Invisible skips (§5.1) |
| 7 | Which command sequences continue past a failed verification? | Ignored verification (§8.2) |
| 8 | Which external-tool code paths are exercised only against stubs? | Untested integration (§6.4) |

**REQ-10.2** Findings from this audit are findings, and follow the ordinary disposition rule: each
becomes a check or a checklist line (companion spec 01, §1.4).

---

## 11. Non-requirements

- **No coverage percentage target for the harness's own code.** Coverage measures execution, not
  discrimination. A mutated check that still passes had full coverage.
- **No mocking of the file system or version control.** Construct real throwaway trees; they are
  cheap and they catch real path handling.
- **No snapshot tests of long output.** They pass until someone reformats, then get regenerated
  without being read.
- **No test that asserts only "did not error."**
