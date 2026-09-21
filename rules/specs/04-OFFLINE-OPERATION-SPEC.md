# Offline and Air-Gapped Operation — Behavioral Specification

**Version:** 1.1 · drafted 2026-09-20, hardened after gap analysis
**Part of:** Engine Specification Package
**Status:** specification only — implementation-independent
**Copyright:** © 2026 Casey Houle. All rights reserved. Confidential — not for distribution.

---

## 0. Scope and why this is its own document

A harness that assumes network access has a different architecture from one that does not, and the
difference is not a flag. Several requirements in the companion specs are satisfied by fetching
something; in a disconnected environment those requirements must be satisfied differently or
explicitly declared unmet.

This document specifies three operating modes and what each guarantees. It matters for two distinct
situations that have the same technical shape:

- **A fully local build** — a workstation with no dependency on a hosted platform.
- **A controlled environment** — a network where outbound access is absent by policy.

The second is the demanding one, and designing for it makes the first free.

---

## 1. Three modes

**REQ-1.1** The harness MUST support three modes, and MUST know which one it is in.

| Mode | Outbound network | Hosted platform | Guarantees |
|---|---|---|---|
| **Connected** | Yes | Yes | Everything in the companion specs |
| **Local** | Yes | No | Everything except platform-enforced controls (§5) |
| **Disconnected** | No | No | Everything except currency verification (§3) and live remediation data (§4) |

**REQ-1.1a** Mode describes **one instance**. Where a project is developed on one network and
deployed on another, the correct model is **two instances with a boundary between them**, specified
in §10. An implementation MUST determine which of these it is before configuring modes, because the
two-instance case changes which records are authoritative and is not expressible as a mode.

**REQ-1.2** Mode MUST be explicit configuration, not inferred by attempting a connection and
observing failure.

**Rationale.** Inference makes a network outage indistinguishable from a policy boundary. The first
should be an error; the second is normal operation. Conflating them means an outage silently
degrades a verdict.

**REQ-1.3** Every output that would differ by mode MUST state the mode it was produced under.

---

## 2. The governing principle

**REQ-2.1** In every mode, a verdict MUST be computed from **local, version-pinned data only**.

**Rationale.** This is already required for reproducibility (companion spec 01, §1.5). The useful
consequence is that disconnected operation does not weaken verdicts at all — the verdict path never
touched the network. What disconnection removes is the ability to confirm that the local data is
still current, which is a different and lesser loss, provided it is declared.

**REQ-2.2** The only components permitted to reach the network are: the currency checker (§3), the
scanner image acquisition (§4.1), and the remediation-data updater (§4.2). No other component may
attempt a connection in any mode.

---

## 3. Standards currency without a network

**REQ-3.1** Catalogues MUST be vendored and version-pinned (companion spec 01, §8.2).

**REQ-3.2** In disconnected mode, the currency checker MUST report **"currency not checked"** and
MUST NOT report the pins as current.

**Rationale, and the specific trap.** The failure this prevents is treating "unverified" as a
resting state. If the offline path reports success, every run confirms currency that nobody
verified, and the pin silently ages past the point where it describes a published baseline. The
offline path must make the absence of verification *visible in the output*, every time.

**REQ-3.3** The offline path MUST exit successfully. It is a legitimate operating mode, not a
failure.

**REQ-3.4** Attempting a fetch in disconnected mode without the offline flag MUST be an **error**,
not a silent fallback.

**Rationale.** A silent fallback is how a run produces a report that looks online and is not.

**REQ-3.5** A **catalogue transfer path** MUST exist: an operator on a connected machine produces a
dated catalogue bundle; an operator in the disconnected environment ingests it.

**REQ-3.6** The bundle MUST carry provenance — source, content hash, catalogue version, retrieval
date — and ingestion MUST verify the hash.

**REQ-3.7** Ingestion MUST produce a reviewable diff of what changed, and MUST NOT be automatic.

**REQ-3.8** The harness MUST record the date of the last successful currency verification, and
SHOULD report the elapsed time since. Rationale: this converts "we cannot check" into a measurable
number an assessor can evaluate.

**REQ-3.9** A path MUST exist for catalogues that cannot be redistributed at all — published behind
authentication or carrying handling markings — by ingesting an operator-supplied copy, with the
marking acknowledgement required by companion spec 01, §8.4.5.

---

## 4. Scanning without a network

This is the hardest part of disconnected operation, because two scanner categories have opposite
requirements.

### 4.1 Scanner images

**REQ-4.1.1** Scanner images MUST be acquirable as an offline bundle: exported image archives with
their digests recorded.

**REQ-4.1.2** In disconnected mode, the harness MUST use images already present locally and MUST
NOT attempt a pull.

