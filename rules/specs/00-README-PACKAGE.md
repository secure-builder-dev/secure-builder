# Engine Specification Package

**Version:** 1.1 · assembled 2026-09-20, hardened after gap analysis
**Contents:** six behavioral specifications (454 numbered requirements), a build strategy, the gap analysis that produced this revision, and a private strategy memo, and the provenance setup for the home build
**Status:** specification only — implementation-independent
**Purpose:** a complete, self-contained input for building an assurance harness from scratch, with
**Copyright:** © 2026 Casey Houle. All rights reserved. Confidential — not for distribution.
no access to any existing codebase.

---

## 1. What this package is

Six documents that specify, in behavioral terms, an AI-assisted development harness whose output is
**assurance**: a durable, defensible record that code was checked, by what, against what standard,
with what result, and what was decided about the findings.

Each requirement is numbered, carries the word MUST / SHOULD / MAY, and is followed by a rationale
that names the **specific failure it was written against**. That is the package's actual value. A
requirement list can be reconstructed by anyone in an afternoon; the rationale is what stops a
future reader — or a future model — from optimizing the requirement away because it looked
redundant. Where a rationale is marked *observed*, that failure happened.

**What this package is not:** documentation of any particular codebase, a port, a transcription, or
a set of files to copy. There is no source code in it. Concrete names that appear — a filename, a
flag, a command — are illustrative examples of a behavior, never the requirement itself
(spec 06, §8.2).

---

## 2. The documents

| # | Document | Lines | Reqs | Covers |
|---|---|---:|---:|---|
| 01 | **Security Layer** | 1247 | 158 | The checks themselves: scanning, composition inventory and artifact binding, the two gates, the control manifest and its completeness, standards citation, standing-state probes, mechanical checks, governance, failure semantics |
| 02 | **Gate Records and Evidence Artifacts** | 802 | 98 | What the harness *produces*: the gate log and its run attestation, findings register, governance changelog, scan artifacts, coverage inventory, generated truth, and how the set maps to an authorization package |
| 03 | **Harness Integration** | 317 | 49 | How rules reach the agent, the two-window isolation protocol, the lifecycle state machine, agent conduct constraints |
| 04 | **Offline and Air-Gapped Operation** | 432 | 61 | Three operating modes, transfer paths, platform-control substitutes, the honest degradation statement, and the two-instance topology for development across a domain boundary |
| 05 | **Self-Test Discipline** | 272 | 40 | How to prove a check actually discriminates: negative fixtures, mutation as acceptance, assertion precision, hermetic fixtures, the integration tier, the uninvoked-suite audit |
| 06 | **Distribution, Ownership and Upgrade** | 350 | 48 | The four ownership classes, whole-file agent replacement with stale removal, the instruction-file split, version identity, adoption into an existing project |
| 07 | **Build Strategy** | 544 | — | How to actually get it built: the v1.0 exit condition, the ledger, mutation receipts, the agent roster, the two-layer loop, enforcement outside the assistant's judgment |
| 08 | **Gap Analysis** | 427 | — | The five-pass analysis that produced v1.1, including the classified-environment research. Kept because the findings explain *why* several requirements are shaped the way they are |
| 09 | **Commercial Strategy and IP Position** | 235 | — | Private. Not a specification. What is copyable and what is not, four packaging options with tradeoffs. Do not distribute with the specs |
| 10 | **Provenance and Build Record** | 222 | — | Operational. Twenty minutes of setup — separate identity, signed commits, environment record, session log — so the independence of the home build is documented as it happens rather than reconstructed |

Read 01 → 06 in order once, before building anything. They cross-reference heavily and several
requirements in later documents only make sense against premises established in 01.

**09 is private.** It concerns ownership, data rights and commercial packaging. It is in this folder
because it belongs with the work, not because it travels with it. Remove it before the package goes
to anyone else.

