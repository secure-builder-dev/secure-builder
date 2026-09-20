# Gap Analysis — Engine Specification Package v1.0

**Date:** 2026-09-20
**Method:** five passes over all eight documents, each with a distinct lens
**Result:** 36 findings — 9 P0, 15 P1, 11 P2 (31 from the five passes, 5 more from the
classified-environment research in §5)
**Status:** all findings dispositioned; fixes folded into specs 01–07 (see §6)
**Copyright:** © 2026 Casey Houle. All rights reserved. Confidential — not for distribution.

---

## 0. Method and what "five passes" means

Five sequential readings of the full package, each looking for a different class of defect. A single
pass finds what its lens is shaped to find; the value is in the lenses being genuinely different.

| Pass | Lens | Question |
|---|---|---|
| 1 | **Coverage** | What subject matter is absent entirely? |
| 2 | **Consistency** | Do the documents contradict each other or themselves? |
| 3 | **Adversarial** | What can be built that satisfies every MUST and is worthless? |
| 4 | **Assessor** | Hand the output to an assessor — what can they not be shown? |
| 5 | **Operational** | What breaks in the first ninety days of real use? |

Pass 3 is the one that matters most, because this package's entire claim is that it prevents
assurance theater. A package that can be satisfied by theater has failed at its own thesis.

**Severity.** P0 = would produce a false assurance claim, or undermines a premise the package rests
on. P1 = a material gap an implementer or assessor will hit. P2 = a correctness or consistency
defect worth fixing before anyone builds from this.

---

## 1. P0 findings

### P0-1 · The reviewer is an AI and the package never says so

**Passes 3, 4.** Spec 02 §10.1 maps gate verdicts to "assessment findings" and the gate log to
"assessment records." Spec 01 §6 specifies the reviewer as an agent in a cold context. Nowhere does
any record carry the fact that **the assessment was performed by an automated reviewer**.

Gate log rows record "reviewer identity" (02 REQ-3.1.2) with the stated purpose "accountability."
An identity string naming an agent does not establish accountability; it names a process.

This is the package's largest exposure and it is not technical. An assessor who discovers partway
through a review that the assessment evidence was machine-generated, and that this was nowhere
disclosed, does not simply discount that evidence — they lose confidence in the whole package,
including the parts that are solid. The honest framing is strictly stronger than the quiet one, and
it is available at no cost: contemporaneous machine-generated evidence with a human attestation on
top is a *better* story than most manually-assembled packages, and it only works if it is stated
first rather than discovered.

**Fix:** every gate row records reviewer *class* (human / automated / automated-with-human-review)
alongside identity; a human attestation field naming the accountable person per unit of work; and a
disclosure statement in the export bundle. Spec 02 §10 reframed from "this is the assessment" to
"this is contemporaneous evidence produced by the development process, attested by a named human."

### P0-2 · Gate log rows are self-reported and unforgeable in the wrong direction

