# F-PREP-10 — Close the mandatory-read gaps

## Header  *(Charter — PM lane)*
- **Story ID:** F-PREP-10
- **Epic:** EPIC-PREP — Make the gates real
- **Intent element(s):** IE-1 (executable), IE-6 (real evidence)
- **Type:** docs
- **Security-sensitive?** **Yes** — several of the absent documents are security artifacts
  (IL4 baseline, IL6 delta, CDS guidance, STIG checklists). Sentinel owns those.
- **Routing:** Bastion / Sentinel / Codex (per owning lane) → Crucible

## Mandatory Reads
- [ ] `CLAUDE.md` §10 — the category (a)/(b)/(c) split, which already lists these honestly
- [ ] `CLAUDE.md` §3.2 — the mandatory-read table
- [ ] `agents/manifest.json` — `mandatory_reads` per agent
- [ ] F-PREP-04's completeness report — the machine-generated gap list

## User Story
As a gate, I need every document I am told to read to exist, so that the mandatory-read
protocol is a real precondition rather than a list containing paths that were never written.

## The gap
`CLAUDE.md` §10 category (c) lists engine files still to be written:
`docs/security/README.md`, `controls/IL4-baseline.md`, `controls/IL6-delta.md`,
`controls/CDS-guidance.md`, `providers/**`, `DEVSECOPS_SPEC.md`,
`agent-usage-guidelines.md`, `agent-cve-poam-guidelines.md`, `docs/context/**`.

Listing them honestly was correct. But at least one — `docs/architecture/DEVSECOPS_SPEC.md`
— is a **mandatory read** for Bastion in `agents/manifest.json`. A gate whose precondition
cannot be satisfied cannot run, and today nothing detects that.

## Acceptance Criteria
- **AC-1 — The gap list is machine-generated,** taken from F-PREP-04's blocking-category
  output rather than assembled by hand. → depends on F-PREP-04
- **AC-2 — Every mandatory-read gap is closed or reclassified.** For each category-(c) path
  that is also a `mandatory_reads` entry: either the document is written, or the read
  requirement is removed from the manifest with a recorded reason. No path may remain both
  required and absent.
- **AC-3 — Documents are written by their lane owner** (§2): Sentinel for `docs/security/**`,
  Bastion for `DEVSECOPS_SPEC.md`, Codex for the guidance docs. Charter does not write them.
- **AC-4 — Each document is real, not a stub.** A file created only to satisfy a path check
  is a §9 over-claim and is treated as a finding. Where content genuinely cannot be written
  yet, the honest move is AC-2's reclassification, not an empty heading.
- **AC-5 — Remaining category-(c) paths stay honest.** Anything deliberately still unwritten
  remains listed in §10 as (c) and is cited nowhere as if it existed.
- **AC-6 — Corpus citations resolve.** Any control text cited by the new security documents
  is openable per `corpus/MANIFEST.md`, or is marked as not vendored. Never grounded from
  model memory (Guarantee #4).
- **AC-7 — The completeness script goes fail-closed.** Once the blocking gaps are zero,
  F-PREP-04's script is wired into `pre-commit` so new drift is caught mechanically. This is
  the story's exit condition.

## SHALL NOT constraints
- **SHALL NOT** create empty or placeholder files to make a path check pass (AC-4). That
  converts an honest absence into a false claim — the precise failure §9 exists to prevent.
- **SHALL NOT** write any real infrastructure value, account ID, ARN, boundary name, or
  network name into these documents. Placeholders only (§8, §8.1).
- **SHALL NOT** paste from work artifacts. Clean-room: PRD and the operator's own
  descriptions only (§8.1).
- **SHALL NOT** let one agent write another lane's document (§2, Guarantee #5).

## Endpoints touched
N/A.

## Negative authorization tests planned
N/A — non-code story. *(AC-7 wires a script whose own tests live in F-PREP-04.)*

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
