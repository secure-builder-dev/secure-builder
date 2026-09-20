# Security Layer — Behavioral Specification

**Version:** 1.1 · drafted 2026-09-20, hardened after gap analysis
**Describes:** the compliance and assurance subsystem of an AI-assisted development harness
**Part of:** Engine Specification Package
**Status:** specification only — implementation-independent
**Copyright:** © 2026 Casey Houle. All rights reserved. Confidential — not for distribution.

---

## 0. How to read this document

This is a **behavioral specification**, not documentation of an existing codebase. It describes
what the security layer must do and why each requirement exists, in terms that do not depend on the
language, directory layout, or command runner used to implement it. Where the reference
implementation made an arbitrary choice (a filename, a flag spelling), this document says so and
does not require it.

Requirements use these words:

- **MUST** — the behavior is load-bearing. An implementation lacking it does not satisfy this spec.
- **SHOULD** — strongly recommended; deviation needs a documented reason.
- **MAY** — genuinely optional.

Each numbered requirement is followed by a **Rationale** paragraph. The rationale is not commentary.
Several requirements look arbitrary or over-cautious until you know the failure they were written
against, and an implementer who does not know the failure will simplify the requirement away.

### What this document deliberately omits

Three subsystems of the wider harness are **out of scope** here because they are generic, widely
implemented elsewhere, and carry no compliance weight:

- **Project onboarding and interview flow** — turning a blank repo or an existing codebase into a
  product spec. Any agent-driven questionnaire produces this.
- **Agent persona content and skill routing** — the mechanism by which a coding agent is given a
  role and a procedure. Commodity. Note the narrowness: the *distribution* of reviewer definitions
  (spec 06 §3) and the constraint that they cannot be thin (spec 03 §1.3) are both in scope, because
  both are load-bearing for whether the reviewer's rules actually reach it.
- **Ticket implementation loop** — claim a unit of work, write a failing test, make it pass, commit.
  Commodity.

What remains — everything in this document — is the part that makes the harness a *compliance*
instrument rather than a productivity one.

---

## 1. Foundational premises

These are the theses the whole layer rests on. An implementation that discards one of these has
built something different, whatever else it keeps.

### 1.1 A check that has never failed is unobserved, not proven

**Premise.** The default state of a verification mechanism is *not working*. Checks rot, get
disconnected, scan the wrong target, or were never wired to a call site. None of these announce
themselves, because a check that runs nothing and a check that runs and finds nothing produce the
same output: success.

**Consequence.** Every verification mechanism in this layer MUST have a demonstrated failure mode.
Either it has been observed failing against a deliberately broken input, or it is not yet evidence.

### 1.2 Silence is not a pass

**Premise.** The most dangerous defect class in a compliance pipeline is the **false green**: exit
code zero with no work performed. It is dangerous specifically because it is indistinguishable from
success at every level that matters — the log line, the exit code, the CI badge, the audit artifact.

**Consequence.** Every component MUST distinguish, in its output, between:

1. **Checked, clean** — the check ran against real input and found nothing.
2. **Not applicable** — the check has nothing to run against, structurally, on this project shape.
3. **Could not run** — the check was prevented from running.
4. **Checked, findings** — the check ran and found something.

States 2 and 3 MUST NOT be reported with the same wording as state 1. State 3 SHOULD exit non-zero.

### 1.3 Review contaminated by construction is not review

**Premise.** The reasoning that justified a shortcut while building is exactly the reasoning that
will excuse it during review. This is not a discipline failure; it is how justification works. The
person who decided a test was unnecessary will, reviewing an hour later, still believe it.

**Consequence.** The reviewing context MUST be structurally separated from the building context,
such that no build-time reasoning is available to the reviewer. The reviewer reads the artifact
(the diff) and the rules, and nothing else.

### 1.4 A finding is a defect in the checks, not only in the code

**Premise.** Any defect a human found by reading is a defect the automated checks did not find. The
code fix addresses one instance. The check addresses the class.

**Consequence.** Every finding MUST be triaged into one of two dispositions: mechanical (becomes an
automated check) or judgmental (becomes a line in a reviewer checklist). Findings that receive
neither disposition recur.

### 1.5 A verdict must be re-derivable

**Premise.** A compliance verdict is an assertion about a specific tree at a specific moment, which
someone may need to re-examine months later. A verdict that depends on a live network fetch cannot
be reproduced, because the remote source will have changed.

**Consequence.** Verdicts MUST be computed against vendored, version-pinned reference data. Live
fetching is permitted **only** for reporting currency of that vendored data, never for deciding a
verdict.

**The boundary, stated plainly, because half of this layer does not satisfy it.** The mechanical
checks are deterministic: same tree, same catalogues, same result, re-derivable years later. The
reviewing agent (§6) is a language model applying a checklist in prose, and it is **not**
reproducible — the same range reviewed twice yields different findings. Pretending otherwise would
be exactly the kind of unexamined claim this layer exists to catch.

What the agent reviewer offers instead is **breadth of inspection against a fixed checklist,
performed contemporaneously and recorded**. That is genuinely valuable and it is not the same
property, so it must not be described as the same property.

Two rules follow, and they are load-bearing:

**REQ-1.5.1** The *inputs* to a review MUST be re-derivable even where its output is not: every
verdict MUST record the checklist version and the harness version under which it ran, so a later
reader can reconstruct what the reviewer was asked, if not what it answered.

**REQ-1.5.2** Any property whose correctness must be reproducible MUST be implemented as a
mechanical check, not left to the reviewing agent. When a judgment check proves load-bearing, that
is the signal to mechanize it — which is the same disposition rule as §1.4, arrived at from the
other direction.

### 1.6 The system cannot certify changes to its own rules

**Premise.** The reviewing agent reads its criteria from a file. If a change weakens that file, the
next review applies the weakened criteria. The review of a rule change is therefore structurally
incapable of catching a weakening — it is not a matter of the reviewer being insufficiently careful.

**Consequence.** Changes to the rule set MUST be governed by a separate protocol in which a human is
the accountable control, and the automated review is advisory only.

---

## 2. Configuration model

### 2.1 The four axes

The security layer's behavior is switched by exactly four project-level values, fixed at
initialization:

| Axis | Values | Determines |
|---|---|---|
| **Track** | `web` · `android` | Toolchain, test runner, linter, which gate blocks apply |
| **Tier** | `IL4` · `IL6` | Whether the elevated control block is enforced or informational |
| **Provider** | `aws` · `azure` · `tactical` | Which infrastructure checks apply; cloud vs on-prem |
| **App type** | `native` · `atak` | Android-only; affects distribution and runtime host |

**REQ-2.1.1** These values MUST be stored in a single machine-readable project configuration file at
a fixed, well-known path.

**REQ-2.1.2** Every component that varies by project shape MUST read these values from that file
rather than accepting them as flags. Rationale: a flag can be forgotten at gate time; a file cannot.

**REQ-2.1.3** A sentinel value MUST exist meaning *not yet chosen*.

**REQ-2.1.4** If any axis holds the not-yet-chosen sentinel, the security gate MUST return a
blocking finding and MUST NOT pass. Rationale: an uninitialized project has no defined control
baseline, so any verdict about it is meaningless. Failing loudly is the only honest option.

