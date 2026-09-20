# Harness Integration and Orchestration — Behavioral Specification

**Version:** 1.1 · drafted 2026-09-20, hardened after gap analysis
**Part of:** Engine Specification Package
**Status:** specification only — implementation-independent
**Copyright:** © 2026 Casey Houle. All rights reserved. Confidential — not for distribution.

---

## 0. Scope

This document specifies the **connective tissue**: how rules reach an AI agent's working context,
how the review isolation is actually achieved rather than merely instructed, what the handoff between
contexts may and may not carry, and the state machine that tracks work through the lifecycle.

It is the least obvious of the specs and the one most likely to be reinvented badly, because every
requirement here looks like a matter of taste until you know what happens without it.

**Out of scope:** the content of the checks (companion spec 01), the records they produce (02), and
the generic agent-skill routing that any harness provides.

---

## 1. How rules reach the agent

### 1.1 The loading mechanism

**REQ-1.1.1** The harness MUST have a well-known file that the agent runtime loads automatically
into every session's context, without the agent choosing to read it.

**Rationale.** A rule the agent must remember to read is a rule that applies only when the agent
remembers. Automatic loading is the difference between a rule and a suggestion.

**REQ-1.1.2** That file MUST be able to pull in additional files by reference.

**REQ-1.1.3** The implementation MUST establish, by direct test, **how many levels of reference the
runtime actually resolves**, and MUST NOT exceed that depth.

**Rationale — observed, and non-obvious.** In the reference runtime, references resolve exactly
**one level**. A file pulled in by the root file loads. A file that *that* file references does not —
the reference line sits in context as inert text, and nothing reports an error. A rule placed two
levels down is silently absent from every session. The depth is a property of the runtime, not of
the design, so it must be measured rather than assumed.

**REQ-1.1.4** Where content must live in an included file, that file MUST NOT itself use references.

### 1.2 Precedence is a convention, not a mechanism

**REQ-1.2.1** Where the harness's rules and a project's own rules can conflict, the precedence
ordering MUST be stated in the rules.

**REQ-1.2.2** That statement MUST be accompanied by an explicit note that it carries **no
enforcement**, and that no control whose failure matters may rest on it alone.

**Rationale — established by adversarial test.** An experiment placed a harness rulebook and a
project rulebook in deliberate contradiction, with a distinguishing token in each. Both arrived in
the session's context with **identical framing and equal weight** — neither was marked as
authoritative by the runtime. The harness rules were followed, but only because they were phrased as
a general ordering principle while the project file merely asserted an outcome. Reversing the
phrasing reverses the result.

The practical conclusion: precedence text has *persuasive* force and no mechanical force. The rules
that actually held under a hostile project file held because they were **also** enforced outside the
repository — by branch protection, by a pre-execution hook, by the runtime's own constraints.

**REQ-1.2.3** Every non-negotiable rule MUST therefore have an enforcement point outside the
repository's text. A rule that exists only as prose is advisory regardless of how it is worded.

### 1.3 Reviewer definitions cannot be thin

**REQ-1.3.1** Where the runtime supports separate reviewer/agent definitions, those definitions MUST
be **self-contained**. A definition MUST NOT rely on pulling in shared procedure by reference.

**Rationale — observed.** In the reference runtime, reference lines inside an agent definition are
**not** resolved when that agent runs. A canary agent whose definition referenced its own procedure
file reported that no procedure had reached it. Meanwhile the project-level rules *did* reach the
same agent, because those load by a different path.

So: shared governance can live in the project rules and will reach an agent. Anything specific to
the agent must be inlined in its own definition. A "thin router" agent definition is an agent with
no instructions.

**REQ-1.3.2** Because definitions must be whole, keeping them current across projects is a
distribution problem, not a composition problem. See spec 06.

### 1.4 Rule-set integrity

**REQ-1.4.1** Where a rule or format is stated in more than one file — for example a verdict format
appearing in both a reviewer definition and a reference document — an automated check MUST assert
the copies agree.

**REQ-1.4.2** That check MUST itself follow the reference chain (REQ-1.1.2), and MUST **fail** when
it finds nothing to compare rather than passing vacuously.

**Rationale — observed in the check itself.** The reference implementation's consistency check read
its input from the root rules file. When the rules were restructured and the relevant section moved
into an included file, the check found nothing, extracted an empty set, iterated zero times, and
passed. A check that cannot fail is the exact defect the check existed to catch.