**07 and 08 are different in kind.** Specs 01–06 are implementation-independent by design; 07 is
deliberately prescriptive about mechanism, because it describes an operating procedure rather than a
system. Read it after 01–06 and before writing any code. 08 is a findings document, not a
specification — its fixes are already folded into 01–07, and it is retained because the reasoning
behind a requirement is the thing that stops a future reader from optimizing the requirement away.

---

## 3. The four ideas the whole package rests on

If the requirements were lost and only this section survived, these would be enough to rebuild most
of it.

**3.1 A check that cannot fail is worse than no check.** It produces the appearance of coverage,
which is consumed as coverage, and nothing ever contradicts it. Most of the observed failures behind
these specs are of this shape: a scanner that exited zero because its container never started; a
consistency checker that found nothing to compare and passed; a test suite of fifty-eight cases that
no command invoked. Spec 05 exists entirely to find these; spec 01 §13 specifies the failure
semantics that prevent them.

**3.2 The reviewer must not have been in the room.** A reviewer who watched the code being built
inherits the rationalizations that produced it. The isolation is architectural, not procedural: the
handoff between building and reviewing must carry no free-text channel through which context can
cross. Spec 03 §2.

**3.3 A finding is not fixed until it cannot recur.** Every finding is sorted into one of exactly
two buckets — mechanical, which becomes an automated check, or judgment, which becomes a line on a
reviewer's checklist. A finding that is merely fixed will reappear. The count of findings per review
cycle should trend toward zero, and if it does not, the sorting is not happening. Spec 01 §1.4.

**3.4 A control is not proven by a passing test. It is proven by breaking it and watching the test
fail.** Applied to security controls this is the control manifest and its mutation run (spec 01 §7);
applied to the harness's own checks it is spec 05 §3. Same idea, two scopes, and it is the single
highest-value practice in the package.

---

**3.5 A record that nothing can contradict is not evidence.** This is 3.1 applied to artifacts
instead of checks, and it is the finding that most changed the package between v1.0 and v1.1. The
gate log is written by the agent whose verdict it records: a failing run that never gets a row is
invisible, because the evidence of the omission *is* the omission. The fix is structural rather than
procedural — a different component writes a started marker before any verdict exists to be
inconvenient, and a marker with no completed row is a checkable gap. Spec 02 §3.5.

**3.6 Say what the reviewer is.** The gates are automated. Contemporaneous, checklist-driven,
machine-generated evidence with a named human attestation on top is a *stronger* position than
evidence reconstructed later by people recalling what happened — and it is only available to a
package that discloses it up front. Discovered late, the same facts read as something that was being
kept quiet, and the doubt spreads to everything else in the bundle. Spec 02 §0 and §10.5.

---

## 4. Build order across all eight documents

Each document carries its own internal build order. This is the order **across** them. The ordering
is not arbitrary: each stage produces something the next stage needs, and the early stages are the
ones that are nearly impossible to retrofit.