### 2.2 Forced combinations

**REQ-2.2.1** Certain axis combinations are not independently selectable. In the reference, choosing
`android` forces `IL6` and `tactical`. The initializer MUST apply such constraints automatically
rather than asking and validating.

Rationale: an operator asked four independent questions will eventually produce an incoherent
combination — an Android build targeting a cloud provider it will never deploy to. Constraints
encoded in the initializer cannot be answered wrongly.

### 2.3 Conditional check blocks

**REQ-2.3.1** The reviewer checklist MUST support blocks that activate on an axis value.

**REQ-2.3.2** Three activation semantics MUST be distinguished, because they are not the same thing:

- **Additive** — the block's checks run *in addition to* the base set. (Reference: the elevated-tier
  block, the mobile-track block.)
- **Substitutive** — the block's checks *replace* a named subset of the base set. (Reference: the
  on-prem provider block replaces the cloud infrastructure checks.)
- **Informational** — the block is displayed but not enforced. (Reference: the elevated-tier block
  when the project is at the lower tier.)

**REQ-2.3.3** A substitutive block MUST NOT reduce the application-layer checks. Only
infrastructure-shaped checks are substitutable.

Rationale: authentication, authorization, injection defence and input validation are properties of
the application, not of where it runs. A deployment-target change must never be able to remove them.

---

## 3. Where security attaches to the lifecycle

The harness runs a repeating unit of work (an *epic*: a branch, a set of tickets, one merge). The
security layer attaches at five points.

```
  PLAN ─────► BUILD ─────► SCAN ─────► HANDOFF ─────► REVIEW ─────► MERGE ─────► CLOSE
                 │            │            │             │            │
              [3.1]        [3.2]        [3.3]         [3.4]        [3.5]
           continuous    pre-gate     precondition   two gates    human only
             checks       scan          refuses        on the       merge
                                       unscanned       range
```

### 3.1 Continuous checks (during build)

**REQ-3.1.1** A single command MUST run every mechanical check, and CI MUST invoke that same
command. Rationale: two definitions of "the checks" drift within weeks, and the drift is discovered
by a failure in the environment that has the stricter set.

**REQ-3.1.2** That command MUST be runnable locally with no credentials and no network.

### 3.2 The scan runs *before* the gate

**REQ-3.2.1** The vulnerability and composition scan MUST complete, and be green, before the review
gate is entered.

**Rationale — this is the ordering requirement most likely to be "simplified" by an implementer, and
it is load-bearing.** A vulnerability finding is remediated by changing a dependency version. If the
scan runs after the quality review, the resulting dependency bump invalidates the coverage
measurements and test results the review just certified — the review blessed a tree that no longer
exists. Running the scan at the end of the review has the same defect: the finding still arrives
after the measurements were taken. Only scanning *before* the review, and fixing on the branch as
ordinary work, lets the review run once against a settled tree.

### 3.3 The handoff refuses an unscanned tree

**REQ-3.3.1** The mechanism that produces the review handoff MUST verify that a scan has been
recorded, that it describes **this exact commit**, and that its verdict was green. If any is false,
the handoff MUST be refused.

**REQ-3.3.2** An override MUST exist for the case where scanning is impossible (no container runtime
available), and it MUST announce itself in the output. It MUST NOT be usable to bypass a *failed*
scan — only an *impossible* one.

Rationale: REQ-3.2.1 without REQ-3.3.1 is a convention. Conventions survive until the first
deadline.

### 3.4 Two gates on the range

Covered in §5 and §6.

### 3.5 Merge is a human act

**REQ-3.5.1** No automated agent may merge to the protected branch, approve its own work, or
override a gate verdict.

**REQ-3.5.2** This MUST be enforced by the hosting platform's branch protection, not only by
instruction. Rationale: an instruction is a request; branch protection is a wall. The instruction is
still worth writing, because it stops the attempt earlier and more clearly.

**REQ-3.5.3** A local pre-execution hook SHOULD additionally refuse the specific dangerous commands
(push to protected branch, merge while on protected branch, remote merge command) before they reach
the network. This is defence in depth, not the primary control.

---

## 4. The scan subsystem

### 4.1 Composition

**REQ-4.1.1** The scan MUST cover at least these five concerns, each by a separate tool:

| Concern | What it reads |
|---|---|
| Container build hygiene | Container build definitions |
| Infrastructure-as-code misconfiguration | IaC templates and manifests |
| Malware / unexpected binary content | The working tree |
| Known vulnerabilities in built images (A) | Built images |
| Known vulnerabilities in built images (B) | Built images |

**REQ-4.1.2** Two independent vulnerability scanners MUST be used, and their findings correlated.
Rationale: vulnerability databases disagree. A finding both report is a finding; one only one
reports is worth reading but not blocking.

### 4.2 Execution model

**REQ-4.2.1** Scanners MUST run as pinned container images, not host-installed binaries.

**Rationale.** A host-install requirement means the scan works on the one workstation somebody set
up and silently degrades everywhere else. Worse, the degradation is a false green: a missing scanner
and a clean scanner both produce "no findings." Containerization makes the tool version a one-line
change in a single file rather than a request that every developer re-run an installer.

**REQ-4.2.2** The implementation MUST support an explicit engine selection with at least three
modes: containers-only, host-binaries-only, and automatic. Automatic selects containers when a
container runtime is usable.

**REQ-4.2.3** A scanner that cannot run MUST cause the scan to fail. It MUST NOT be skipped.

### 4.3 Version pinning — and the one exception

**REQ-4.3.1** Scanner images MUST carry an explicit version tag or digest. An unpinned reference is
a defect.

**REQ-4.3.2** Scanners whose detection data is **embedded in the image** MUST be pinned to a *moving*
tag, never a digest and never an immutable patch tag.

**Rationale, with the failure that produced it.** Vulnerability scanners that download their
database at runtime can be pinned to a digest freely, because the pin governs the tool and not the
data. A malware scanner that ships its signature set inside the image is the opposite case: pinning
it freezes the signatures permanently, and the scan quietly stops recognizing anything published
after the image was built. The subtlety that bit the reference implementation: an *immutable patch
tag* is a digest wearing a tag's clothes. The publisher builds `x.y.z` once and never rebuilds it,
so pinning to a patch version has exactly the effect of pinning to a digest. Only tags the publisher
rebuilds — the moving major/minor line, or a `stable`/`latest` alias — actually move.

**REQ-4.3.3** An automated check MUST enforce REQ-4.3.2 by rejecting a digest reference *and* a
patch-version reference for the embedded-data scanner.

### 4.4 Detection-data freshness

**REQ-4.4.1** Before a scan is allowed to report clean, the age of the embedded detection data MUST
be determined and compared against a threshold.

**REQ-4.4.2** If the data is older than the threshold, the implementation MUST attempt a refresh
using the tool's own update mechanism, then re-check.