**REQ-4.1.3** A missing image MUST be a **failure**, never a skip. (Companion spec 01, §4.2.3.)

**REQ-4.1.4** A local registry MAY be used. Where one is, image references MUST remain pinned.

### 4.2 Detection data — the tension, stated plainly

The companion spec requires two things that conflict under disconnection:

- Vulnerability scanners download their data at run time. Disconnected, they cannot.
- The malware scanner's data ships inside its image and must be refreshed by a live update
  mechanism, because pinning freezes the signatures. Disconnected, it cannot.

**REQ-4.2.1** The harness MUST NOT resolve this by silently scanning with stale data.

**REQ-4.2.2** A **detection-data transfer path** MUST exist, analogous to §3.5: a connected machine
produces a dated data bundle; the disconnected environment ingests it into the shared storage the
scanners read.

**REQ-4.2.3** Every scan in disconnected mode MUST report the **age** of each scanner's detection
data in its output.

**REQ-4.2.4** The freshness threshold MUST remain enforced. Exceeding it MUST fail the scan.

**Rationale, and the design decision worth defending.** The temptation is to relax the threshold
because disconnected environments cannot refresh on demand. That converts the scan into a ritual: it
runs, it passes, and it has not been able to detect anything recent for months. Keeping the threshold
and failing makes the data bundle's delivery cadence an **operational requirement with a visible
deadline** rather than a background task that slips. If the organisation cannot meet the cadence,
that is a finding about the environment, and it should be recorded as one rather than absorbed by
the tool.

**REQ-4.2.5** The bundle's production MUST be scriptable, so the cadence can be automated on the
connected side.

**REQ-4.2.6** Ingestion MUST record the bundle's production date, and that date MUST appear in the
scan verdict stamp.

### 4.3 Image provenance

**REQ-4.3.1** Where base images come from a controlled registry, the harness MUST NOT embed
credentials for it in any tracked file.

**REQ-4.3.2** Base image acquisition is a build concern, not a scan concern. The scanner reads
locally built images and MUST NOT need registry access.

**Rationale — observed.** The reference implementation had carried registry credential plumbing
inside its scanner scripts, inherited from an earlier design. The scanners read local images and
never needed it; the plumbing was dead, and it was in the wrong layer besides.

---

## 5. Platform controls without a platform

Several controls in companion spec 01 are enforced by a hosting platform. Disconnected or local
operation must replace them or declare them absent.

| Control | Connected mechanism | Local / disconnected substitute |
|---|---|---|
| No direct writes to protected branch | Platform branch protection | Server-side hook on the shared repository |
| Change requires review | Platform pull request | Server-side hook requiring a second signer, or documented procedure |
| Checks pass before merge | Platform status checks | Server-side hook running the check command |
| Change history integrity | Platform audit log | Signed commits |

**REQ-5.1** Where a platform control is unavailable, the harness MUST either implement an equivalent
or **declare the control unmet in its output**.

**REQ-5.2** The harness MUST NOT treat the pre-execution hook (companion spec 03, §4.2) as a
substitute for a server-side control.

**Rationale.** A client-side hook is a convenience that a determined or hurried operator bypasses in
one command. It reduces accidents; it is not a control. Presenting it as one in an assessment record
would be a misrepresentation.

**REQ-5.3** A single-operator local environment MUST state that separation of duties is not achieved.

**Rationale.** One person cannot review their own work independently, whatever the tooling says.
Saying so plainly is more defensible than a record implying otherwise.

---

## 6. Documentation and generated pages

**REQ-6.1** Generated documentation MUST render with no network access.

**REQ-6.2** Typefaces MUST be embedded or MUST degrade to system fonts without layout failure.

**REQ-6.3** Diagrams MUST be hand-authored vector markup inline, not produced by a library fetched
at render time.

**REQ-6.4** No generated page may fetch scripts, stylesheets, images, or data at render time.

**Rationale.** A documentation page that silently renders blank on a disconnected workstation is
discovered at the worst possible moment, usually in front of someone being briefed.

---

## 7. What degrades, stated honestly

**REQ-7.1** The harness MUST be able to produce, on demand, a statement of which guarantees are
reduced in the current mode.

**REQ-7.2** That statement MUST be included in any exported evidence package (companion spec 02,
§10.2.2).

**REQ-7.3** The statement MUST distinguish:

| Category | Example |
|---|---|
| **Unaffected** | Control wiring verification, mutation testing, citation resolution, all record-keeping |
| **Reduced, quantified** | Detection data is N days old; catalogue currency last verified on date D |
| **Not achieved** | Platform-enforced merge control; separation of duties in a single-operator environment |

