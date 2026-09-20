# Distribution, Ownership and Upgrade — Behavioral Specification

**Version:** 1.1 · drafted 2026-09-20, hardened after gap analysis
**Part of:** Engine Specification Package
**Status:** specification only — implementation-independent
**Copyright:** © 2026 Casey Houle. All rights reserved. Confidential — not for distribution.

---

## 0. Scope, and why this is the spec that decides whether the others survive

Companion specs 01–05 describe a harness that works *in one repository at one moment*. This document
describes what happens when the harness is used by more than one project, and when it changes after
a project has adopted it.

That is the axis on which assurance tooling actually dies. The checks do not stop working; they stop
being *present*. A project copies the harness, edits a check to unblock a release, and three months
later that project is passing gates that no longer test anything — while the engine's authors believe
every project runs the same checks, because the engine's copy is untouched.

So the requirement is not "distribute the harness". It is: **make the set of checks a project runs
knowable and non-negotiable, while leaving the project genuinely free where it must be free.** Those
two goals conflict on almost every file, and the resolution is the ownership model in §2.

---

## 1. Premises

**REQ-1.1** The harness MUST exist as a distributable unit separate from any project that uses it.

**REQ-1.2** A project MUST be able to state which version of the harness it carries, from the
project's own tree, with no network access.

**Rationale.** During an assessment the question "which version of your checks produced this record"
must be answerable from the artifacts in hand. A version derivable only from a remote is not
available in the room where it is asked.

**REQ-1.3** The harness MUST be adoptable by an existing project, not only by a new one.

**Rationale.** Every project that needs assurance tooling already exists. A harness that only works
from a clean start is a harness for projects that do not need it yet.

**REQ-1.4** Update MUST be a deliberate operator action, never automatic.

**Rationale.** An automatic update changes the definition of passing, silently, between two runs of
the same command. Every gate record produced across that boundary becomes ambiguous.

---

## 2. The ownership model

This is the core of the document. Every file the harness places in a project MUST belong to exactly
one of four classes, and the class MUST be declared in the harness, not inferred from the file's
location or contents.

**REQ-2.1** The four classes and their update behavior:

| Class | On update | For |
|---|---|---|
| **Engine-owned** | Overwritten unconditionally | Checks, scripts, the rulebook, agent definitions, the self-test suite |
| **Seed-if-absent** | Written only when missing; never touched again | Project configuration, project instruction file, document templates |
| **Engine-reference** | Written beside the project's copy under a distinguishing suffix | Documents the project must own but the engine must keep a current exemplar of |
| **Project-owned** | Never written | Everything the project authors: plans, tickets, records, source |

**REQ-2.2** The class assignment MUST be a single enumerated list in the harness source, readable by
a human in one screen per class.

**Rationale.** The list is the contract. If a reader must trace conditionals to learn whether their
file will be overwritten, they will guess, and they will guess wrong at the worst time.

**REQ-2.3** Project-owned paths MUST be enumerated too, even though the update performs no action on
them.

**Rationale.** An unlisted path is indistinguishable from an oversight. Enumerating them turns "this
is yours" into a statement someone wrote deliberately, and makes a future misclassification visible
as a diff against that list.

### 2.1 Engine-owned

**REQ-2.1.1** Engine-owned files MUST be overwritten on every update without prompting and without
merging.

**REQ-2.1.2** Engine-owned files MUST carry a machine-readable marker declaring that local edits are
discarded.

**REQ-2.1.3** The harness MUST NOT provide a supported way to exempt an individual engine-owned file
from overwrite.

**Rationale, and this is the requirement most likely to be softened.** An exemption mechanism is
requested within days of adoption, always for a defensible reason, and it converts the guarantee
"every project runs these checks" into "every project runs these checks except where it doesn't,
recorded somewhere nobody reads at gate time." If a project genuinely needs a check to behave
differently, the check is wrong for everyone and belongs in the harness, parameterized by
configuration (companion spec 01, §2). That path is slower on purpose.

**REQ-2.1.4** Where an update would overwrite an engine-owned file whose content has diverged
locally, the prior content MUST be preserved beside it under a distinguishing suffix, and the
divergence MUST be reported in the update's summary.

**Rationale.** The overwrite is non-negotiable; losing someone's work silently is not. The backup
costs nothing and converts an angry discovery into a diff. The *report* matters more than the
backup — an operator who is not told will not look.

### 2.2 Seed-if-absent

**REQ-2.2.1** Seed-if-absent files MUST be written only when no file exists at the target path.

**REQ-2.2.2** An existing file at the target path MUST be left byte-identical, with no merge attempt.

**REQ-2.2.3** The update summary MUST distinguish *seeded now* from *already present*.

**Rationale.** "Already present" is the state in which a project is running an old template it has
never revisited. Naming it in the summary is the only prompt the operator will ever get.

### 2.3 Engine-reference

**REQ-2.3.1** Where a document must be owned and edited by the project, but the engine must be able
to ship an updated exemplar, the engine copy MUST be written beside the project's copy under a
suffix that makes it non-authoritative on sight.