**Rationale, and a second failure worth inheriting.** The reference originally attempted the refresh
by pulling a newer image. That cannot work: if the newest published image *is* the stale one, pulling
changes nothing, and the check then emits advice ("use a newer version") that the operator cannot
act on because they are already on the newest. A threshold whose remedy cannot clear it is worse
than no threshold — the operator learns to skip the check. The refresh must use a mechanism that can
reach current data independently of the image build date.

**REQ-4.4.3** The refresh mechanism and the scan MUST share persistent storage for the detection
data. Rationale: if they run as separate container invocations with ephemeral filesystems, the
refresh is discarded before the scan sees it.

**REQ-4.4.4** If the data age cannot be *determined at all*, the scan MUST refuse to report clean.

**Rationale.** In the reference, this branch originally emitted a warning and proceeded, under a
comment asserting it had never occurred. It then occurred: a misconfigured image reference made every
scanner invocation fail, the version string was unparseable, and a scan that could detect nothing was
free to print *no infections found*. An override MAY exist, but it MUST mark the resulting verdict as
unverified rather than clean.

### 4.5 Scanning the right artifact

**REQ-4.5.1** The scan MUST determine which images the project actually ships, from the deployment
pipeline definition where one exists, and fall back to convention otherwise.

**Rationale.** Local development compose files build *development* images, often on a different base
from the hardened images the deployment pipeline builds. Defaulting to the development names scans
images the project never deploys and produces a number that looks like evidence and is not.

**REQ-4.5.2** Images MUST be rebuilt from the current tree before scanning, with base-image refresh
and without layer cache.

**REQ-4.5.3** Where a build is skipped for any reason, the implementation MUST verify that no stale
image is silently scanned in its place, and MUST refuse rather than grade a stale artifact.

Rationale: on a developer machine a stale tagged image is the *normal* state, so a skipped build
plus a tag search equals scanning last week's code and reporting it as today's.

### 4.6 Two separate verdicts

**REQ-4.6.1** The scan MUST produce two distinct pass/fail judgments, with different policies:

| Verdict | Policy | Used by |
|---|---|---|
| **Gate verdict** | Fails on: anything actionable (a fixable finding, a malware hit), or fewer than the full scanner set having run | The review gate |
| **Standing-alarm verdict** | Fails on: any finding at high or critical severity | Scheduled/nightly runs |

**Rationale.** These must not be the same policy. A scheduled alarm should fire on danger, so
severity is correct there. A gate using the same rule would block an epic indefinitely over a
vulnerability with no upstream fix available — holding the team's work hostage to a third party's
release schedule. The gate's question is "is there something to do here," not "is there anything
dangerous in the world."

**REQ-4.6.2** A finding with no available fix MUST be recorded as a carried risk item and MUST NOT
block the gate.

**REQ-4.6.3** A scanner that did not run MUST fail the gate verdict, independent of findings.
Rationale: a partial scan reporting nothing is indistinguishable from a complete scan reporting
nothing.

### 4.7 Finding routing

**REQ-4.7.1** Scan results MUST be sorted automatically into two documents:

- **Actionable** — findings with a known remediation, routed to whoever owns that surface
  (application dependencies vs. infrastructure definitions).
- **Carried** — findings with no available fix, formatted as risk-acceptance candidates.

**REQ-4.7.2** The existence of the actionable document, not its contents, MUST be the gate's
blocking condition. Rationale: this makes the blocking condition a file-system fact rather than a
parse, which cannot silently mis-parse to zero.

### 4.8 The verdict stamp

**REQ-4.8.1** A completed scan MUST write a machine-readable stamp recording at minimum: the commit
identifier scanned, the verdict, and a timestamp.

**REQ-4.8.2** The handoff precondition (REQ-3.3.1) reads this stamp. A stamp naming a different
commit MUST be treated as no stamp at all.

### 4.9 Composition inventory and artifact binding

**REQ-4.9.1** A software bill of materials MUST be generated for each scanned image and retained as
a scan artifact.

**REQ-4.9.2** The inventory MUST be included in the evidence export (companion spec 02, §10.2.2).

**Rationale.** A composition inventory is a baseline expectation for federal software delivery, and
a package without one is incomplete however strong the rest is. It is also the artifact that makes a
vulnerability finding checkable rather than trusted: a scanner's claim about what is in an image can
be compared against a generated inventory of what was put there.

**REQ-4.9.3** The verdict stamp (§4.8) MUST record **both** the source commit scanned and the
**digest of each image built from it**.

**REQ-4.9.4** A mechanical check MUST assert that the image digest the gate blessed is the digest
the deployment pipeline ships.

**Rationale — this closes a hole in the layer's own logic, not merely a delivery gap.** REQ-4.5.2
requires images to be rebuilt from the current tree before scanning, and REQ-4.5.1 requires scanning
what the project actually ships. Neither *proves* the scanned artifact corresponds to the reviewed
source. Without the binding, the chain from "this code was reviewed" to "this image is safe" has an
unverified link in the middle, and every verdict downstream of it inherits that weakness. With it,
the chain is checkable end to end by a comparison of two strings.

**REQ-4.9.5** A digest mismatch MUST be a blocking finding, and MUST be reported as *the artifact
under review is not the artifact being shipped* rather than as a scan failure.

### 4.10 The standing alarm and the aging of carried findings

§4.6 separates the gate verdict from the standing-alarm verdict. The alarm fires on a schedule
against code that is already merged and running, which is a different situation from a gate finding
and needs its own handling.

**REQ-4.10.1** A standing-alarm finding MUST have a defined disposition path: an owner, a triage
window, and an entry point into the ordinary lifecycle. An alarm with no path is a notification, not
a control.

**REQ-4.10.2** A standing-alarm finding MUST produce a durable record, so that the interval between
detection and remediation is measurable.

**Rationale.** The retroactive case — a vulnerability discovered in shipped code — is the normal
case in production, and a layer that specifies only the forward path (plan, build, gate, merge) has
specified the easy half. The measurable interval is also what a continuous-monitoring record is
actually asked to demonstrate.

**REQ-4.10.3** Every carried finding (§4.6.2) MUST record an owner, a re-review trigger, and a
**review-by date**.

**REQ-4.10.4** A carried finding whose review-by date has passed MUST become a blocking finding.

**REQ-4.10.5** A carried finding for which an upstream fix has **become available** since it was
carried MUST become a blocking finding, and this MUST be checked on every scan.

**Rationale, and why this matters more than the date.** REQ-4.6.2 is correct that an unfixable
finding must not block — holding a team hostage to a third party's release schedule helps nobody.
But nothing in that rule ever revisits the decision, and "report it every run" produces a
monotonically growing list that is read as wallpaper within a month. This is precisely the failure
the companion spec describes in its §1.3 — an acceptance whose remediation never happens — and the
layer currently catches it for design risks and not for scan findings.

REQ-4.10.5 is the one that fires in practice. *No fix available* is a statement about a moment in
time, and it stops being true without anyone being told. Re-checking it on every scan costs nothing
and converts a permanent exception back into ordinary work the day it becomes possible.

---

## 5. The quality gate

The quality gate is not itself a security control, but two of its criteria are load-bearing for the
security layer and are specified here.

### 5.1 Coverage is measured on the range

**REQ-5.1.1** Coverage thresholds MUST be evaluated against the files changed in the range under
review, not the project average.