**Rationale.** The third category is the one that matters and the one most likely to be omitted. An
evidence package that is silent about an unmet control is worse than one that names it, because the
silence will be discovered and will cast doubt on everything else in the package.

---

## 8. Non-requirements

- **No degraded-mode verdicts.** A verdict is computed the same way in every mode, or it is not
  produced.
- **No automatic fallback from connected to offline.** REQ-3.4.
- **No relaxed freshness thresholds for disconnected operation.** REQ-4.2.4.
- **No claiming a platform control that is not present.** REQ-5.1.
- **No network access from any component not named in REQ-2.2.**

---

## 9. Build order for a local-first implementation

Building disconnected-first is easier than retrofitting it, because every network call added along
the way must later be found and removed.

| Stage | Build | Note |
|---|---|---|
| 1 | Mode configuration and the degradation statement (§1, §7) | Build this first; it shapes everything |
| 2 | Vendored catalogues + citation verification | Never needed a network |
| 3 | Control manifest, wiring verification, mutation | Never needed a network |
| 4 | Records and the evidence set | Never needed a network |
| 5 | Scanner images as an offline bundle (§4.1) | Before any scanning works |
| 6 | Detection-data transfer path (§4.2) | Before the scan can honestly report clean |
| 7 | Currency transfer path (§3.5) | Can lag; the offline report is honest without it |
| 8 | Platform-control substitutes (§5) | Or declare them unmet and move on |
| 9 | Two-instance topology (§10) | Only if the project crosses a domain boundary — but if it does, this is not optional and shapes stages 5–7 |

**A note on stage 1.** Implementing the degradation statement before anything else forces the
question "what does this guarantee, and under what conditions" to be answered for each component as
it is built. Retrofitted, it becomes an archaeology exercise across the whole codebase, and the
answers are guesses.


---

## 10. Two-instance topology — development across a domain boundary

### 10.0 Why this is not a mode

§1 describes one instance in one of three modes. The established pattern for development targeting a
controlled environment is different in kind: developers work on a lower-classification network (the
**low side**), and code crosses into the controlled environment (the **high side**) through a
gatekeeper that filters, logs, and may modify what passes. High-assurance boundaries are one-way.

That is **two harness instances with a one-way boundary between them**. It cannot be expressed as a
mode, because the questions it raises are not about connectivity — they are about which copy of the
record set is authoritative, and what an instance can claim about code it received rather than built.

An implementation that models this as "the high side runs in disconnected mode" will produce two
divergent record sets, each internally consistent, neither describing the whole, and will not notice
until someone compares them.

### 10.1 Record authority

**REQ-10.1.1** For each artifact class in companion spec 02 §2, the implementation MUST declare
which side is authoritative.

**REQ-10.1.2** The default assignment MUST be: **the side where the work happened owns the record**.
Low-side gates produce low-side rows; high-side gates produce high-side rows.

**REQ-10.1.3** Records MUST NOT be silently merged across the boundary. Where both sides hold rows
for the same unit of work, both MUST be retained and MUST be distinguishable by side.

**Rationale.** A merged series that does not say which side produced each row is unreadable as
evidence, because the two sides did not have the same tooling, the same data, or the same
constraints. Retaining the distinction costs one column.

**REQ-10.1.4** Every record MUST carry the identifier of the side that produced it.

**REQ-10.1.5** Where the boundary is one-way, the **high side's record set is the deliverable one**
for anything assessed against the high-side system.

**Rationale, and it is the practical consequence that matters most.** A one-way boundary means
high-side evidence cannot flow back. Whatever an authorization needs must therefore be *producible
and deliverable on the high side*, by an instance that may have no visibility into the low side's
history at all. An evidence pipeline that only works where the developers are is an evidence
pipeline that does not work where the assessment happens.

### 10.2 What crosses, in each direction

**REQ-10.2.1** The implementation MUST enumerate what crosses in each direction. Nothing crosses
that is not enumerated.

**REQ-10.2.2** The expected set, low to high: source at a defined revision, vendored catalogues
(§3.5), detection-data bundles (§4.2.2), scanner image bundles (§4.1.1), and approved dependencies
(§10.6).

**REQ-10.2.3** The expected set, high to low, **where the boundary permits it at all**: nothing
required for correctness. An implementation MUST NOT depend on a return path.

**Rationale.** Designing for a return path that policy may forbid produces a system that works in
the lab and stops at the boundary. Where a return path does exist it is a convenience; every
requirement here must hold without it.

**REQ-10.2.4** Each crossing MUST carry provenance: source side, revision or bundle identifier,
content hash, production date, and the operator responsible.

### 10.3 The assessed boundary for received code

**REQ-10.3.1** A high-side instance MUST be able to establish an assessed boundary (companion spec
02, §8) for code it **received** rather than gated.