---

## 2. Context isolation — the two-window protocol

### 2.1 What is being prevented

The reasoning that justified a shortcut during construction is the same reasoning that will excuse
it during review. This is not a discipline failure. A reviewer who has the construction context
available *will* use it, and will find the shortcut reasonable, because it was reasonable given the
constraints they remember.

### 2.2 Requirements

**REQ-2.2.1** The review MUST execute in a context that has never contained the construction
conversation.

**REQ-2.2.2** The mechanism achieving this MUST be structural — a genuinely separate session — not
an instruction to disregard prior context.

**Rationale.** "Do not consider the earlier discussion" is unverifiable and, in a system with a
shared context window, meaningless.

**REQ-2.2.3** The transition between contexts MUST occur through a **generated artifact** whose
entire content is derivable from version control and project configuration.

**REQ-2.2.4** The handoff artifact MUST NOT contain any free-text field.

**Rationale, and this is the whole design in one line.** If build rationalization cannot be typed
into the handoff, it cannot cross the wall. A single "notes for the reviewer" field defeats the
entire protocol, and it will be added by a well-meaning implementer within a month unless the
prohibition is explicit.

### 2.3 Handoff contract

**REQ-2.3.1** The handoff MUST contain exactly:

| Element | Source |
|---|---|
| Range: base and head commit identifiers | Version control |
| Merge base, where it differs from base | Version control |
| Commit count and changed-file count | Version control |
| Unit-of-work identifier | Branch name |
| Work item identifiers in the range | Commit messages |
| Project shape (all configuration axes) | Configuration file |
| Enumerated list of documents to read first | Fixed |
| Paths to the work items' own files | Derived from the above |
| A single instruction naming the gates to run | Fixed |

**REQ-2.3.2** The handoff MUST state explicitly that the construction conversation is not to be read.

Rationale: belt and suspenders. The structural separation is the control; the instruction closes the
case where a reviewer has incidental access.

**REQ-2.3.3** The handoff generator MUST refuse to produce output when its preconditions are unmet
(companion spec 01, §3.3).

**REQ-2.3.4** A checkpoint mode SHOULD exist that produces the same handoff labelled as advisory —
findings only, no merge implication.

### 2.4 The reviewer reads from source

**REQ-2.4.1** The reviewer MUST obtain the change from version control itself, not from a diff
supplied to it.

**Rationale.** A supplied diff can be filtered, truncated, or summarized — by tooling or by
accident. Reading from source makes the artifact under review the same artifact that will merge.

---

## 3. Lifecycle state machine

### 3.1 Two nested units

**REQ-3.1.1** The harness MUST track two levels: a **unit of work** (a branch, one merge, one gate
series) and the **items** within it.

**REQ-3.1.2** Unit-of-work states MUST include at minimum: planned, building, in review, merged.

**REQ-3.1.3** Item states MUST include at minimum: open, claimed, in review, done.

**REQ-3.1.4** State MUST be stored in the item and unit files themselves, in a structured header —
not in a separate tracking system.

**Rationale.** State in a separate system requires synchronization, and synchronization fails
silently. State in the file travels with the branch, diffs in version control, and survives the
tooling.

### 3.2 Dependencies

**REQ-3.2.1** Items MUST be able to declare dependencies on other items.

**REQ-3.2.2** Dependencies MUST record only true ordering constraints, not preference.

**REQ-3.2.3** A dependency in the *in review* state MUST count as satisfied.

**Rationale.** Its work is on the branch. Treating it as blocking stalls the whole unit on a
review that is already underway, which teaches people to lie about dependencies.

### 3.3 Definition of done, per item

**REQ-3.3.1** Every item MUST carry a single sentence stating an **observable outcome** that
constitutes completion.

**REQ-3.3.2** That sentence MUST be phrased as something a person could check by hand or with one
test — not as "implement X."

**REQ-3.3.3** That sentence is the input to the first failing test written for the item. Its quality
is therefore load-bearing, not documentation.

### 3.4 Orientation

**REQ-3.4.1** A command MUST exist that reports current position and exactly one next action.

**REQ-3.4.2** It MUST derive its answer from version control, the item files, and CI status — never
from a handoff or status file written by a previous session.

**Rationale.** A handoff file is stale the moment someone commits. Version control, item files and CI
are never stale, because they *are* the state.

