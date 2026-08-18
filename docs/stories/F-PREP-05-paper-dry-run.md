# F-PREP-05 — Paper dry-run of one story, end to end

## Header  *(Charter — PM lane)*
- **Story ID:** F-PREP-05
- **Epic:** EPIC-PREP — Make the gates real
- **Intent element(s):** IE-1 (executable), IE-2 (falsifiable)
- **Type:** docs
- **Security-sensitive?** No
- **Routing:** Marshal → Crucible

## Mandatory Reads
- [ ] `CLAUDE.md` §3 (the two-context lifecycle), §3.1 (routing), §3.3 (handoffs), §4 (gate criteria)
- [ ] `docs/STORY_TEMPLATE.md`, `docs/QUALITY_GATE.md`, `docs/DEFINITION_OF_DONE.md`, `docs/GATE_LOG_SCHEMA.md`
- [ ] `docs/templates/NEXT_PROMPT-template.md`, `NEXT_PROMPT_GATES-template.md`

## User Story
As the operator, I want one imaginary story walked through the entire lifecycle on paper, so
that every point where the process cannot actually proceed is discovered cheaply, before
those blockers are found the expensive way mid-build.

## Why this matters
This is the **highest yield per hour** of the pressure-test methods, and it is the only one
that tests the *seams*. The gate criteria, the templates, and the routing table have each
been reviewed alone; they have never been executed in sequence. F-016's lesson generalizes:
artifacts that read correctly can still fail on first execution, and seams are where the
failures hide.

## Acceptance Criteria
- **AC-1 — A concrete walkthrough exists.** One invented, representative story (an endpoint
  with auth — the case that exercises the most gate machinery) is walked from dispatch to the
  next handoff, recorded as a document. A generic narrative of the process is not acceptable.
- **AC-2 — Every lifecycle step is attempted, in order.** Dispatch → build context →
  implementation → `NEXT_PROMPT_GATES.md` → cold gate context → Crucible → Sentinel →
  manual review → human approval → gate-log row → next `NEXT_PROMPT`. No step is skipped as
  "obvious."
- **AC-3 — Every blocker is recorded as a finding.** Each point where the walkthrough cannot
  proceed — a missing artifact, an undefined format, an ambiguous rule, an unanswerable
  question — is logged with the step, what was needed, and what was missing.
- **AC-4 — Findings are triaged into the epic.** Each blocker is mapped to an existing
  EPIC-PREP story, or raised as a new one. A blocker that maps to nothing is a scope gap and
  must be surfaced explicitly, not absorbed.
- **AC-5 — The information barrier is tested, not assumed.** The walkthrough states exactly
  what the gate context receives and confirms the builder's reasoning is **not** in it (§3).
  Any leak path found is a blocking finding.
- **AC-6 — The 3-round self-healing cap is walked.** Simulate a Crucible FAIL and follow the
  remediation loop, including what happens at the cap and how escalation reaches the human.
- **AC-7 — Honest verdict.** The document states plainly which steps could not be completed
  even on paper. A dry-run that reports everything working is either wrong or was not
  adversarial enough.

## SHALL NOT constraints
- **SHALL NOT** use a real work artifact or any real system, boundary, account, or network
  name for the invented story (§8.1 clean-room, OPSEC). Generic placeholders only.
- **SHALL NOT** resolve a discovered blocker inside this story. Record it and route it —
  fixing as you go destroys the record of what was broken, which is the deliverable.
- **SHALL NOT** describe the two-context split as separation of duties (§9).

## Endpoints touched
N/A — the endpoints in the walkthrough are invented and produce no code.

## Negative authorization tests planned
N/A — non-code story. The invented story *plans* the Guarantee #8 negative tests as part of
AC-2, but nothing is implemented.

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