**Rationale — this breaks silently and the failure is not obvious.** The coverage inventory computes
*assessed by a gate* from gate-log history: a file is assessed because a merge carrying it appears
in the log. A high-side instance that received a source drop has no such history. Every file
therefore reads as never-assessed — which is either a false alarm that trains people to ignore the
inventory, or, if someone suppresses it, a false clean. Both are worse than the truth.

**REQ-10.3.2** A received code drop MUST be accompanied by the **transferred gate records** covering
it, where the boundary permits, and the high-side inventory MUST treat those as evidence of
assessment **on the low side**, recorded as such.

**REQ-10.3.3** Where gate records cannot cross, received code MUST be classified as *assessed
elsewhere, evidence not available* — a distinct third state from *assessed* and *never assessed*.

**Rationale.** This is companion spec 01 §1.2's rule applied to an artifact rather than a check.
"Assessed somewhere I cannot show you" is a real and defensible state; it is not the same as
assessed, and it is not the same as unassessed. Collapsing it into either one is the falsehood.

**REQ-10.3.4** The proportion of the high-side tree in the third state MUST be reported in the
export.

### 10.4 Divergence — the case that will actually happen

When a vulnerability is found on the high side there are two fix paths. Fix on the low side and
re-transfer: correct, and gated by a transfer window measured in days. Or fix on the high side:
immediate, and the two sides have now diverged, with the low-side repository no longer describing
what is running.

**REQ-10.4.1** A high-side-originated change MUST produce a record naming: what changed, why it
could not wait for the low-side path, who authorized it, and its back-port status.

**REQ-10.4.2** Back-port status MUST be one of: *not yet ported*, *ported at revision R*, or
*will not be ported*, the last requiring a written reason.

**REQ-10.4.3** The count of unported high-side changes MUST be reported at every gate and in the
export.

**REQ-10.4.4** A high-side-originated change MUST pass the high-side gate. Urgency is a reason to
skip the transfer window; it is not a reason to skip review.

**Rationale for the section.** This will happen, because operational pressure beats a transfer
window every time, and pretending otherwise produces no record rather than no divergence. Specifying
it converts divergence from an accumulating surprise — discovered months later by someone comparing
two trees — into a number that is visible at every gate and can be driven down deliberately. The
count is the point: one unported change is a normal Tuesday, and forty is a different system.

### 10.5 Ingest records

**REQ-10.5.1** Every bundle ingested across the boundary MUST produce a record: bundle identifier,
production date, arrival date, hash verification result, and whether the content was modified in
transit.

**REQ-10.5.2** The implementation MUST distinguish **hash mismatch because the boundary filtered the
content** from **hash mismatch because the bundle is wrong**.

**Rationale.** A cross-domain gatekeeper performs content filtering — it can redact, strip or
quarantine. A bundle that arrives is therefore not necessarily the bundle that was sent, and §3.6's
hash check will correctly fail without explaining why. The two cases look identical and are not: the
first is routine and needs a re-send or an exemption, the second is an integrity incident. An
implementation that cannot tell them apart will learn to treat integrity failures as routine, which
is the worst available outcome.

**REQ-10.5.3** A filtered bundle MUST NOT be ingested on the assumption the filtering was benign.
It is re-requested, or the filtering is understood and recorded.

**REQ-10.5.4** Ingest records are part of the evidence set and MUST be included in the export.

**Rationale.** They are the chain of custody for every piece of reference data the high-side verdicts
depend on. An assessor asking "where did your vulnerability data come from and when" is asking for
exactly this record.

### 10.6 Dependency approval

**REQ-10.6.1** The dependency policy MUST record, per dependency: approval state, approval date, and
the date it became available on the target side.

**REQ-10.6.2** A branch targeting the high side MUST fail its gate if it introduces a dependency not
yet approved and available there.

**REQ-10.6.3** The failure MUST name the lead time, not merely the fact.

**Rationale.** Adding a dependency in a controlled environment means a written request with
justification, a scan performed on a connected system, and a transfer window — days to weeks. A gate
that treats a new dependency as a documentation line (companion spec 01, §6.2.1 item 10) will pass
work that cannot be built where it is going, and the discovery happens at the boundary, after the
review, by someone who cannot fix it. Naming the lead time at the moment the dependency is added is
the difference between a planning input and a surprise.

### 10.7 Non-requirements for the topology

- **No automatic synchronization between sides.** Every crossing is an operator action with a record.
- **No dependence on a return path.** REQ-10.2.3.
- **No merged record series without side attribution.** REQ-10.1.3.
- **No treating received code as gated.** REQ-10.3.3.
- **No high-side change without a record.** REQ-10.4.1, whatever the urgency.
