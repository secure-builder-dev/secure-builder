# F-PREP-11 — Falsifiability review: can every gate actually FAIL?

## Header  *(Charter — PM lane)*
- **Story ID:** F-PREP-11
- **Epic:** EPIC-PREP — Make the gates real
- **Intent element(s):** IE-2 (falsifiable), IE-6 (real evidence)
- **Type:** docs
- **Security-sensitive?** **Yes** — a security gate that cannot fail is theater, and
  briefing it as a control would be the §9 failure mode that turns the engine into a
  liability.
- **Routing:** Crucible → Sentinel

## Mandatory Reads
- [ ] `CLAUDE.md` §3.4 (the existing verification table), §3.5 (cohesion gate), §5.1 (portability)
- [ ] `docs/QUALITY_GATE.md`, `docs/DEFINITION_OF_DONE.md`
- [ ] F-PREP-08's check registry
- [ ] `SECURE_BUILDER_PRD.md` §4.4, §4.5

## User Story
As the operator, I want every gate demonstrated failing, so that a PASS is evidence
something was checked rather than evidence nothing was.

## Why this matters
`CLAUDE.md` §3.4 already does this for the original gates and is unusually honest about the
heuristic rows. Two newer gates have **never been through it**: the **epic cohesion gate**
(§3.5) and the **portability conformance** rules (§5.1 rule 9). Neither has a stated failure
mode, so neither can currently be shown to discriminate.

F-016 is the precedent: three of six defects were checks that *looked* correct and silently
could not fail — the secret scan disabled by the word "example", the TDD check cured by a
later remediation commit. Both passed review by reading. Only execution found them.

## Acceptance Criteria
- **AC-1 — Every gate has a demonstrated failing case.** For each gate in §3.4 plus the
  cohesion and portability gates: a concrete input that makes it FAIL, and the observed
  failure recorded. An argued failure mode is not sufficient.
- **AC-2 — The §3.4 table is extended** to cover the cohesion gate and portability
  conformance, in the same format, with the same honesty about what is machine-checkable.
  *(Editing `CLAUDE.md` requires the operator's express permission — propose the diff.)*
- **AC-3 — Heuristic rows are re-tested, not trusted.** The two named heuristics — "no DB
  mocks" via import/mock detection, and skip-detection — are each shown catching their target
  **and** a case they miss is documented. Known blind spots beat assumed coverage.
- **AC-4 — The trivially-neutered-test hole is characterized.** `expect(true).toBe(true)`
  passes skip-detection. State plainly whether anything catches it and, if not, that the
  manual gate is the only backstop (§3.4).
- **AC-5 — Human-attested gates are labelled, never "verified."** Mandatory reads and the
  manual security review are marked human-attested with their negative-check nature stated
  (§3.2, §9).
- **AC-6 — Cohesion gate gets a real `DRIFT` case.** A worked example where each story
  passed individually but the assembled epic violates a matrix `SHALL NOT` or leaves an
  intent element uncovered — the exact scenario §3.5 exists for.
- **AC-7 — Any gate that cannot be made to fail is reported as a finding**, not quietly
  omitted. That is the single most valuable output this story can produce.

## SHALL NOT constraints
- **SHALL NOT** record a gate as falsifiable on the strength of reading its criteria. F-016
  proved review-by-reading misses exactly this defect class. Execute it.
- **SHALL NOT** describe a human-attested gate as verified (§9).
- **SHALL NOT** weaken a gate so that a failing case is easier to construct. The failing case
  is constructed against the gate as written.
- **SHALL NOT** imply automation where a human ran the checklist by hand (§0, §9). Crucible
  and Sentinel do not exist yet; say so.

## Endpoints touched
N/A.

## Negative authorization tests planned
N/A — non-code story. This story *is* the negative-testing discipline applied to the gates
themselves, the same principle as Guarantee #8 one level up.

## TDD Red-Phase Evidence
`N/A — non-code story.`

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
