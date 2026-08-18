# F-PREP-12 — Instantiate the gate log; run the two-context flow once

## Header  *(Charter — PM lane)*
- **Story ID:** F-PREP-12
- **Epic:** EPIC-PREP — Make the gates real
- **Intent element(s):** IE-1 (executable), IE-2 (falsifiable), IE-6 (real evidence)
- **Type:** docs / process
- **Security-sensitive?** **Yes** — this produces the first real RMF evidence artifact
  (CA-2, SA-11). What it claims must be exactly what happened.
- **Routing:** Sentinel (gate log) → Marshal (handoffs) → human approval
- **Blocked by:** every other EPIC-PREP story. This one closes the epic.

## Mandatory Reads
- [ ] `docs/GATE_LOG_SCHEMA.md`
- [ ] `CLAUDE.md` §3 (two-context lifecycle), §7 (commit protocol), §7.2 (append-only gate log), §9
- [ ] `docs/templates/NEXT_PROMPT_GATES-template.md`, `NEXT_PROMPT_FRAMEWORK-template.md`
- [ ] F-PREP-05's dry-run findings

## User Story
As the operator, I want one real story driven through both context windows with a gate-log
row at the end, so that the lifecycle is demonstrated working rather than described working.

## Why this closes the epic
Everything else in EPIC-PREP builds a component. This story is the **integration test**: the
seams either hold or they do not. It also produces the first row in the gate log — which has
a schema, an owner, and an append-only discipline, but **no file and no entries.**

## Acceptance Criteria
- **AC-1 — `_bmad-output/gate-log.md` exists** and conforms to `GATE_LOG_SCHEMA.md`, authored
  by **Sentinel** (§2, §7.2 — an earlier draft wrongly assigned this to Marshal).
- **AC-2 — One real story completes the full lifecycle** across two genuinely separate
  sessions: build context → `NEXT_PROMPT_GATES.md` → cold gate context → Crucible → Sentinel
  → manual review → human approval. A recommended candidate is **F-PREP-02**, which is
  code-bearing and therefore exercises the TDD gate.
- **AC-3 — The gate context is genuinely cold.** It receives only the story file and the
  diff — not the builder's reasoning, justification, or self-assessment. Any leak is a
  blocking finding (§3).
- **AC-4 — Both ledger rows are appended:** the Quick Ledger row and the Detailed Ledger row,
  with real verdicts, real finding counts, a concrete risk note, and a follow-up owner for
  anything open (§7.2).
- **AC-5 — The record says who actually ran the gate.** Crucible and Sentinel do not exist as
  automated agents; the row states the checklist was run by a human, not by an agent (§0, §9).
  Writing it the other way is the epic's most damaging possible failure.
- **AC-6 — Human approval is real.** Explicit "approved" with what was reviewed in the
  approver's own words, per §4.4 anti-rubber-stamp rules. A bare approval is not accepted for
  a security-sensitive story.
- **AC-7 — Handoff continuity is proven.** Marshal writes the next `NEXT_PROMPT_FRAMEWORK.md`
  and a fresh session with no memory can continue from it alone. Test by actually starting
  cold from it.
- **AC-8 — Friction is captured** and fed back to PRD §10 (the Track-B rebuild inventory),
  per the build plan's Week-3 intent.
- **AC-9 — The epic cohesion gate runs** (§3.5) against EPIC-PREP's own criteria, producing
  `COHERENT` or `DRIFT`. `DRIFT` blocks epic close.

## SHALL NOT constraints
- **SHALL NOT** record a verdict that did not happen, or imply an automated gate ran when a
  human ran the checklist by hand (§0, §9). This is the load-bearing honesty rule of the
  entire story.
- **SHALL NOT** edit or delete a gate-log row, ever. Corrections are new entries (Guarantee #6).
- **SHALL NOT** enter a story in the gate log before all four gates pass — in-progress
  stories have no entries (§7.2).
- **SHALL NOT** describe the two-context split as separation of duties in the row, the retro,
  or any write-up (§9). It is context-isolated independent review.
- **SHALL NOT** self-approve. Human approval is the only thing that unlocks promotion
  (Guarantee #1).

## Endpoints touched
N/A — the driven story may have endpoints; this story has none of its own.

## Negative authorization tests planned
N/A for this story. If F-PREP-02 is the driven story, its own obligations apply.

## TDD Red-Phase Evidence
`N/A — non-code story.` *(The driven story carries its own red-phase evidence.)*

## Implementation note
_TBD_

## Epic close-out note
On completion, the operator's standing rule engages: **no edits to settings config or
governance docs without express per-edit permission.** Record it in the retro and in the
handoff so the next session inherits it.

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