Rationale: a project-wide average lets a large well-tested codebase absorb an untested new control
without moving the number.

**REQ-5.1.2** Thresholds SHOULD vary by layer, with the highest requirement on the layers where
controls live (service, data access, middleware).

### 5.2 The negative-test set

**REQ-5.2.1** For every route added or changed, a test MUST exist asserting rejection without
credentials.

**REQ-5.2.2** For every record-scoped route, a test MUST exist asserting that one principal cannot
read or mutate another's records.

**REQ-5.2.3** For any operation that can remove the last privileged principal, a test MUST exist
asserting that it is prevented.

**REQ-5.2.4** The routes MUST be enumerated from a generated inventory of the running code, not
from a hand-maintained list.

**REQ-5.2.5** Where the range adds no routes, the reviewer MUST state that the section was empty
rather than passing it silently.

Rationale: on project shapes with no HTTP surface (a mobile plugin, a library), this section has
nothing to enumerate and passes trivially — producing a verdict identical to one where every route
was found and covered. See §1.2.

### 5.3 Mutation of declared controls

**REQ-5.3.1** Before the gate can pass, every declared security control MUST be broken on purpose,
the test suite run, and the suite MUST fail. A control whose mutation leaves the suite green is a
blocking finding.

**Rationale.** A passing test proves the code behaves. It does not prove the test would notice if
the code stopped behaving. This is the only mechanical check in the layer that verifies the *tests*
rather than the code, and it is the one that catches a test asserting on a stub, a test whose
assertion is unreachable, or a control with no test at all despite a test file bearing its name.

**REQ-5.3.2** The mutation applied MUST be appropriate to the control's shape. The reference infers
from signature and naming, with an explicit override available per control:

| Control shape | Mutation |
|---|---|
| Middleware (passes control onward) | Short-circuit to pass-through |
| Decision function (returns a permission) | Return permissive constant |
| Scoping / filtering function | Return the input unmodified |
| Redaction / sanitization | Return the input unmodified |
| Other | Return without effect |

**REQ-5.3.2a** Where a control has more than one enforcement branch, **each branch MUST be mutated
independently**. Where a single mutation is used for a multi-branch control, the override MUST state
why the chosen mutation is representative.

**Rationale.** The self-test discipline (spec 05, §3.3) already requires per-assertion mutation for
the harness's own checks, on the argument that a suite of ten assertions where nine are load-bearing
and one is vacuous passes identically to one where all ten are. That argument applies at least as
strongly to the controls the harness exists to verify — yet the weaker rule was on the more
important target. One mutation per control is a single point of gaming: the mutation that is easiest
to detect is the one that gets chosen.

**REQ-5.3.3** A baseline run MUST be performed first, confirming the suite is green before mutation.
A red baseline aborts: mutation results against an already-failing suite mean nothing.

**REQ-5.3.4** Every mutated file MUST be restored after the run, and the implementation MUST verify
restoration rather than assume it.

---

## 6. The security gate

### 6.1 Execution context

**REQ-6.1.1** The security gate MUST execute in a context containing only: the handoff prompt, the
rules, and the ability to read the repository at the range under review. It MUST NOT have access to
the conversation in which the code was written. (See §1.3.)

**REQ-6.1.2** The handoff prompt MUST NOT contain a free-text field through which build-time
narrative could be carried across.

**REQ-6.1.3** The gate MUST read the diff from version control directly, not accept a diff as input.
Rationale: an input diff can be filtered.

**REQ-6.1.4** The security gate runs only after the quality gate has passed. Rationale: reviewing
the security properties of code whose tests do not pass is wasted effort.

### 6.2 The base checklist

**REQ-6.2.1** The base checklist MUST cover at minimum:

1. **Credential hygiene** — no embedded secrets, including no fallback or default values in
   configuration.
2. **Authentication completeness** — every endpoint requires a valid token, with enumerated
   exceptions; the authenticating middleware is registered before all handlers such that no route can
   be reached around it.
3. **Authorization enforcement** — role and scope rules enforced at the API layer, never only in the
   client.
4. **Negative coverage** — tests exist for the rejection cases, not only the success cases.
5. **Last-privileged-principal guard** — enforced server-side.
6. **Injection defence** — parameterized queries only.
7. **Soft-delete and archival filters** — applied to all active-record queries where the schema
   defines them.
8. **Error handling** — a global handler prevents stack traces, internal messages, database errors,
   file paths and storage keys from reaching responses.
9. **Upload handling** — where uploads exist, no untrusted writes to local disk.
10. **Dependency policy** — every new dependency is recorded in the project's dependency policy
    document, **with its approval state and the date it became available on the target
    environment**. Where the target environment requires dependencies to be approved and transferred
    before use, an unapproved dependency is a blocking finding on a branch targeting that
    environment, not a documentation note. Rationale: in a controlled environment, adding a
    dependency means a written request, an external scan, and a transfer window measured in days or
    weeks. A gate that treats it as a line in a document passes work that cannot be built where it
    is going. See spec 04, §10.6.
11. **Project-specific invariants** — a named section of project-owned rules is enforced without
    being asked for each time.

### 6.3 Completeness review (conditional, narrow)

**REQ-6.3.1** When the diff creates or modifies authentication, authorization, audit, redaction,
cryptography, or scoping code, the gate MUST additionally perform a **completeness review**.

**REQ-6.3.2** This review MUST be answered in prose, per control touched. A question that can be
answered by a checkmark has not been asked.

**REQ-6.3.3** The questions MUST include at minimum:

| # | Question | Defect class it catches |
|---|---|---|
| 1 | Does the guard recurse into nested structures, or inspect only top-level keys? | A redaction pass that checks the outer object and copies nested values by reference, writing sensitive data into a store that cannot be corrected |
| 2 | Is there a second write path to this same state, and is the guard on both? | A ceiling enforced on create but not update, making the restricted operation reachable in two steps |
| 3 | Which framework entry points does this hook *not* cover? **Enumerate them.** | Lifecycle hooks bound to a subset of operations — e.g. a read hook that does not fire for aggregates, or binds only the root entity so joined relations go unscoped |
| 4 | What does this verification *not* verify? **Enumerate it.** | A token check validating issuer and signature but not audience, algorithm, or token type — accepting a credential minted for a different client of the same realm |
| 5 | Name the production call site — file and line. | A control implemented and tested but never invoked |
| 6 | If it rejects input: is the schema strict, and is it actually mounted? | Validation schemas written, exported, and imported by nothing; or schemas passing unknown keys through |

**REQ-6.3.4** Questions 3 and 4 require the reviewer to *produce a list*. The enumeration is the
mechanism; a summary judgment defeats it.

**REQ-6.3.5** The trigger MUST stay narrow. Rationale: this review costs real reviewer effort.
Applied to every change it becomes a ritual, and a ritual answered by habit finds nothing. The
reference triggers on roughly one change in four.

**REQ-6.3.6** An unanswered question, or one answered with a bare pass, MUST be a blocking finding.