| Stage | Build | From | Why here |
|---|---|---|---|
| 1 | Configuration model and mode declaration | 01 §2, 04 §1 | Every later component branches on these; retrofitting means auditing every component |
| 2 | Ownership classes and the update mechanism | 06 §2 | Decide what is overwritable before writing files that will need to be |
| 3 | Failure semantics — the honesty rules | 01 §13 | These are a *convention* every subsequent check must be written against |
| 4 | Self-test harness, with negative fixtures | 05 | Build the thing that proves checks work before building checks |
| 5 | Mechanical checks | 01 §10 | Cheapest real value; each one is small and independently useful |
| 6 | Record set: gate log, findings register, changelog, **run attestation** | 02 §3–5 | Must exist before the first gate, or the first gates leave no trace — and without the started marker the log cannot be contradicted |
| 7 | Control manifest, wiring verification, mutation | 01 §7 | The core assurance claim |
| 8 | The two gates and the isolation protocol | 01 §5–6, 03 §2 | Needs 5, 6 and 7 to have something to check and somewhere to record |
| 9 | Scan subsystem, **composition inventory and artifact binding** | 01 §4, §4.9 | Independently valuable; deliberately late because it is the most environment-dependent. The binding is what connects a scan verdict to the reviewed source |
| 9a | **Integration tier** | 05 §6.1 | The moment stage 9 exists, so its external paths are exercised somewhere before release |
| 10 | Standards citation and currency | 01 §8, 04 §3 | Needs the control manifest to cite *from* |
| 11 | Governance protocol | 01 §11 | Needs something worth protecting |
| 12 | Standing-state probes, **manifest completeness probe** | 01 §9, §7.5 | Needs a running system to observe; completeness needs §6.3's control-shape detection |
| 13 | Generated truth and drift detection | 02 §9 | Needs a codebase with accumulated documentation to drift from |
| 14 | Evidence package export, **traceability index, disclosure statement** | 02 §10 | Assembles what stages 6–12 produce; cannot precede them |
| 15 | **Two-instance topology**, if the project crosses a domain boundary | 04 §10 | Only if applicable — but if it is, it reshapes stages 6, 9 and 14, so decide before stage 6 |

**On stage 15.** It is last in the table and it is a decision you make first. If the project will be
developed on one network and deployed on another, the two-instance model changes which records are
authoritative and what an instance may claim about code it received rather than built. Retrofitting
that is a rework of the record set.

**The two stages people skip, and the cost.** Stage 3 gets skipped because it produces nothing
runnable — and then every check written before it has its own idea of what a failure means, and
unifying them later is a rewrite. Stage 4 gets skipped because a test harness with no checks to test
feels premature — and then the first twenty checks are never mutated, and some fraction of them have
never been able to fail.

---

## 5. Driving this with an AI assistant locally

**Document 07 is the full treatment** — the exit condition, the ledger, mutation receipts, the four
agent roles, the loop and its guards, and the enforcement that does not depend on the assistant
cooperating. What follows is the short version; where the two differ, 07 is the operational one.

**5.1 One stage per session.** Give the assistant the relevant document sections and the stage from
§4. Do not paste all six documents and ask for a plan; the result is a summary, and a summary of a
specification is a specification with the rationales removed.

**5.2 Demand the mutation, every time.** The acceptance criterion for any check is *not* "the tests
pass". It is: break the property, show the check failing, restore it, show the check passing. Ask
for the output of both. An assistant that reports tests passing without having run the negative case
has told you nothing (spec 05 §1).

**5.3 Watch for the four erosions.** These are the specific ways requirements get softened in
practice, all of them defensible in isolation:

| Erosion | Sounds like | Where it is forbidden |
|---|---|---|
| Skip instead of fail | "the scanner isn't available here, so we skip it" | 01 §4.2.3, 01 §13 |
| Silent fallback | "if the fetch fails we use the cached copy" | 04 §3.4 |
| Per-project exemption | "this one project needs the check relaxed" | 06 §2.1.3 |
| Vacuous pass | "nothing matched the pattern, so it passed" | 05 §7.2 |
| Unfalsifiable record | "the gate writes its own log row" | 02 §3.5 |
| Mutation that removes rather than alters | "I deleted the file and the check failed" | 07 §2.2 |

**5.4 Keep a requirement-to-implementation table** from the first stage (spec 06 §8.3). Each
requirement gets a pointer to what satisfies it, or an explicit *not implemented*. This is tedious
for a week and then it is the only thing that answers "did we actually build this".

**5.5 Build the honest-degradation statement early** (spec 04 §7). Asking "what does this component
guarantee, and under what conditions" while the component is being written takes a minute. Asking it
across a finished codebase is archaeology, and the answers are guesses.

**5.6 Do not let the assistant write the governance rules.** Spec 01 §11 specifies which artifacts
are constitutional — the instruction files, the reviewer definitions, anything that alters gate
behavior. These are human-authored and reviewed line by line. An assistant editing the rules that
constrain it is the one loop in this package that has no check on it, by construction.