**REQ-3.4.3** It MUST compare against the **remote** protected branch, not a local copy.

**Rationale — observed.** In this workflow the developer branches from the remote and a human merges
the pull request, so the local copy of the protected branch is never checked out and drifts silently.
On a real project it was six months behind, and the orientation command cheerfully reported the
branch as hundreds of commits ahead. An orientation tool that reports a stale number is worse than
one that reports nothing.

**REQ-3.4.4** It MUST always exit successfully. It is a reporter, not a check.

**REQ-3.4.5** Absence of CI integration MUST be reported as "not configured," never as an error.

### 3.5 Plan documents are edited only in planning contexts

**REQ-3.5.1** Design documents MUST be editable only during explicit planning sessions, never during
construction.

**REQ-3.5.2** A decision that the plan did not anticipate MUST stop construction and escalate. If it
changes the plan, it requires a planning session, a recorded decision, and re-cut work items.

**Rationale.** Otherwise the plan is rewritten to match whatever was built, and the comparison
between plan and reality — which is the only signal that a design assumption failed — is destroyed
by the same act that should have raised it.

**REQ-3.5.3** Divergence between generated truth and the plan MUST be surfaced as a human decision.
It MUST NOT be silently reconciled in either direction.

---

## 4. Agent conduct constraints

These are constraints on the agent itself, enforced where possible outside the prose.

**REQ-4.1** The agent MUST NOT merge, approve, or override a verdict. Enforced by platform branch
protection (companion spec 01, §3.5).

**REQ-4.2** A pre-execution hook SHOULD refuse the specific dangerous commands before they reach the
network: push to protected branch, merge while on protected branch, remote merge.

**REQ-4.3** The hook MUST block **only** those commands. A hook that blocks broadly gets disabled.

**REQ-4.4** The agent MUST NOT read or reproduce environment-specific secrets material — deployment
value files, infrastructure variable files, or platform-produced vulnerability artifacts.

**REQ-4.5** The agent MUST NOT attribute itself in anything that lands in a repository — commit
messages, change descriptions, code comments, or generated documents.

**Rationale.** The human is accountable for the work. Attribution in the record makes it ambiguous
who is, and that ambiguity surfaces at exactly the wrong moment.

**REQ-4.6** A frozen surface MUST be definable — files the agent may propose changes to on a branch
but never write directly. Typically deployment and infrastructure definitions owned by another team.

**REQ-4.7** The agent MUST report the frozen surface's state at every gate: filenames, counts,
presence of expected keys — never values.

---

## 5. Session-context hygiene

**REQ-5.1** Rules loaded into context MUST be short enough to remain effective. A rule set that
exceeds the attention available is a rule set with arbitrary gaps.

**REQ-5.2** Long reference material MUST live in files read on demand, with the always-loaded rules
acting as navigation.

**REQ-5.3** The always-loaded rules SHOULD state only: non-negotiables, the map of where things live,
and the lifecycle. Everything else is a pointer.

**REQ-5.4** Where content is moved out of the always-loaded file to satisfy REQ-5.1, REQ-1.1.3 applies
— it must be reachable within the runtime's actual resolution depth.

---

## 6. Non-requirements

- **No agent-to-agent handoff of construction context.** The wall is the point.
- **No free-text handoff field.** REQ-2.2.4.
- **No separate work-tracking system.** State lives in files under version control.
- **No reliance on precedence prose for any control that matters.** REQ-1.2.3.
- **No thin agent definitions.** REQ-1.3.1.

---

## 7. Verification checklist for an implementation

An implementation of this spec should be able to demonstrate each of these by test:

| # | Demonstration |
|---|---|
| 1 | A rule placed in the always-loaded file reaches a fresh session |
| 2 | A rule placed one reference-level down reaches a fresh session |
| 3 | A rule placed two reference-levels down **does not** — and this is documented, not assumed |
| 4 | A reference inside an agent definition does not resolve; the agent's own procedure must be inlined |
| 5 | Project-level rules **do** reach a dispatched agent |
| 6 | The handoff artifact contains no field a human can type into |
| 7 | The handoff refuses to generate when preconditions are unmet |
| 8 | The consistency check fails, rather than passing, when its input is empty |
| 9 | The orientation command compares against the remote protected branch |
| 10 | The pre-execution hook blocks exactly three commands and nothing else |
