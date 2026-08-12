# QUALITY_GATE.md — Crucible's Quality Gate

> **Owner:** Crucible (Test Architect). **Source of record:** `SECURE_BUILDER_PRD.md`
> §5.2 / §5.3 / §4.4. **Operationalized by:** `CLAUDE.md` §4.2.
>
> **Today's reality (Phase 1):** Crucible is not yet built as an automated agent (PRD §3.1,
> Phase 2). Until then this checklist is run by the operator and the AI assistant **by
> hand**, and the verdict is recorded the same way. The gate is real now; its automation
> is Phase 2.

The Quality Gate runs **after Forge (implementation), before Sentinel (security).** It
is **binary — PASS or FAIL. No partial credit, no "PASS with notes."** A single failing
criterion is a FAIL and returns the story to the implementer for remediation and a
re-run.

---

## 1. Criteria

### 1.1 TDD compliance (Guarantee #3)

- A **test-only commit precedes the implementation commit** in `git log`
  (`[S-XXX/tests]` before `[S-XXX/impl]`). No prior failing-test commit on a code-bearing
  story is an automatic **FAIL** regardless of any agent's assertion.
- The story file contains a `### TDD Red-Phase Evidence` section with the first 20–30
  lines of the failing-test output.
- **No skipped tests** — none of `it.skip` / `test.skip` / `xit` / `xtest`.
- **No DB mocks** — integration tests hit a real PostgreSQL via testcontainers, not a
  mocked database.

> **Heuristic caveat (state honestly).** Skip-detection catches the *named* annotations
> above but not a test trivially neutered without them (e.g., `expect(true).toBe(true)`).
> "No DB mocks" relies on import/mock-pattern detection. The manual gate (§4.4 of the
> constitution) is the backstop for what these heuristics miss. Do not claim exhaustive
> detection.

### 1.2 Coverage thresholds

**Minimum line coverage, measured on the story diff — not the project average.**

| Layer | Minimum |
|---|---|
| Service layer | 80% |
| Repository layer | 80% |
| Route handlers | 70% |
| Middleware | 80% |

Coverage below any applicable threshold blocks PASS.

### 1.3 Negative test coverage (every endpoint story — Guarantee #8)

Every endpoint ships with tests proving it *rejects*, not merely that it serves the
authorized caller:

- **401** — no token.
- **403** — valid token, wrong role.
- **IDOR** — user A cannot reach user B's resource.
- **Invalid input** — malformed / missing / out-of-range → **400**.
- **Conflict** — uniqueness / mutual-exclusivity under concurrent or duplicate requests.

A passing happy-path test is **not** sufficient evidence an endpoint is safe.

### 1.4 ATDD compliance

Every acceptance criterion in the story maps **by name** to ≥1 test. Untested ACs block
PASS. (Machine-checkable *partially* — the name mapping is checkable; that the test
*actually exercises* the AC is judgment.)

### 1.5 CI quality stage

- `npm run lint` exits **0**.
- `npm run typecheck` exits **0**.
- `npm test` exits **0** with **no skipped tests**.
- **No debug statements** (`console.log` / `console.error` / debug calls) in production
  paths.

### 1.6 Flaky-test check

Non-deterministic tests pass **3 consecutive runs.** A test that fails any of the three
is flaky and blocks PASS until stabilized.

---

## 2. Android Track additions (`APP_TRACK=android`)

When the story is on the Android track, these apply **in addition** to §1 before Crucible
issues PASS:

- **ktlint** — zero violations.
- **Detekt** — zero `error`-severity issues.
- **JUnit 5 coverage** — meets the same per-layer thresholds as web (§1.2).
- **TDD two-commit** with a red-phase **JUnit** failure (same rule as §1.1); **both
  commit hashes** required in the gate record.
- Supply-chain scan is **OWASP Dependency-Check** (or equivalent SCA) over the resolved
  Gradle graph, same severity matrix as web (see `DEPENDENCY_POLICY.md`).

---

## 3. What is machine-checkable vs. attested (honest split)

| Criterion | Machine-checkable? |
|---|---|
| TDD two-commit ordering, skip annotations, no DB mocks | **Yes** (named patterns only; heuristic on the last two) |
| Coverage thresholds on the diff | **Yes** |
| Lint / typecheck / no skipped tests / no debug | **Yes** |
| Flaky check (3 runs) | **Yes** |
| ATDD AC→test name mapping | **Partially** — name mapping yes; meaningful exercise is judgment |
| Negative tests *present* | **Yes** (existence); *correct/sufficient* is judgment |

The "Yes" rows are deterministic for their **named** patterns (git-log ordering, exit
codes, coverage numbers, listed annotations). Do not describe the heuristic sub-checks as
exhaustive.

---

## 4. Verdict format

Crucible issues exactly this shape:

```
QUALITY GATE VERDICT [PASS/FAIL]
- TDD compliance: [PASS/FAIL]  (test-only commit <hash> precedes impl <hash>)
- Coverage: service [x%/PASS|FAIL] | repository [x%] | routes [x%] | middleware [x%]
- Negative tests present: [401/403/IDOR/400/conflict — listed]
- ATDD: [x/x ACs covered]
- CI stage: lint [0] | typecheck [0] | tests [0, no skips] | no debug statements
- Flaky check: [PASS/FAIL/N/A]
- Open findings: [n]   Blocking findings: [n]
```

**FAIL** → return to implementer with the failing criteria named; remediate; re-run the
full gate. **PASS** → proceed to Sentinel (Security Gate). Nothing about a Crucible PASS
substitutes for the Security Gate, the Manual Review, or human approval.