**Rationale for the whole section.** The base checklist asks whether a control *exists*. It has a
structural blind spot: a control can exist, be correctly implemented, be thoroughly tested, pass its
gate, and still have an edge its author never walked to. A yes/no checklist cannot surface those,
because the honest answer to "is scoping enforced?" is *yes*. This section catches incompleteness
rather than absence.

### 6.4 Conditional blocks

**REQ-6.4.1** The elevated-tier block (additive when the tier is elevated) MUST cover: validated
cryptographic modules only with named prohibited algorithms; response classification marking;
absence of unclassified external calls at runtime; audit logs written to append-only storage not
writable by the application process; documented cross-domain boundaries; and personnel clearance data
delegated to the identity provider rather than stored in the application database.

**REQ-6.4.2** The mobile-track block MUST cover: transport security minimums with no cleartext
permitted; no sensitive data on shared external storage; no sensitive data in platform logs;
credential storage in the platform keystore rather than preference files; authenticated backend
calls; certificate pinning evaluated with justified absence permitted; no embedded credentials or
endpoints in source; exported inter-process components minimized with per-component justification;
and a documented minimum platform version supporting the above.

**REQ-6.4.3** The on-prem provider block MUST *substitute for* the cloud infrastructure checks and
cover: transport termination and cipher minimums at the proxy layer; no plaintext secrets in
provisioned configuration; audit log destination and retention; encryption at rest for persistent
storage; firewall rules with no management ports exposed to the client network segment; current OS
and runtime packages; and documented deployment authorization.

**REQ-6.4.4** Each conditional check MUST cite the external standard that grounds it.

### 6.5 The verdict block

**REQ-6.5.1** Every gate run MUST end with a structured verdict recording at minimum: pass/fail,
the tier, the run number, the range reviewed, whether the diff was control-shaped, the control
manifest result, the completeness-review block count, the platform-surface report, the scan verdict
carried forward, open finding count, blocking finding count, and the identifiers of any tickets
opened.

**REQ-6.5.2** The verdict block format MUST be defined in exactly one place. Where it is duplicated
(for example, in both a reviewer procedure and a reference document), an automated check MUST assert
the copies match.

Rationale: in the reference, these two copies drifted. The rulebook instructed the gate to emit the
block from the reference document, and that copy was missing the scan line the same rulebook
required — so a gate following the instructions would have emitted a verdict with no scan result and
been correct to do so.

---

## 7. The control manifest subsystem

This is the mechanism that survives the diff-scoped gate's central blind spot.

### 7.1 The problem it solves

A diff-scoped review can establish that a control introduced in *this* change is correct. It
structurally cannot establish that a control introduced three epics ago is still wired, because
nothing in a diff-scoped review ever looks outside the change in flight. Controls decay silently:
a refactor removes the last call site, a file move breaks an import, an infrastructure artifact the
control depends on is deleted by a change in a different repository.

### 7.2 The manifest

**REQ-7.2.1** The project MUST maintain a declarative register of its security controls. Each entry
MUST carry at minimum: a stable identifier, a human description, the implementation location
(file and symbol), any required infrastructure artifact, a pattern matching its proving test, and
the implementation status defined in REQ-7.2.4.

**REQ-7.2.1a** The manifest MUST carry a **scope statement**, and that statement MUST be reproduced
in any evidence export:

> This manifest covers system-specific controls and the system-specific portion of hybrid controls.
> Fully inherited controls are implemented by the hosting platform, are tracked in the platform's
> system security plan, and are outside this harness's verification scope.

**Rationale.** Without it, an artifact named "control manifest" holding a dozen entries reads to an
assessor as a control set that is conspicuously short, rather than as a scoped one. The harness can
only verify what is in the tree, which is the right boundary; the failure is in not declaring it.
This is the cheapest finding in the entire analysis to fix and one of the most consequential,
because the misreading it prevents happens silently and in the reader's head.

**REQ-7.2.4** Each entry MUST declare an implementation status drawn from the vocabulary the
assessment process already uses:

| Status | Meaning | In the manifest |
|---|---|---|
| **system-specific** | The project implements the control entirely | Full entry, fully verified |
| **hybrid** | The project implements part; the platform implements the rest | Full entry for the project's portion, plus the counterpart field below |
| *inherited* | The platform implements it entirely | **Not present.** Tracked in the platform's plan, referenced by the scope statement |

**REQ-7.2.5** A hybrid entry MUST name its shared-responsibility counterpart: which platform
component provides the other portion, and what that portion is.

**Rationale.** The hybrid case is the one that produces the opposite error from the one REQ-7.2.1a
fixes. Boundary protection is the standard example: the platform provides the ingress gateway and
transport termination, while the project enforces authorization per route. If the project's half
sits in the manifest as an ordinary entry, the manifest implicitly claims the whole control — an
overstatement, in an artifact whose entire value is that its claims are verified. Naming the
counterpart costs one field and makes the entry exactly as strong as it should be.

**REQ-7.2.6** The harness MUST NOT verify, assert, or imply verification of an inherited control.

**Rationale.** It has no evidence for one and cannot acquire any. A row the harness cannot test,
sitting in a register whose claim is that every row is tested, weakens every other row in the file.

**REQ-7.2.2** The manifest is **project-owned**. It MUST be seeded once and never overwritten by
tooling updates.

**REQ-7.2.3** Call sites MUST NOT be recorded in the manifest. They MUST be recomputed from the tree
on every verification run.

**Rationale — this is the subtle and important one.** The manifest declares what *should* be true.
The verifier computes what *is* true and compares. If call sites were stored, the manifest could go
stale in precisely the direction that matters: a control loses its last call site, the stored value
still names one, and the check passes. Recomputation makes that failure impossible.

### 7.3 Verification

**REQ-7.3.1** For each populated entry, verification MUST confirm all of:

1. The implementation exists at the declared location.
2. A production call site exists — recomputed, non-zero, and excluding the definition line itself
   and test files.
3. Any declared required artifact is present.
4. A test matching the declared pattern exists.

**REQ-7.3.2** Call-site detection MUST recognize indirect invocation — a symbol passed by reference
to a framework registration rather than called directly — and MUST NOT count a mention in a comment.

**REQ-7.3.3** The verifier MUST distinguish three exit states: all entries resolve; at least one
entry fails; **the manifest exists but contains only template placeholders**.

**Rationale for the third state.** A freshly seeded manifest with no real entries verifies
successfully — there is nothing to fail. That is a false green of the purest kind: a compliance
artifact reporting success while declaring nothing. It MUST be distinguishable from a populated
manifest that passed.

### 7.4 Linkage to the gate

**REQ-7.4.1** A control-shaped diff with no corresponding manifest entry in the same change MUST be
a blocking finding.

**REQ-7.4.2** Every manifest entry MUST also be subject to mutation testing (§5.3).

Rationale: §7.3 proves the control is wired. §5.3 proves the tests depend on it. Both are needed;
neither implies the other.

### 7.5 Completeness — the question the manifest cannot currently answer

§7.3 verifies that every *declared* control is implemented, called, and tested. REQ-7.3.3 catches a
manifest holding only placeholders. Neither asserts that the manifest is **complete**, and a
manifest with a single genuine entry satisfies every requirement above.

