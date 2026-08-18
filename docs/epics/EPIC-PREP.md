# EPIC-PREP — Make the gates real

> **Lane:** Charter (PM). **Source of record:** `SECURE_BUILDER_PRD.md` §4, §10, §14;
> operationalized by `CLAUDE.md` §0, §3, §5.1. **Track:** F-prefix (engine/framework work).
>
> **Artifact budget (`CLAUDE.md` §5.1 rule 1): ≤ 3,000 tokens.** This file is a prompt.

---

## Why this epic exists

`CLAUDE.md` §3 specifies a four-gate chain. **Most of it is not executable.** The gate
criteria are prose, the agents that would run them do not exist, the scripts that own the
deterministic checks were never tested, and the whole thing has only ever run on a
platform the engine does not ship to.

The operator decision of 2026-08-11 stands: **harden the structure before any epics.**
This epic is the exception that proves it — it is not feature work, it is the work that
makes feature work gateable. It also follows Phase 0's own ordering (§2.3): gap-hardening
at stage 3 precedes backlog generation at stage 4. The engine obeys the sequence it
imposes on everything else.

**Trigger for writing it now:** F-016 executed the F-006 gate scripts for the first time
and found six defects, three of which defeated the guarantee the script exists to enforce.
That is the evidence that specified ≠ working, and it generalizes to everything below.

## Intent elements this epic is built toward

Provisional traceability. Phase 0 has **not** been run on Secure Builder itself, so there
is no ratified document matrix; these are drawn from the PRD, which is the engine's intent
document. **This mapping is a draft until a human ratifies it** (§2.3, Guarantee #1).

| ID | Intent element | Source |
|---|---|---|
| **IE-1** | Every gate is *executable*, not merely specified | PRD §4, §5.2, §5.4 |
| **IE-2** | Every gate is *falsifiable* — it can demonstrably FAIL | PRD §4.4 · CLAUDE.md §3.4 |
| **IE-3** | Script-decidable checks are owned by scripts, never by a model | PRD §10 · NEXT_PROMPT item 3 |
| **IE-4** | Instruction artifacts run on the target substrate, not only the frontier model | PRD §10.2 · ADR-0005 |
| **IE-5** | The engine runs where it ships — offline, Linux, 24 GB | PRD §14 · ADR-0003 |
| **IE-6** | Evidence is real and attributable, never asserted | PRD §2 G#6, §8.1 |

## SHALL NOT constraints (bind every story in this epic)

- A story **SHALL NOT** report a gate as automated when a human ran the checklist by hand
  (§9). Say which it was.
- A story **SHALL NOT** describe the two-context split as separation of duties (§9).
- A story **SHALL NOT** describe a human-attested gate as "verified" (§3.2, §3.4).
- A story **SHALL NOT** introduce a check whose verdict differs by host OS. Determinism
  across the dev laptop and the air-gapped Linux target is a correctness property, not a
  preference. *(F-016 proved this is a live defect class, not a hypothetical.)*
- A story **SHALL NOT** cite a `docs/` path that does not exist (§10 category (c)).
- A story **SHALL NOT** relax a guarantee, a gate, or a security rule (§preamble).

## Scope

**In:** the machinery the gate chain depends on — the deterministic script layer and its
tests, the lane model, the skill-file format, the slicing map, the check registry, the
harness contract, the absent mandatory-read docs, and the environment the whole thing runs
on.

**Out (deliberately):** building the eleven agent skills themselves (that is the next
epic, and it *blocks on* F-PREP-06/07/08); Phase 0 on the engine; any application feature
work; Track B orchestration; buying hardware.

## Stories

Dependency-ordered. The first three are the operator's stated priorities.

| ID | Story | Lane / routing | Code-bearing? |
|---|---|---|---|
| **F-PREP-01** | Dual-boot Ubuntu LTS — build where the engine ships | Bastion | No (environment) |
| **F-PREP-02** | Test suite for the gate scripts | Forge → Crucible | **Yes — TDD** |
| **F-PREP-03** | Lane ownership for the engine's own artifacts | Keystone → Forge | Yes (manifest) |
| **F-PREP-04** | Completeness script — every referenced path exists | Forge → Crucible | **Yes — TDD** |
| **F-PREP-05** | Paper dry-run of one story, end to end | Marshal | No |
| **F-PREP-06** | Skill-file format specification | Keystone | No |
| **F-PREP-07** | `CLAUDE.md` slicing map | Keystone | No |
| **F-PREP-08** | Check registry + competence taxonomy | Crucible → Sentinel | Yes (data file) |
| **F-PREP-09** | Harness contract specification | Keystone | No |
| **F-PREP-10** | Close the mandatory-read gaps | Bastion / Sentinel / Codex | No |
| **F-PREP-11** | Falsifiability review — can every gate FAIL? | Crucible | No |
| **F-PREP-12** | Instantiate the gate log; run the two-context flow once | Sentinel → Marshal | No |

**Critical path:** F-PREP-01 → 02 → 04 (the deterministic layer, on the target platform),
in parallel with 06 → 07 → 08 → 09 (the specification layer). F-PREP-12 closes the epic and
cannot start until every other story is done.

## Cohesion criteria (§3.5)

> **Lane honesty:** these belong to **Atlas**, which does not exist yet (§0). Charter has
> drafted them so the epic is closeable; they are **not ratified** and Atlas must own them
> once built. Self-ratification by an agent is a protocol violation, as self-approval is.

At epic close, `COHERENT` requires **all** of:

1. Every gate named in `CLAUDE.md` §3 either runs, or is recorded in §0 as not-yet-built
   with the human-run fallback named. No gate is silently absent.
2. Every check in the registry (F-PREP-08) is assigned to script, model, or human — and
   **no check is assigned to the model that a script could decide** (IE-3).
3. Every gate in the §3.4 table has a demonstrated FAIL, not an argued one (IE-2).
4. The full deterministic layer produces identical verdicts on Linux and Windows (IE-5).
5. No `docs/` path is cited anywhere in the repo that does not exist (F-PREP-04 exit 0).
6. No story in the epic violated a SHALL NOT above.

`DRIFT` blocks epic close and returns to correct-course.

## Definition of done for the epic

The two-context workflow runs end to end on one real story: dispatch → build context →
`NEXT_PROMPT_GATES.md` → a cold gate context that sees only the story and the diff → both
gates → manual review → human approval → an appended gate-log row → the next handoff.

> **This is also a governance trigger.** On delivery of that flowing two-context workflow,
> the operator's standing rule engages: **no edits to settings config or governance docs
> without express per-edit permission.** Record it in the epic retro so the next session
> inherits it.

## Honest limits

- This epic makes the gates *executable and falsifiable*. It does **not** make them
  *strong*. A local model can pass every mechanical check and still reason worse than the
  model these checks were written against (§5.1, portable ≠ equivalent).
- Nothing here is an ATO or authorization to operate (§9).
- The three Phase-0-style self-checks used inside this epic are structured self-checks,
  not proof.