**REQ-2.3.2** The engine-reference copy MUST NOT be read by any check.

**Rationale.** This class exists for exactly one situation: a document whose *structure* is the
engine's and whose *content* is the project's. Overwriting destroys the project's content; seeding
once leaves the structure frozen at adoption. Writing both, with the engine's copy plainly marked as
a reference, lets a human diff them and decide. It is the only class that requires human judgment,
so it MUST be kept small — if this class grows past a handful of files, the split between structure
and content is in the wrong place.

### 2.4 Project-owned

**REQ-2.4.1** The update MUST NOT create, modify, or delete a project-owned path under any
circumstance, including cleanup of paths it believes are obsolete.

---

## 3. Agent definitions are a distribution problem, not a documentation problem

Companion spec 03 (§1) establishes that an agent definition cannot delegate its rules to an imported
file: it must carry its full instructions inline. That has a direct and initially counter-intuitive
consequence for distribution.

**REQ-3.1** Agent definitions MUST be engine-owned and overwritten whole.

**Rationale.** Because the rules cannot be factored out into a shared imported file, every rule lives
inside each definition. A definition a project has edited is therefore not "a definition with a local
tweak" — it is a *different reviewer*, potentially missing an entire class of checks, and nothing in
the file's appearance says so.

**REQ-3.2** The harness MUST track which agent definitions it placed, so that a definition removed
from the harness is removed from the project on the next update.

**Rationale, and the failure this prevents.** Without tracking, a retired reviewer definition lives
on in every project that ever received it, is still invoked by name, and still renders a verdict
using rules the engine has abandoned. This is worse than a stale check, because the output is a
*judgment* and it looks current.

**REQ-3.3** The tracking record MUST be written by the update itself and MUST live beside the
definitions.

**REQ-3.4** A definition present in the project but not in the tracking record MUST be left alone.

**Rationale.** That is a project's own additional reviewer. The engine removes what the engine
placed; nothing more. The distinction between "engine-placed and now retired" and "project-added"
is exactly what the tracking record exists to make.

**REQ-3.5** Entries in the tracking record MUST be validated as simple filenames before use, and any
entry containing a path separator or a directory traversal component MUST be ignored.

**Rationale.** The record is a file the update reads and then *deletes based on*. An untrusted or
corrupted entry becomes an arbitrary deletion. This is cheap to guard and unrecoverable to get wrong.

---

## 4. The instruction-file split

Companion spec 03 (§1) establishes that project instructions resolve exactly one level of import
from the top-level instruction file, and that this shapes how rules can be organized.

**REQ-4.1** The engine's rules MUST live in an engine-owned file, imported by the project's
instruction file.

**REQ-4.2** The project's instruction file MUST be seed-if-absent, and MUST contain the import plus
the project's own rules.

**Rationale.** This is the only arrangement that satisfies all three constraints simultaneously: the
engine's rules update on sync; the project's rules survive; and both arrive in the agent's context,
which requires the import to sit in the file that is actually read.

**REQ-4.3** The import MUST be by a stable path the engine controls, so that reorganizing the
engine's rule documents does not require every project to edit its instruction file.

**REQ-4.4** The instruction file MUST state which of the two files wins on conflict.

**REQ-4.5** That statement MUST NOT be relied upon as a control.

**Rationale, established by direct test and worth restating here because distribution is where it
bites.** Both files reach the agent with identical framing and equal weight. The precedence
statement has persuasive force and no enforcement behind it; reverse the wording in the two files
and the outcome reverses. Therefore a rule whose violation matters MUST also be enforced by a check
that runs outside the agent's judgment (companion spec 01, §10). The written precedence is for
resolving honest ambiguity, not for defending against a project file that contradicts the engine.

---

## 5. Version identity

**REQ-5.1** Every update MUST record, in the project tree, the harness version applied and the date.

**REQ-5.2** The version MUST be a content-derived or explicitly tagged identifier, not a
human-maintained number in a file that can drift from what was actually copied.

**REQ-5.3** Gate records (companion spec 02) MUST be able to reference the harness version in force
when they were produced.

**Rationale.** "This gate passed" means nothing without "under these checks". Linking the record to a
version makes a past verdict re-derivable; without it, an old record is an assertion.

**REQ-5.4** The harness MUST provide a check that reports whether the project's copy of every
engine-owned file matches the recorded version, and MUST report any divergence.

**Rationale.** This is the mechanism that makes §2.1.3 real. Without a divergence check, the
overwrite guarantee holds only for projects that actually run the update — which is to say, it holds
where it is least needed.

**REQ-5.5** The divergence check MUST be part of the routine check command, not a separate
maintenance tool.

---

## 6. Upgrade behavior

**REQ-6.1** The update MUST support a mode that reports every action it would take and changes
nothing.

**REQ-6.2** The summary MUST be grouped by class and MUST state counts per outcome: overwritten,
seeded, already present, reference written, diverged, removed.

**REQ-6.3** Divergences and removals MUST be listed individually, not only counted.

**Rationale.** These are the two outcomes that destroy or delete. A count is enough for the routine
cases; the destructive ones need names.