REQ-7.4.1 closes this going forward — a control-shaped diff with no manifest entry is blocking. It
does nothing for code that predates adoption, which §9.3 establishes is the normal case.

**REQ-7.5.1** A probe MUST identify control-shaped code in the tree that has no corresponding
manifest entry, and MUST produce that list as a durable artifact.

**REQ-7.5.2** The probe MUST use the same control-shape detection as the completeness-review trigger
(REQ-6.3.1), applied to the tree rather than to a diff.

**Rationale.** The detection already exists and is already tuned; pointing it at a second target is
cheap, and using one definition means the two cannot drift into disagreeing about what a control is.

**REQ-7.5.3** Each undeclared control MUST be dispositioned: declared in the manifest, or explicitly
accepted as not-a-control with a written reason.

**REQ-7.5.4** The probe MUST NOT block. Its purpose is to convert an unbounded unknown into a finite
list, exactly as the never-reviewed inventory does (§9.3).

**Rationale for the whole section.** An assessor's question is never "are your declared controls
wired." It is "are these all of them." Without this probe the layer has no answer, and worse, it has
no way to know whether it has an answer — the manifest looks equally healthy whether it describes
every control in the system or one of forty. The probe does not prove completeness, which is not
provable; it makes incompleteness *visible*, which is the achievable version.

---

## 8. Standards citation subsystem

### 8.1 The problem

The reviewer's authority rests on its checks being grounded in real, current control references. In
the reference implementation, nothing had ever read a control identifier and asked whether it was
real. Three were wrong: a withdrawn control had been cited as the primary grounding for the
dependency check for four months; another withdrawn control sat in the baseline; a third carried a
different control's title. **A wrong citation is worse than an absent one, because it reads as
diligence.**

### 8.2 Storage model

**REQ-8.2.1** Control catalogues MUST be vendored as version-pinned structured data.

**REQ-8.2.2** Each catalogue MUST carry provenance metadata: source location, source content hash,
catalogue version, and retrieval timestamp.

**REQ-8.2.3** Entries MUST record at minimum: identifier, current status (active or withdrawn),
official title, and — for withdrawn entries — the identifiers that superseded them.

**REQ-8.2.4** Catalogues MUST NOT store full control text.

**Rationale, and a design point worth defending.** This is a lookup table, not a retrieval system.
There are no embeddings, no vector store, no semantic search, and nothing is retrieved at inference
time. The subsystem answers exactly one question — *does this identifier resolve to a real, current
control?* — deterministically. An accreditation needs a citation to resolve or the build to fail;
"the system probably found the right control" is not a property that can be handed to an assessor.
Storing full text would invite the temptation to build retrieval on top, which trades a deterministic
verdict for a probabilistic one in the one place determinism matters most.

### 8.3 Verification

**REQ-8.3.1** Every citation-shaped token in the governed document set MUST be resolved. Verification
MUST distinguish:

| Result | Disposition |
|---|---|
| Unknown identifier | **Fail** — typo, invented, or from another framework |
| Withdrawn identifier | **Fail**, naming its replacement |
| Superseded publication revision | **Report**, naming the current revision |
| Revision that was never published | **Fail**, listing what was published |
| Stale edition numbering (for ordered lists) | **Fail**, naming the identifier and the title it now carries |
| Identifier on a platform not in the index | **Report**, not fail, with a path to supply it |

**REQ-8.3.2** The governed document set MUST be explicitly enumerated, not inferred. Rationale: an
inferred set expands silently and starts failing on incidental mentions.

**REQ-8.3.3** An escape MUST exist for a deliberate mention of a withdrawn identifier (documenting
history).

**REQ-8.3.4** Prose that resembles an identifier but is not one MUST NOT be misread. Rationale: a
document-formatting reference or a standards number in running text will otherwise produce false
failures, and a check with false positives gets disabled.

### 8.4 Currency

**REQ-8.4.1** A separate command MUST fetch published sources and report whether the vendored pins
are current. This command is the *only* component permitted to reach the network.

**REQ-8.4.2** Adopting a newer catalogue version MUST be an explicit, reviewable action producing a
diff. It MUST NOT happen automatically.

**Rationale.** An accreditation is granted against a specific baseline revision. Silently adopting a
newer one changes what the project is being measured against without anyone deciding to.

**REQ-8.4.3** An offline mode MUST exist, and it MUST report that currency was **not checked**
rather than reporting current.

**Rationale.** This is the distinction that made "unverified" usable as a permanent resting state in
the first place. The offline mode must make the absence of verification visible, or it becomes a way
to claim currency without checking.

**REQ-8.4.4** A path MUST exist to supply a catalogue that cannot be redistributed (published behind
authentication, or carrying handling markings), by ingesting an operator-supplied copy.

**REQ-8.4.5** The ingest path MUST refuse a document carrying handling markings unless the operator
explicitly acknowledges. Rationale: the tool must not become the mechanism by which marked content
enters a repository that is not cleared for it.

---

## 9. Standing-state probes

Everything in §5–§8 is diff-scoped or artifact-scoped. Two probes exist specifically to see what a
diff-scoped review cannot.

### 9.1 Repository state snapshot

**REQ-9.1.1** A probe MUST capture a fixed set of measurements of the current head, independent of
any change under review, and diff them against the previous gate's snapshot.

**REQ-9.1.2** The measurement set MUST include at minimum: whether CI runs tests and linting;
deployment artifact counts; test suite result counts; control manifest result; and count of exported
symbols with no call site.

**REQ-9.1.3** Snapshots MUST be keyed by commit, so re-running at the same commit is idempotent.

**REQ-9.1.4** The probe MUST NOT remediate and MUST NOT block on its own. Blocking is a human
decision made on the delta.

**REQ-9.1.5** It MUST stay fast, and MUST NOT run the test suite itself — the result is passed in.
Rationale: a probe costing minutes gets skipped within a month, and a skipped probe is worth nothing.

### 9.2 Delta disposition

**REQ-9.2.1** Every delta the probe reports MUST receive a disposition: either a findings-register
entry (companion spec 02, §4) explaining why it is expected, or a ticket.

**REQ-9.2.2** Failing to disposition a delta MUST open a ticket rather than block. Rationale: an
unwritten record leaves nothing inert — it is a bookkeeping failure, not a safety failure.

**REQ-9.2.3** **Control decay is the exception and MUST block even when dispositioned.** Specifically:
CI ceasing to run tests or linting when it previously did; the control manifest regressing from pass
to fail; removal of an artifact that a manifest entry names as required.

**Rationale.** Each of these silently disarms a check that is supposed to be running. The general
rule is "a finding blocks only if skipping it would leave another check verifying nothing" — and
these three are exactly that case.

### 9.3 Never-reviewed inventory

**REQ-9.3.1** A probe MUST classify every source file as *seen by a gate* or *never seen*.

**REQ-9.3.2** The signal for *seen* MUST be evidence-based: the file entered the protected branch via
a merge whose identifier appears in the gate log.

**REQ-9.3.3** This probe gates nothing. Its purpose is to convert an unbounded unknown into a finite
list that can be burned down.

