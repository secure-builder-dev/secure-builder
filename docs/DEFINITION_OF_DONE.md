# DEFINITION_OF_DONE.md — When a story is "done"

> **Lane:** Core governance. **Source of record:** `SECURE_BUILDER_PRD.md` §2, §4, §8.1.
> **Operationalized by:** `CLAUDE.md` §3, §7.
>
> "Done" in Secure Builder is not "the code works." It is "the code passed the full gate
> chain and a human approved it, with the evidence recorded." This file states that bar
> exactly.

---

## 1. The bar

A story is **done** only when **all four** of the following are true, **in order**, with
no step skipped, reordered, or auto-approved:

1. **Quality gate PASS** (Crucible — `QUALITY_GATE.md`).
2. **Security gate PASS** (Sentinel — `CONTROLS-MAPPING.md` / PRD §5.4).
3. **Manual security review CLEAR** (human + AI assistant — `CLAUDE.md` §4.4).
4. **Explicit human approval** — the human types "approved." This is the **hard stop**
   and the only thing that unlocks promotion.

> Gates 1–3 run in a separate **gate context (CW2)** that sees only the story and the
> diff — blind to the builder's reasoning (`CLAUDE.md` §3). The build context (CW1) makes
> the local TDD commits and hands off to the gate context; it never gates its own work.

> **No self-approval (Guarantee #1).** No AI agent approves AI-produced work. A story is
> never "done" on an AI's say-so, no matter how correct the work appears.

If any gate returns FAIL or the manual review returns findings, the story returns to the
implementer with remediation notes and is **fully re-gated** — not patched and waved
through.

---

## 2. Per-story evidence that must exist before "done"

- **TDD two-commit sequence** in `git log` (`[S-XXX/tests]` before `[S-XXX/impl]`) for
  any code-bearing story (Guarantee #3). Non-code stories — docs, ADRs, pipeline config —
  are exempt by nature.
- **`### TDD Red-Phase Evidence`** section in the story file (failing-test output).
- **`## Gate Results`** section in the story file carrying the verdict tuple
  (Crucible / Sentinel / Manual / Human).
- **Negative authorization tests** for every endpoint touched (401 / 403 / IDOR / 400 /
  conflict — Guarantee #8).
- **Security checks mapped to controls** — each Sentinel check carries a control ID from
  `CONTROLS-MAPPING.md`, resolving to verbatim text in `docs/security/corpus/`
  (Guarantee #4). A check whose source is not vendored says so; it is never filled from
  memory.
- **Intent element recorded** in the story header — the matrix element this story traces
  to (Phase 0, PRD §15.2). A story with none is rogue work.
- **Instruction-artifact portability** (F-prefix stories that add or change an instruction
  artifact — `CLAUDE.md`, an agent skill file, the manifest, a gate doc, a handoff
  template): the artifact declares its token budget and obeys the CLAUDE.md §5.1 authoring
  rules in force (1–6) — sliceable, self-contained slices, data over prose, imperative gate
  checklists, no runtime-specific syntax. These artifacts are prompts that must run on the
  Track-C local models, not documents (PRD §10.2).
- For **security-sensitive** stories (auth, RBAC, new endpoints, data-boundary changes):
  the human has **named the endpoints touched** and stated, in their own words, *who can
  call each one and what stops everyone else.* A bare approval is not accepted.

---

## 3. Obligations triggered by "done" (the commit + handoff protocol)

On human approval, before the story is **promoted** (closed out / pushed / merged)
(`CLAUDE.md` §7):

1. **Confirm the TDD two-commit sequence is present** in `git log` — `[S-XXX/tests]` then
   `[S-XXX/impl]` (or `[F-XXX/...]` for framework/engine work), made as local working
   commits in the build context. **No AI co-author or attribution trailer on any commit**
   (standing rule, `CLAUDE.md` §7.1).
2. **Sentinel appends to the gate log** (`_bmad-output/gate-log.md`) — Quick Ledger row,
   Detailed Ledger row, a `DETECTED` row for any new finding, and the terminal
   `REMEDIATED` / `ACCEPTED` row for any finding that closed. Sentinel owns this artifact
   (`CLAUDE.md` §2, §7.2). **Append-only** — never edit or delete a prior row
   (Guarantee #6).
3. **Marshal writes the handoff prompt** — `NEXT_PROMPT.md` (S-prefix) or
   `NEXT_PROMPT_FRAMEWORK.md` (F-prefix), fully self-contained for a fresh session.

A story does **not** appear in the gate log until it has passed all four gates.
In-progress stories have no entries.

---

## 3.5 When an *epic* is done (the cohesion bar)

Story-level "done" does not close an epic. An epic is **done** only when, in addition to
every story in it being done above:

- **Atlas's epic-boundary cohesion gate returns `COHERENT`** (`CLAUDE.md` §3.5, PRD §4.5)
  — the assembled, gate-passed epic still satisfies the intent elements the Phase-0 matrix
  assigned it, no acceptance criterion was met in a way that violates a matrix `SHALL
  NOT`, and every intent element the epic owns is covered by shipped work.
- The verdict is **appended to the gate log's Epic Cohesion Ledger**
  (`GATE_LOG_SCHEMA.md` §1.4).

`DRIFT` **blocks epic close** and returns to correct-course — re-scope, add a story, or
amend the intent with a recorded ADR — then re-run the gate. Like every gate here it is a
structured self-check with a human confirming, not proof (`CLAUDE.md` §9).

> **Upstream of all of this:** no story runs at all until **Phase 0** has produced, and a
> human has **ratified**, the document matrix, the intent-traceable backlog, and the
> epic cohesion criteria (`CLAUDE.md` §2.3, PRD §15). Self-ratification by an agent is a
> protocol violation, exactly as self-approval is.

---

## 4. What "done" does NOT mean (honesty clause)

- **Not authorized to operate.** Done here means release-ready *as far as a pre-flight
  development tool can make it* — not an ATO. The downstream platform team is the sole
  approval authority and re-runs its own checks.
- **Not separation of duties.** The four gates are a structured self-check by a single
  operator, not separation of duties (`CLAUDE.md` §9). "Approved" evidences one
  developer's structured self-check at the §4.4 depth — not senior security sign-off
  unless a qualified senior reviewer actually performed it.
- **Not proof an automated gate ran.** While Crucible and Sentinel are Phase-2 builds, the
  gate verdicts are produced by a human running the checklist by hand. Evidence and
  briefings must say which it was.