**REQ-6.4** The update MUST be idempotent: running it twice with no intervening change MUST produce
the same tree and a summary showing no divergences.

**REQ-6.5** The update MUST NOT require the project's working tree to be clean, and MUST NOT perform
any version-control action itself.

**Rationale.** Committing on the operator's behalf makes the update's effects hard to inspect before
they are recorded. The operator reviews the diff and commits. The update writes files; that is all.

**REQ-6.6** Where an update changes the *meaning* of a check — a new requirement, a tightened
threshold — the harness SHOULD ship a note naming what will newly fail.

**Rationale.** An update that silently turns a project's gates red is indistinguishable from a
regression in the project, and will be debugged as one.

---

## 7. Adopting into an existing project

**REQ-7.1** Adoption MUST NOT require the project to already satisfy the harness's checks.

**REQ-7.2** Adoption MUST produce an inventory of code that predates the harness and has therefore
never passed a gate.

**REQ-7.3** Each entry in that inventory MUST be dispositioned explicitly — reviewed, accepted with
a reason, or scheduled — and the disposition MUST be a durable record (companion spec 02).

**Rationale.** The alternative is that pre-existing code is implicitly blessed by the first passing
gate, which reviewed none of it. An assessor asking "what has this tool actually examined" deserves
a real answer, and "everything since date D, with these N files explicitly accepted unreviewed" is a
far stronger answer than an implied "everything".

**REQ-7.4** Adoption MUST NOT modify project source code.

---

## 8. Provenance and clean-room reimplementation

This section exists because this package is itself a distribution artifact, and because a
specification-driven reimplementation has a provenance story that must hold up if anyone asks.

**REQ-8.1** An implementation built from this package MUST be written from the specified behavior,
not transcribed from any reference implementation.

**REQ-8.2** Where this package names a concrete artifact of the reference implementation — a
filename, a flag spelling, a command name — that naming is **illustrative**. An implementation MUST
be free to choose differently, and the specification MUST remain satisfiable if it does.

**Rationale.** Every requirement in these six documents is stated in terms of behavior and the
failure it prevents. That is deliberate and it is the property that makes the package usable as a
build input rather than as documentation of one codebase. Where a document slips into naming a
mechanism, treat the mechanism as an example and the behavior as the requirement.

**REQ-8.3** An implementation SHOULD record, per requirement, how it is satisfied — or that it is
not.

**Rationale.** This is the same argument as the control manifest (companion spec 01, §7) applied to
the harness itself: a requirement nobody can point to an implementation of is a requirement nobody
implemented. A short requirement-to-implementation table, kept current, makes the gap visible while
it is still cheap.

**REQ-8.4** Third-party components used by an implementation MUST be recorded with their licenses,
and that record MUST be produced by tooling rather than maintained by hand.

**REQ-8.4a** That record MUST be **evaluated against a declared license policy**, not merely
generated. Rationale: a record nothing evaluates is an inventory. License constraints are frequently
a delivery requirement rather than a preference, and the point at which one is discovered to have
been violated is usually the point at which it is most expensive to remedy. The check belongs in the
mechanical set (companion spec 01, REQ-10.5).

**REQ-8.5** An implementation MUST be able to state, for each vendored data set (catalogues,
baselines), its source and the terms under which it is redistributed — or that it is not
redistributed and must be supplied by the operator (companion spec 04, §3.9).

---

## 9. Non-requirements

- **No per-project exemption from engine-owned files.** REQ-2.1.3. A needed variation is a
  configuration parameter or a change to the harness.
- **No merge on update.** Overwrite or leave alone. A three-way merge of a check file produces a
  check nobody reviewed.
- **No automatic update.** REQ-1.4.
- **No network requirement for version identity.** REQ-1.2.
- **No deletion of anything the harness did not place.** REQ-2.4.1, REQ-3.4.
- **No version-control side effects from the update.** REQ-6.5.
- **No thin agent definitions.** REQ-3.1, and companion spec 03 §1 for why this is not a style
  preference.

---

## 10. Suggested build order

| Stage | Build | Why here |
|---|---|---|
| 1 | The four-class enumeration, with project-owned listed | Everything else is mechanics on top of this |
| 2 | Engine-owned overwrite, with divergence backup and report | The guarantee the whole model exists to provide |
| 3 | Seed-if-absent, with seeded / already-present in the summary | Makes first adoption possible |
| 4 | Version recording and the divergence check (§5) | Without this, stage 2's guarantee is unverified |
| 5 | Agent tracking record and stale removal (§3) | Needs stage 1's list and stage 2's overwrite |
| 6 | Report-only mode and the grouped summary (§6) | Trivial once the actions are classified |
| 7 | Engine-reference class (§2.3) | Last; it is the smallest class and needs the rest to be settled |
| 8 | Existing-project adoption and the never-reviewed inventory (§7) | Independent; build when a second project appears |

**A note on stage 4.** It is tempting to defer the divergence check, because immediately after an
update nothing has diverged. That is precisely the window in which it is cheap to build and the only
window in which it can be tested against a known-good tree. Deferred, it becomes a report of
accumulated unexplained differences that nobody can adjudicate.