**Pass 3.** The most important artifact in the package (02 §3, "if only one artifact survives, this
is the one") is written by the same agent whose verdict it records. Nothing binds a row to an actual
execution. Two specific attacks, neither requiring bad faith — ordinary optimization finds both:

- An agent that fails, re-runs, and writes only the passing row. 02 REQ-3.2.1 requires re-runs to
  append; nothing *detects* a re-run that did not append. The absence of a row is invisible by
  construction.
- A row written without a run behind it.

The package repeatedly insists that a check which cannot fail is worthless. The gate log is a record
that cannot be contradicted.

**Fix:** the handoff generator writes a **started** marker (range, commit, timestamp, run number)
before the gate runs. A started marker with no completed row is a visible, checkable gap, and the
check for it runs in the mechanical set. This makes the omission of a failing row detectable, which
is the case that matters.

### P0-3 · Manifest completeness is never asserted — only the entries that exist are verified

**Passes 3, 4.** Spec 01 §7.3 verifies that every *declared* control is implemented, called, and
tested. REQ-7.3.3 catches a manifest containing only placeholders. But nothing asserts the manifest
is **complete**: a manifest with one real entry passes every check in the package.

REQ-7.4.1 closes this going forward — a control-shaped diff with no manifest entry is blocking. It
does nothing for the adopted codebase, which spec 01 §9.3 establishes is the normal case.

The assessor's question is not "are your declared controls wired." It is "are these all of them."
The package currently has no answer.

**Fix:** a completeness probe that finds control-shaped code with no manifest entry — the same
control-shape detection REQ-6.3.1 already needs for the completeness-review trigger, pointed at the
tree instead of the diff. Output is an undeclared-controls list, dispositioned like the
never-reviewed inventory (declared, or explicitly accepted with a reason). It does not block; it
converts an unbounded unknown into a finite list.

### P0-4 · No supply-chain evidence: no SBOM, no build provenance, no artifact-to-source binding

**Passes 1, 4.** The scan subsystem (01 §4) covers five concerns and none of them is composition
inventory. There is no requirement for an SBOM, no build provenance or attestation, no verification
that the scanned image was built from the reviewed commit, and no dependency-integrity requirement
beyond "record new dependencies in a policy document" (01 §6.2.1 item 10).

Two consequences. For delivery: SBOM is now a baseline expectation for federal software delivery,
and a package without one is incomplete regardless of how good the rest is. For the package's own
logic: 01 REQ-4.5.2 requires rebuilding images from the current tree before scanning, but nothing
*proves* the scanned artifact corresponds to the reviewed source. That binding is the whole basis on
which a scan verdict says anything about the code that was reviewed.

**Fix:** SBOM generation per scanned image, retained as a scan artifact and included in the export;
the scan verdict stamp records the source commit **and** the image digest built from it; a check
that the digest the gate blessed is the digest the pipeline ships.

### P0-5 · "A verdict must be re-derivable" is not true of the reviewing agent

**Passes 2, 4.** Spec 01 §1.5 makes re-derivability a foundational premise and satisfies it by
requiring vendored, version-pinned reference data for verdict computation. That reasoning is sound
for the mechanical checks. It does not hold for the security gate, which is a language model
applying a checklist in prose. The same range reviewed twice produces different findings.

The package never acknowledges this. A premise stated as foundational and silently untrue of one of
the two gates is exactly the kind of defect the package exists to catch, and it will be found by an
assessor or a reviewer, not by us.

**Fix:** state the boundary plainly. Mechanical checks are deterministic and re-derivable; the
reviewing agent is not, and its value is **breadth of inspection against a fixed checklist, recorded
contemporaneously** — not reproducibility. Require the checklist version and the harness version in
every verdict so that what the reviewer was *asked* is re-derivable even though its output is not.
Anything whose correctness must be reproducible belongs in the mechanical set, and that is now a
stated design rule rather than an accident.

### P0-6 · Carried findings never block and never age out

**Passes 3, 4.** 01 REQ-4.6.2: a finding with no available fix is carried and must not block the
gate. The rationale is correct — a gate should not hold a team hostage to a third party's release
schedule. But nothing ever revisits a carried finding. 02 REQ-4.2.2 requires unsatisfied rows be
reported every run, which produces a list that grows monotonically and is read as wallpaper within
a month.

This is how a plan-of-action becomes permanent. It is also the exact failure the package names in
02 §1.3 — an acceptance whose remediation never happens — applied to scan findings instead of
design risks, and the package catches it in one place and not the other.

**Fix:** every carried finding carries an owner, a re-review trigger, and a **review-by date**. A
carried finding past its date, or one whose upstream fix has since become available, is a blocking
finding. The upstream-fix-now-available case is mechanically checkable on every scan and is the one
that actually fires.

### P0-7 · The loop's own exit condition is unverified, and written by the thing it judges

**Pass 3, on spec 07.** `make progress` decides v1.0. It is the single check that cannot be wrong,
and spec 07 has the assistant write it in step 4 alongside everything else. No negative fixture is
required for it, no mutation receipt, no human authorship. The one component whose failure mode is
"declares the build finished when it is not" is the one component to which the package's own rules
are not applied.

**Fix:** `make progress` is human-authored and human-owned, like `v1.0.md`. It gets negative
fixtures first — a ledger with a `done` row whose receipt is missing must fail; a receipt whose
broken-section passed must fail — and those fixtures are written before the loop starts.

---

## 2. P1 findings

### P1-1 · Three names for one artifact

**Pass 2.** The same register is called the *findings register* (02 §4), the *standing exceptions
register* (01 REQ-12.4), and a *permanent-record entry* (01 REQ-9.2.1). An implementer building from
01 and 02 in sequence will build two files. In a package whose own rule is that pointers must
resolve, this is the first thing to fix.

### P1-2 · The gate log schema has no harness-version column

**Pass 2.** 06 REQ-5.3 requires records to be able to reference the harness version in force. 02
REQ-3.1.2 enumerates the gate row's mandatory fields and there is no such field. Two requirements,
directly contradictory, in a package that elsewhere insists a schema defined in one place and
written in another must be checked for agreement. Add the column — and with P0-5, the checklist
version too.

### P1-3 · The scan verdict stamp is both excluded from and required by the record set

**Pass 2.** 02 REQ-2.3 excludes scan artifacts from version control by default. 01 REQ-3.3.1 requires
the handoff to verify a stamp for *this exact commit*, and 02 REQ-10.2.2 requires the scan bundle in
the export. If the stamp is gitignored it is local to one machine, and a gate run anywhere else
cannot see it. Resolve explicitly: the **stamp** is a record and is committed; the **raw output** is
an artifact and is not.

### P1-4 · No integration tier — everything is hermetic, and the external tools are the risk

**Passes 1, 5.** 05 REQ-5.1 forbids tests that need a network, container runtime, or device, for
good reasons. The consequence is that in a harness whose primary job is orchestrating external
scanners, **no test ever runs a real scanner**. The reference implementation's malware scanner was
broken in every containerized environment and its hermetic tests were green throughout.

**Fix:** a second, explicitly separate tier that runs the real tools, required to pass before a
release of the harness, reporting which environment it ran in. Hermetic tests gate every push; the
integration tier gates a version.

### P1-5 · Nothing bounds a project that is "not applicable" to everything

**Pass 3.** 01 §13.2 is careful: a non-applicable check must name the shape and state what covers
that ground instead. Nothing bounds the *aggregate*. A project shape where most checks report
not-applicable passes the whole suite honestly, one line at a time, with the honest lines summing to
an assurance claim nobody made. The engine's own Android track is close to this today.

**Fix:** the suite reports applicable / not-applicable / failed counts, and a not-applicable
proportion above a threshold is a finding requiring disposition — not a block. The point is to force
the sentence "this track is covered by four checks, and here is what is unguarded" to be written down
once.

### P1-6 · One mutation per control is a single point of gaming

**Pass 3.** 01 REQ-5.3.2 applies one mutation per control, inferred from shape, with a per-control
override. 05 REQ-3.3 requires *each distinct assertion* to be mutated independently — the stronger
rule, applied to the harness's own checks but not to the controls the harness exists to verify. The
weaker rule is on the more important target.

**Fix:** where a control has multiple enforcement branches, each is mutated. At minimum, an override
must state why the chosen mutation is representative.

### P1-7 · No POA&M artifact with dates and milestones

**Pass 4.** 02 REQ-6.3.1 records identifier, component, severity and reason-no-fix. A
plan-of-action needs a remediation milestone, a scheduled completion date, an owner, and status
history. "Input to a risk-tracking process" leaves the deliverable to be assembled by hand, which is
precisely the hand-assembly the package claims to eliminate.

### P1-8 · Control inheritance is absent

**Pass 4.** Systems on an accredited platform inherit a substantial fraction of their controls. The
package has no concept of an inherited or common control — every control in the manifest is one the
project implements. An assessor reading the manifest as the control set will find it conspicuously
short and draw the wrong conclusion.

**Fix:** either a manifest entry type for inherited controls (provider, the control, the evidence
reference) or an explicit scope statement that the manifest covers system-specific controls only and
inheritance is tracked elsewhere. The scope statement is cheap and prevents the misreading.

### P1-9 · No lifecycle for a standing-alarm finding

**Passes 1, 5.** 01 REQ-4.6.1 specifies a nightly severity-based alarm distinct from the gate
verdict. The alarm fires — and the package stops. There is no specification of what happens to code
already merged and running: who triages, in what time, how the fix enters the lifecycle, what record
it produces. The entire package is forward-looking: plan, build, gate, merge. The retroactive case —
a vulnerability discovered in shipped code — is the normal case in production and is unspecified.

### P1-10 · Concurrent work is not addressed anywhere

**Pass 5.** Every record is an append-only markdown table in git, and every process assumes one unit
of work at a time. With two developers on two branches: gate log rows conflict on every merge; the
standing-state snapshot diffs against "the previous gate's snapshot," which is ambiguous across
concurrent branches; the never-reviewed inventory races. Markdown tables are the worst possible
format for concurrent append.

This is a design question, not a defect, and it has to be answered deliberately — see the decisions
at the end.

### P1-11 · No spec-amendment path during the build

**Pass 5.** Spec 07 routes ambiguity to `.journal/questions`. It has no path for a requirement that
is *wrong* — and over 368 requirements there will be several. Without a path, the loop will either
implement something it knows is wrong or quietly reinterpret it, and no record will exist either
way. Ironic in a package with a governance protocol.

**Fix:** an amendment log in the build repo — requirement, why it is wrong, what replaces it, who
decided. It is the governance changelog applied to the specs themselves, and it is the artifact that
makes the eventual v1.1 of this package possible.

### P1-12 · The build's governance set is undefined on day one

**Pass 5.** 07 §5.1's tripwire defers "the governance set (spec 01 §11)" to a human. On day three of
the build, spec 01 §11 is not implemented. The tripwire has nothing to match against and will never
fire.

**Fix:** name the build's governance set explicitly and from the start: `v1.0.md`, `make progress`,
the hooks, `prompts/iteration.md`, and the specs themselves. Those files are human-owned for the
duration of the build.

### P1-13 · No cost ceiling on an unattended loop

**Pass 5.** 07 caps iterations at 200 and detects stalls. Neither is a spend control, and 368
requirements at roughly one per iteration means the cap is below the work. An unattended loop on a
personal account needs a budget the operator sets, checked per iteration, that stops cleanly and
writes the reason. Also: state the rough size of the commitment up front, because the honest number
changes how someone schedules it.

---

## 3. P2 findings

| # | Finding | Pass |
|---|---|---|
| P2-1 | **Requirement IDs are not unique across specs** (01 and 03 both have REQ-1.1.1). The ledger keys on spec+req so it works, but 07's "lowest-numbered requirement" is ambiguous across documents. Define the ordering. | 5 |
| P2-2 | **07's stall detector keys on commit HEAD**, and the loop's first act each iteration is a ledger commit — so it produces a new HEAD without progress, defeating the detector. Key it on the `done` count instead. | 5 |
| P2-3 | **The inner Stop hook and the outer driver may double-drive.** A blocking Stop hook inside a non-interactive invocation is untested here. Flag it as day-one verification, not an assumption. | 5 |
| P2-4 | **01 §0 declares agent definitions out of scope** as commodity, but 03 §1.3 and 06 §3 both specify them. Narrow the exclusion to persona/routing. | 2 |
| P2-5 | **Nothing specifies where a timestamp comes from.** Every record carries one; none is attested. Cheap to state, and an assessor may ask. | 4 |
| P2-6 | **No requirement that the harness's own dependencies are scanned.** The harness vendors catalogues and pulls scanner images; spec 05 covers self-testing, nothing covers self-scanning. | 1 |
| P2-7 | **No license/IP compliance check.** Frequently required for delivery; entirely absent. 06 REQ-8.4 requires a license record but nothing checks it against a policy. | 1, 4 |
| P2-8 | **Nothing prohibits real data in test fixtures.** 05 REQ-2.4 requires constructed fixtures for correctness reasons; the handling reason is not stated and is the one that bites. | 1 |
| P2-9 | **No verdict revocation.** A gate passes, merges, and is later found wrong. No mechanism marks a historical verdict superseded — and 02's no-deletion rule makes it ambiguous how to record it. | 4 |
| P2-10 | **No bound on record growth.** A gate log after three years is a markdown table thousands of rows long. Specify rotation by period with an index, before it becomes a migration. | 5 |
| P2-11 | **07's receipt schema does not constrain what a mutation may be.** Deleting the file under test produces a valid-looking receipt. Require the mutation to be a property-level edit to the implementation, not a structural change. | 3 |

---

## 4. What the passes say about the package as a whole

**What held up.** Every pass tried to find a false-green mechanism the package permits, and the
mechanical layer is genuinely hard to game: the honesty rules (01 §13), the manifest's recomputed
call sites (REQ-7.2.3), the template-only-manifest state (REQ-7.3.3), and the mutation requirement
are mutually reinforcing, and pass 3 could not construct a way through them. That is the core of the
package and it is sound.

**Where the gaps cluster — and they cluster tellingly.** Six of the seven P0s are at the boundary
between the harness and the humans and institutions around it: who attests, whether the evidence was
machine-made, whether the declared control set is the real one, whether the scanned artifact is the
shipped one, what happens to a finding nobody can fix. The package is strongest where it is checking
a file and weakest where it is making a claim to a person.

That is the expected shape for a system built by engineers solving engineering problems. It is also
exactly the surface an assessment lives on, which is why the fixes above are worth more per line
than anything else that could be added.

**One structural observation.** Three of the P0s (1, 2, 5) share a root cause: the package treats
the automated reviewer as if it were a deterministic check, and inherits assumptions from that
framing — reproducible verdicts, self-reported records, identity as accountability. Naming the
reviewer as what it is, once and prominently, resolves all three and makes the resulting story
stronger rather than weaker.

---

## 5. Addendum — findings from the classified-environment research (2026-09-20)

Research into how development actually works in classified/air-gapped environments surfaced five
further findings, four of which are new and one of which upgrades an existing one. Sources are
listed at the end.

### P0-8 · Spec 04 models one instance in three modes; the real topology is two instances

**New.** The established pattern for classified development is a **low side / high side** split:
uncleared or lower-cleared developers build on the unclassified network, and code crosses into the
classified environment through a cross-domain solution. That is not one harness running in offline
mode. It is **two harness instances with a one-way boundary between them**, and the package has no
model for it.

Consequences the current spec cannot answer:

- Gate records exist on both sides. Which is authoritative?
- A one-way boundary means high-side evidence **cannot flow back**. Whatever the ATO needs must be
  produced and deliverable on the high side, by an instance that may never have seen the low side's
  records.
- The coverage inventory (02 §8) computes "assessed by a gate" from gate-log history. A high-side
  instance that received a code drop rather than a merge history has no such history, so every file
  reads as never-assessed.

**Fix:** spec 04 gains a topology section specifying the two-instance case: which records are
authoritative on which side, what crosses the boundary in each direction, and how the high-side
instance establishes an assessed boundary for code it received rather than gated.

### P0-9 · Divergence between sides is unspecified, and it is the normal case

**New.** When a vulnerability is found high-side, there are two fix paths. Fix low-side and
re-transfer — correct, and gated by a scheduled transfer window measured in days. Or fix high-side —
fast, and the two sides have now diverged, with the low-side repository no longer describing what is
running.

This will happen, because operational pressure always wins against a transfer window. The package
says nothing about it, so it will be handled ad hoc and the divergence will be discovered later by
someone comparing artifacts.

**Fix:** a required record for any high-side-originated change — what changed, why it could not wait
for the low-side path, and the back-port status. Divergence becomes a tracked, countable quantity
rather than an accumulating surprise.

### P1-14 · A boundary transfer is an auditable event and produces no record

**New.** Spec 04 §3.5 and §4.2.2 specify transfer *paths* for catalogues and detection data, with
provenance, hashes and reviewable diffs. What they do not model is that the transfer itself is
logged, filtered and potentially **modified** by the cross-domain solution — content filtering can
redact, quarantine or strip. A bundle that arrives is not necessarily the bundle that was sent, and
the hash check (REQ-3.6) will correctly fail without explaining why.

**Fix:** every ingest writes a record — bundle identifier, production date, hash result, what
arrived, and whether it was modified in transit. Distinguish *hash mismatch because the bundle was
filtered* from *hash mismatch because the bundle is wrong*; the first is routine and the second is
an incident, and they currently look identical.

### P1-15 · Dependency approval lead time is not modelled

**New.** 01 §6.2.1 item 10 requires a new dependency to be recorded in the dependency policy
document. In a classified environment, adding a dependency means a formal request with
justification, an external scan performed on a connected system, and a transfer window — days to
weeks, not minutes.

A gate that treats a new dependency as a documentation line will pass work that cannot actually be
built on the high side.

**Fix:** the dependency policy records approval state and the date a dependency became available on
the target side. An unapproved dependency is a blocking finding on a high-side-targeted branch, not
a note.

### P1-4 upgraded · The integration tier is more than a nicety here

**Upgrade.** The hermetic-only testing gap (P1-4) is worse in this topology than stated. The high
side is where the toolchain is most different — mirrored registries, local package sources, offline
vulnerability data — and it is the environment the developer can least easily reach to debug. A
harness whose external-tool paths have never been executed anywhere will fail first in the place
where failure is most expensive to diagnose.

### What the research confirmed

Three things in the package held up well and should be stated more confidently:

- The **vendored, version-pinned catalogue** model (01 §8.2) is the correct shape. Local mirrors of
  dependencies, images and vulnerability data are the established pattern, not a workaround.
- **Offline bundle transfer with provenance** (04 §3.5, §4.2.2) matches how air-gapped patch and
  data management actually works: produce a dated bundle on a connected machine, transfer, ingest.
- **Refusing to relax the freshness threshold** (04 REQ-4.2.4) is right, and the research reinforces
  the reasoning: these environments support a continuous feed of vulnerability data precisely
  because the cadence is treated as an operational requirement rather than a best effort.

### Sources

- Anchore, *Introduction to the DoD Software Factory* and *Air Gapping for DevSecOps*
- Second Front, *How does control inheritance work for GovRAMP, FedRAMP, and DoD ATOs?*
- DoD CIO, *DoD Cybersecurity Reciprocity Playbook* (2024) and *DoD Enterprise DevSecOps Reference
  Design*
- CACI, *Low to High Side Development Processes*; GitLab/NCSI, *Cross-Domain DevSecOps*
- OPSWAT and Owl Cyber Defense, cross-domain solution overviews
- Sonatype, *Software Governance in Air-Gapped Environments*
- MITRE eMASS client documentation; DCSA *NISP eMASS Industry Operation Guide*

---

## 6. Disposition

Every finding is dispositioned, by the package's own rule (spec 01 §1.4): it becomes a requirement,
or it is explicitly accepted. Nothing is left as a note.

| Finding | Disposition |
|---|---|
| P0-1 reviewer is an AI | 02 §0 reframing; REQ-3.1.5–3.1.8 (class, attestation); §10.5 disclosure statement |
| P0-2 unfalsifiable gate log | 02 §3.5 run attestation — started marker + check |
| P0-3 manifest completeness | 01 §7.5 completeness probe |
| P0-4 supply chain | 01 §4.9 composition inventory + commit↔digest binding; 02 export and mapping table |
| P0-5 re-derivability | 01 §1.5 boundary, REQ-1.5.1–1.5.2; 02 §10.5.3 |
| P0-6 carried findings | 01 §4.10 aging and escalation; 02 REQ-6.3.1 plan-of-action fields |
| P0-7 unverified exit condition | 07 §2.1a — human-authored with its own negative fixtures |
| P0-8 two-instance topology | 04 §10 (new section) |
| P0-9 divergence | 04 §10.4 |
| P1-1 three names | 01 REQ-12.6 — one name, others withdrawn |
| P1-2 harness version column | 02 REQ-3.1.2 fields |
| P1-3 stamp in/out of version control | 02 REQ-2.3.1–2.3.2 |
| P1-4 integration tier | 05 §6.1 |
| P1-5 all-not-applicable | 01 REQ-13.2.3–13.2.4 |
| P1-6 one mutation per control | 01 REQ-5.3.2a |
| P1-7 POA&M fields | 02 REQ-6.3.1, 6.3.3, 6.3.4 |
| P1-8 inheritance | 01 REQ-7.2.1a, 7.2.4–7.2.6; 02 REQ-10.2.1a–1b |
| P1-9 standing-alarm lifecycle | 01 §4.10.1–4.10.2 |
| P1-10 concurrency | 02 §2.4 single-writer assumption + migration path |
| P1-11 spec amendment path | 07 §5.3 amendment log |
| P1-12 governance set day one | 07 §5.1 |
| P1-13 cost ceiling | 07 §5.2 budget guard |
| P1-14 ingest records | 04 §10.5 |
| P1-15 dependency lead time | 01 §6.2.1 item 10; 04 §10.6 |
| P2-1 requirement ordering | 07 §5.3 |
| P2-2 stall detector | 07 §5.2 — keyed on done count |
| P2-3 stop hook / driver | 07 §5.3 — day-one verification, not an assumption |
| P2-4 scope exclusion too broad | 01 §0 narrowed |
| P2-5 timestamps | 02 §2.5 |
| P2-6 harness self-scan | 01 REQ-10.6 |
| P2-7 license policy | 01 REQ-10.5; 06 REQ-8.4a |
| P2-8 real data in fixtures | **Accepted, not specified.** 05 REQ-2.4 already requires constructed fixtures; the handling rationale is added there rather than as a new requirement |
| P2-9 verdict revocation | 02 §11.5 |
| P2-10 record growth | 02 §2.6 |
| P2-11 receipt mutation constraint | 07 §2.2 |

**Result:** 454 requirements, up from 368. One finding accepted without a new requirement; the rest
became requirements.

**What is deliberately still open.** Two things this analysis names and does not resolve, because
neither can be resolved from here:

- **Assessor acceptance of machine-generated evidence** is not established by anything in this
  package, and cannot be. 02 §0 and §10.5 make the package honest about what it is; whether a
  specific authorizing official credits it is a conversation with that official.
- **The specific transfer procedures of a specific facility.** 04 §10 specifies the shape of the
  two-instance problem from the public literature. The actual windows, filters and approval paths
  are local, and the requirements are written to be satisfiable under a range of them rather than
  assuming one.
