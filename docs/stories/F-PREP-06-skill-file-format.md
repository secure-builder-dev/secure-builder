# F-PREP-06 — Skill-file format specification

## Header  *(Charter — PM lane)*
- **Story ID:** F-PREP-06
- **Epic:** EPIC-PREP — Make the gates real
- **Intent element(s):** IE-1 (executable), IE-4 (portable to target substrate)
- **Type:** new ADR
- **Security-sensitive?** No application surface — but Sentinel's own checks will live in
  this format, so a weak format weakens the security gate. Sentinel reviews.
- **Routing:** Keystone → Crucible → Sentinel

## Mandatory Reads
- [ ] `CLAUDE.md` §2 (manifest), §2.1 (activation), §3.2 (Sentinel forced-read), §5.1 (portability rules 1–6)
- [ ] `SECURE_BUILDER_PRD.md` §7 (agent builder), §10 (orchestration requirements), §10.2
- [ ] `docs/architecture/ADR-LOG.md` ADR-0005
- [ ] `agents/manifest.json`

## User Story
As the engine, I need a defined skill-file format, so that eleven personas can be authored
as portable instruction artifacts instead of eleven improvisations.

## Why this is the keystone
There are **eleven personas and zero skill files.** PRD §10 requires a defined format
(persona, capabilities, owned artifacts, activation pattern) and §5.1 now adds hard
constraints on top: declared token budget, sliceable, self-contained slices, data over
prose, imperative gate checklists, no runtime-specific syntax. **All of Week 2 blocks on
this**, and authoring to the rules is explicitly cheaper than retrofitting — which is why
ADR-0005 landed before the skills were written.

## Acceptance Criteria
- **AC-1 — The format is specified as an ADR** with alternatives and consequences, not as a
  README convention.
- **AC-2 — Required sections are enumerated and binary.** Persona identity, lane, owned
  artifacts, mandatory reads, capabilities, activation pattern, declared token budget. A
  reader can tell mechanically whether a given file conforms.
- **AC-3 — Conformance is machine-checkable.** The spec is concrete enough for a stdlib
  script to validate a skill file. Whether that script is written here or in F-PREP-08, the
  spec must not require judgment to check structure.
- **AC-4 — §5.1 rules 1–6 are each satisfied, demonstrably.** For each rule, the spec states
  how the format enforces it. Rule 3 (self-contained slices) is the sharp one: the format
  must make it *impossible* for a skill file to depend on an unresolved cross-reference.
- **AC-5 — Data lives in the manifest, not duplicated in prose.** Lanes, globs and read
  lists come from `agents/manifest.json` (§5.1 rule 4). The format states how a skill file
  references manifest data without restating it — while still satisfying AC-4. Resolving
  that tension is the substance of this story, not a detail.
- **AC-6 — No runtime-specific syntax.** No chat template, tool-call encoding, or
  frontier-model-specific idiom. The per-model adapter owns that (§5.1 rule 6).
- **AC-7 — Proven on a real skill, not an example.** One actual agent — **Sentinel**, the
  hardest case, with its forced skill-load-and-attest protocol — is authored in the format
  and its assembled context measured against the `laptop-resident` budget.
- **AC-8 — Budget is declared and met.** The spec declares a per-skill token budget, and the
  AC-7 artifact comes in under it. Measured, not estimated.

## SHALL NOT constraints
- **SHALL NOT** design the format around what the current frontier runtime auto-loads. The
  target substrate has **no auto-load mechanism at all** (§3.2 portability caveat); a format
  that assumes ambient context is broken by definition.
- **SHALL NOT** make any cross-reference load-bearing (§5.1 rule 3).
- **SHALL NOT** claim portability implies equivalent judgment (§5.1 honesty, §9).
- **SHALL NOT** author the remaining ten skills in this story. This delivers the format and
  one proof case; the rest is the next epic.

## Endpoints touched
N/A.

## Negative authorization tests planned
N/A — non-code story.

## TDD Red-Phase Evidence
`N/A — non-code story.` *(If AC-3's validator is written here, it is code-bearing and the
two-commit sequence applies to that script.)*

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