**REQ-9.3.4** "Seen once" MUST NOT be presented as a clean bill of health.

Rationale: most real projects adopt a harness partway through their life. A large part of the
codebase predates it and has never been read by any gate, and code merged from outside the harness
lands in the same blind spot. Legacy defects and new defects then sit side by side, indistinguishable
and unowned.

---

## 10. Mechanical checks

**REQ-10.1** The following MUST run on every push, in a single command shared with CI:

| Check | Fails on |
|---|---|
| Credential scan | Credential-shaped content in tracked files |
| Injection scan | String-built queries in application source |
| Reference integrity | A path cited in governed documents that does not resolve |
| Reviewer-document consistency | The duplicated verdict format diverging (§6.5.2) |
| Control manifest verification | §7.3 |
| Citation verification | §8.3 |
| Attack-surface diff | A previously-absent risky directive appearing in server configuration |
| Self-test suite | Any regression fixture failing |
| Coverage thresholds | §5.1 |
| Lint and type checking | Track-appropriate |
| Artifact binding | The image digest the gate blessed differs from the digest shipped (§4.9.4) |
| License policy | A dependency whose license is outside the project's declared policy |
| Harness self-scan | The harness's own dependencies and vendored data failing the same scan policy applied to the project |

**REQ-10.5** The license check MUST compare against a declared policy, not merely record licenses.
Rationale: spec 06 REQ-8.4 requires a generated license record. A record nothing evaluates is an
inventory, and license constraints are frequently a delivery requirement rather than a preference.

**REQ-10.6** The harness's own dependencies and vendored data MUST be subject to the same scan
policy the harness applies to projects.

**Rationale.** The harness pulls scanner images, vendors catalogues, and runs with elevated access
to the repository. Spec 05 specifies how it tests itself and nothing specifies how it scans itself.
A compliance instrument exempt from its own policy is an argument nobody wants to have with an
assessor.

**REQ-10.2** The credential scan MUST support an inline allow annotation, and MUST skip
example/template files and obvious placeholders. Rationale: a check with false positives is disabled
within a month.

**REQ-10.3** The credential scan MUST be reusable against the staged index, so a pre-commit hook can
use **this same definition** of a credential rather than a parallel pattern set that drifts.

**REQ-10.4** Checks that cannot apply to the current project shape MUST report *not applicable* and
MUST say what, if anything, covers that ground instead. (See §1.2 and the worked example in §13.2.)

---

## 11. Governance protocol

### 11.1 Scope

**REQ-11.1.1** A *governance change* is any change to the reviewer's rule set: the top-level rulebook,
the reviewing agent definitions, or any skill definition that alters gate behavior.

**REQ-11.1.2** This protocol is itself part of the governed set and MUST NOT be suspended, weakened,
or exempted by the change it governs.

### 11.2 The core rule

**REQ-11.2.1** For governance changes, **the accountable control is a human's line-by-line diff
review.** The automated gate is advisory.

**Rationale.** See §1.6. The reviewer reads its criteria from the file being changed. A weakening
edit is applied to the very rules that would have caught it. No amount of reviewer diligence fixes
this — it is structural.

### 11.3 Allowlist, not blocklist

**REQ-11.3.1** Sections an automated agent may edit MUST be an explicit allowlist. Everything not
named is human-authored only.

**REQ-11.3.2** Adding a zone to the allowlist is itself a governance change.

Rationale: a blocklist is a list of things somebody thought of. An allowlist fails closed.

### 11.4 Transcription, not authorship

**REQ-11.4.1** Within an allowed zone, an agent may only transcribe a decision approved elsewhere.
Every added line MUST cite an external, already-approved source.

**REQ-11.4.2** If no approved source exists, the edit stops and becomes a human decision.

### 11.5 Bounded surface, isolated commit

**REQ-11.5.1** A governance change MUST declare its exact file and section before implementation.

**REQ-11.5.2** Any change outside the declared surface MUST be a blocking finding, not a note.

**REQ-11.5.3** The change MUST land in its own commit, never bundled with feature work.

### 11.6 Review against the pre-change rules

**REQ-11.6.1** When reviewing a governance diff, the gate MUST evaluate against the rule set **as it
existed at the base commit**.

**Rationale.** Asking whether the amended rulebook passes its own amended rules is circular and
always answers yes.

### 11.7 Automated maintenance is append-only

**REQ-11.7.1** Where the system maintains a governed document automatically, automation MUST be
restricted to *appending* grounded entries to a designated data section. It MUST NOT rewrite prose,
reorder, or delete. Removal escalates to a human decision.

### 11.8 The changelog

**REQ-11.8.1** Every governance change MUST append one row recording: date, change identifier, file
and section touched, base and resulting commit, external grounding, and human sign-off.

**REQ-11.8.2** The row is mandatory **before** the commit.

**REQ-11.8.3** The sign-off field MUST record *what the human was shown*, not merely that approval
occurred.

**Rationale, learned the hard way.** A row reading "approved" is unfalsifiable a year later. A row
reading "approved after being shown these two hunks and the note that this row is retroactive" lets
a later reader judge whether the approval covered what actually changed. A corollary the reference
adopted as standing practice: **when presenting a governance change for approval, the literal text
being added must be shown in the request itself, not behind an expandable detail.**

---

## 12. Records and evidence

**REQ-12.1** Every gate run — **including re-runs** — MUST append a row to a persistent log
recording: date, unit of work, range, run number, finding count and identifiers, tickets opened,
verdict, and reviewer identity.

**REQ-12.2** A unit of work that required three rounds MUST show three rows.

**Rationale.** This is the single most valuable artifact the layer produces and the one most likely
to be trimmed by an implementer who sees repetition. An assessor's first question is not "did it
pass" — it is "what was the process, and what did it catch." A log showing only final passes
describes a process that never found anything, which is either false or an indictment.

**REQ-12.3** Findings MUST be tracked to disposition (§1.4), and finding counts per unit of work
SHOULD be reviewed for trend.

**REQ-12.4** Where an out-of-process change is knowingly accepted (an ungated merge), it MUST be
recorded in the **findings register** (companion spec 02, §4) rather than left implicit.

**REQ-12.6** **One name, one artifact.** The register defined in companion spec 02 §4 is called the
**findings register** throughout this package. Earlier drafts of these documents referred to the
same artifact as a *standing exceptions register* and as a *permanent record*; those names are
withdrawn. An implementer reading two documents in sequence and seeing two names will build two
files, and in a package whose own rule is that pointers must resolve, vocabulary drift is the first
thing to fix.

**REQ-12.5** An expedited lane MAY exist for urgent fixes, but it MUST still produce a log row and
MUST still require one human review. Its usage count SHOULD be reviewed at each retrospective.

---

## 13. Failure semantics — the honesty rules

This section collects the requirements that exist purely to prevent false greens. They are gathered
here because they are the layer's distinguishing characteristic, and because they are individually
easy to argue away.

### 13.1 Exit codes are assertions

**REQ-13.1.1** A zero exit MUST mean *the check ran against real input and found nothing*.

**REQ-13.1.2** A component that cannot perform its function MUST NOT exit zero, except where its
non-applicability is a structural property of the project shape (§13.2).