---

## 6. What is deliberately absent

- **Source code.** By design (spec 06 §8.1).
- **A language, framework, or directory layout.** The specs are satisfiable in any of them, and the
  choice should follow the environment it must run in.
- **The plan-and-build workflow** — how work is decomposed into units, what a planning session
  produces, how tickets are cut. It is deliberately out of scope: it is a product-development
  process, it is the part most specific to a particular team, and none of the assurance requirements
  depend on it. Spec 03 §3 specifies only the *state machine* the assurance layer needs — that build
  precedes gate, that a gate runs on a defined range, that closure follows a human approval.
- **Any infrastructure, account, network or credential detail.** No such value appears anywhere in
  the package, and none should be added to it.
- **Coverage-percentage targets for the harness's own code.** Coverage measures execution, not
  discrimination (spec 05 §11).

---

## 7. Minimum useful subset

If the full build is too large to start, this subset delivers real assurance and is a coherent
stopping point rather than a half-built system:

1. Failure semantics (01 §13) — the convention.
2. Self-test discipline (05) — applied to everything below.
3. Four or five mechanical checks (01 §10) — the ones that match your actual risk.
4. The gate log and findings register (02 §3–4) — the record.
5. The control manifest with mutation (01 §7) — the claim.
6. One reviewer, run in isolation on a defined range (01 §6, 03 §2) — the judgment.
7. The started marker and its check (02 §3.5) — without it, item 4 is a record that cannot be wrong.
8. The disclosure statement (02 §10.5) — one generated page, and the thing that makes the rest
   credible rather than awkward.

That is a harness that can honestly say what it checked, prove its checks discriminate, and hand
someone a record that says how it was produced. Scanning, citation, drift detection and the full
evidence export are all additive on top of it and none of them are load-bearing for that claim.

---

## 8. What changed in v1.1

A five-pass gap analysis (document 08) produced 31 findings plus 5 more from research into
classified-environment development. The fixes are folded into 01–07. The substantial ones:

| Area | Change |
|---|---|
| Disclosure | Reviewer class, human attestation, and a generated disclosure statement in every export (02) |
| Run attestation | A started marker written by the handoff generator, and a check for markers with no completed row (02 §3.5) |
| Supply chain | Composition inventory per image, and a commit↔digest binding proving the scanned artifact is the shipped one (01 §4.9) |
| Manifest | Completeness probe for undeclared control-shaped code; RMF-aligned implementation status; scope statement (01 §7.2, §7.5) |
| Carried findings | Owner, review-by date, and automatic escalation when an upstream fix becomes available (01 §4.10) |
| Determinism | An explicit boundary: mechanical checks are re-derivable, the agent reviewer is not, and anything needing reproducibility must be mechanized (01 §1.5) |
| Topology | A two-instance model for development across a domain boundary: record authority, divergence tracking, ingest records, dependency lead time (04 §10) |
| Testing | An integration tier that runs the real external tools before a release (05 §6.1) |
| The loop | `make progress` is human-authored with its own negative fixtures; stall detection keyed on the done count; a budget ceiling; an amendment path for requirements that are wrong (07) |

---

## 9. Provenance

These documents were written from behavior and rationale, not transcribed from source. Requirements
describe what must be true and why; where a document names a concrete artifact, §8.2 of spec 06
governs — the naming is illustrative and an implementation is free to choose otherwise.

Rationales marked *observed* describe failures that occurred in practice. They are recorded because
a requirement whose cost is unknown is a requirement that gets removed by the next person who finds
it inconvenient.

**"The reference implementation"**, where these documents use the phrase, means the author's own
prior practice — the working methods these requirements were derived from. It is not a third-party
codebase, and no repository, organization, branch, file path or command name from any other project
appears anywhere in this package. Concrete names that do appear are invented examples, illustrative
under spec 06 §8.2, and an implementation is free to choose differently.