### 13.2 Non-applicability is stated, with its gap

**REQ-13.2.1** Where a check has nothing to run against because of the project's shape, it MUST say
*not applicable*, name the shape, and — critically — **state whether anything else covers that
ground**.

**Worked example from the reference.** An injection scanner reads one language family's source. On a
project in a different language it has nothing to read. The original wording was *skipped*, which
reads identically to a check that could have run and did not. The corrected output names the track,
explains what the check reads, and adds that persistence in the project's actual language is covered
by no check at all. Saying a check does not apply is only honest if it also says what is therefore
unguarded.

**REQ-13.2.2** A third state MUST be distinguished: *nothing to check yet*, for a project that has
not grown the relevant surface but may. Claiming non-applicability there is a different falsehood.

**REQ-13.2.3** The check suite MUST report **applicable, not-applicable and failed counts
separately**, as an aggregate, in its summary.

**REQ-13.2.4** A not-applicable proportion above a configured threshold MUST be a finding requiring
disposition. It MUST NOT block.

**Rationale, and this is a gap that §13.2.1 leaves open by being careful line by line.** Each
not-applicable line can be individually honest — naming the shape, naming what is unguarded — while
the aggregate quietly amounts to an assurance claim nobody made. A project shape where most checks
do not apply passes the entire suite truthfully, one line at a time, and the summary reads like a
full run.

The purpose of the threshold is not to block anything. It is to force the sentence *"this project
shape is covered by four checks, and here is what is therefore unguarded"* to be written down once,
by a person, where a reader will find it. That sentence is what an aggregate of honest lines fails
to produce on its own.

### 13.3 Assertions must be capable of failing

**REQ-13.3.1** Every assertion about an outcome MUST be specific enough that a wrong outcome fails it.

**Worked example from the reference.** A test asserting that a malware scanner "exits non-zero on
detection" passed when the scanner failed to start — a container-level failure produced a non-zero
exit, satisfying an assertion about detecting malware. The correct assertion names the exact exit
code meaning *detection*, and treats every other non-zero value as *the scanner fell over*, which is
a different result and must not read as success.

**REQ-13.3.2** Assertions about output MUST target the specific line that carries the claim, not the
whole transcript.

**Worked example.** An assertion that an overridden pass is marked *unverified* searched the entire
output for that word. An earlier warning line also contained it, so the assertion passed even when
the final verdict line read as an ordinary clean result. The corrected assertion reads the verdict
line alone.

### 13.4 Every check must have been seen to fail

**REQ-13.4.1** Every check MUST have an accompanying negative fixture: an input that makes it fail,
exercised as part of the self-test suite.

**REQ-13.4.2** A new check MUST NOT be accepted on the evidence that it passes. It MUST be
demonstrated failing against a deliberately broken input.

**Rationale.** This is §1.1 as an implementation rule. In the reference, applying it by mutation to
already-written tests found a test that passed for the wrong reason within its first hour of use.

### 13.5 Verification must be observed, not merely invoked

**REQ-13.5.1** Where an automated process runs a verification before an irreversible action, it MUST
gate on the verification's result, not merely invoke it.

**Rationale.** In the reference, a change was committed and pushed after its verification had already
failed, because the command sequence continued past a non-zero exit. The verification ran and was
ignored — which is worse than not running it, because the log shows diligence that did not occur.

---

## 14. Non-requirements

Stated explicitly so an implementer does not add them believing they were intended.

- **No semantic retrieval over standards text.** See §8.2.4.
- **No automatic remediation of scan findings.** Findings are routed to an owner; the fix is ordinary
  work subject to the ordinary gate.
- **No automated merge, approval, or verdict override, under any condition.**
- **No network access during verdict computation.** Only the currency command (§8.4.1).
- **No severity-based gate blocking.** See §4.6.1.
- **No scoring or weighting of findings.** A finding is blocking or it is not. Rationale: a weighted
  score is a mechanism for passing with known defects.

---

## 15. Suggested build order

Each stage is independently useful; none requires a later one.

| Stage | Build | Why first |
|---|---|---|
| 1 | Configuration model (§2) and the single check command (§3.1, §10) | Everything reads the config; the command is the spine |
| 2 | Honesty rules (§13) as a testing convention | Cheapest to adopt before there is code to retrofit |
| 3 | Records (§12) | Valueless retrofitted; a log with a gap is not a log |
| 4 | Control manifest + verification (§7) | Highest assurance per unit of effort |
| 5 | Mutation of controls (§5.3) | Requires §7's register to exist |
| 6 | Scan subsystem (§4) | Largest surface; most third-party dependency |
| 7 | Two-window gate + checklist (§3.4, §6) | Needs §4 and §7 to have something to report |
| 8 | Standards citations (§8) | Independent; can be built any time after §1 |
| 9 | Standing probes (§9) | Needs §12's log to compute "seen by a gate" |
| 10 | Governance protocol (§11) | Adopt as soon as the rule set stabilizes |
| 11 | Manifest completeness probe (§7.5) | Needs §7's manifest and §6.3's control-shape detection |
| 12 | Composition inventory and artifact binding (§4.9) | Needs §4's scan subsystem |
| 13 | Carried-finding aging and the alarm lifecycle (§4.10) | Needs §4.6's two verdicts and §12's records |

**A note on stage 2.** Adopting the honesty rules as a convention before writing checks is worth more
than any single check in this document. Every false green catalogued here was written by a competent
engineer who believed the check worked. The rules are not a warning about carelessness; they are a
countermeasure against a failure mode that looks exactly like success.

---

## Appendix A — The false-green catalogue

Seven concrete instances observed in the reference implementation. An implementation of this spec
should be able to state, for each, why it cannot occur.

| # | Mechanism | Presented as |
|---|---|---|
| 1 | Test accepted any non-zero exit as "detection"; scanner failed to start | Detection confirmed |
| 2 | Detection-data age unparseable; branch proceeded with a warning | No threats found |
| 3 | Image scanners referenced unresolved placeholder names, scanned nothing | Clean image scan |
| 4 | Tool-update mechanism seeded reviewer files once, never updated them | Configuration synchronized |
| 5 | Local-run command exited zero with no build and no runtime on one project shape | Environment healthy |
| 6 | Non-applicable checks reported *skipped*, identical to *checked, clean* | Full check suite passed |
| 7 | A consistency check read its input from a file that a refactor had emptied | Documents consistent |

Common signature: **exit zero with no work performed.** Not a wrong answer — *no* answer, wearing
a pass.

---

## Appendix B — Terms

| Term | Meaning here |
|---|---|
| **Range** | The set of commits under review; the unit a gate evaluates |
| **Control-shaped** | A change touching authentication, authorization, audit, redaction, cryptography, or scoping |
| **Blocking finding** | A finding that prevents the gate passing; no severity weighting exists |
| **Carried finding** | A finding with no available remediation, recorded as accepted risk |
| **Disposition** | The recorded decision about a finding or delta: a check, a checklist line, a ticket, or a permanent record entry |
| **Cold context** | An execution context containing the rules and the artifact, and nothing from construction |
| **False green** | Success reported by a component that performed no work |
