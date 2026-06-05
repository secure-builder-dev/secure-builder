# Secure Builder — Product Requirements Document

**Document type:** Engine specification (this describes the tool, not any app built with it)
**Owner:** C.J. Houle
**Status:** Draft v0.2 — sanitized / ownable build
**Last updated:** 2026-06-04

> **How to read this document.** Secure Builder is an engine. A PRD for an engine
> does not describe what one app does for a user — it describes what the engine
> *guarantees* about everything it produces. The word *guarantee* is the spine of
> this document. Every section below either states a guarantee or describes the
> machinery that enforces one. If something does neither, it is plumbing detail and
> does not belong here.

---

## 1. Problem and Purpose

### 1.1 The problem

Small, junior-staffed development teams are responsible for delivering and
sustaining multiple applications across several secure pipelines (IL4, IL6, and
restricted perimeter/edge environments). Each target network has a platform team
that owns the deployment pipeline and is the approval authority for production
release. Code that arrives at those pipelines unprepared generates long
remediation cycles: linting and static-analysis findings, dependency CVEs,
control-mapping gaps, and POA&M items that consume weeks of back-and-forth before
anything reaches an end user.

### 1.2 The purpose

Secure Builder is an AI-driven, multi-agent code generation engine that produces
application code which is **compliant, tested, and control-mapped from the first
line**, so that work arriving at a platform team's pipeline is as close to
release-ready as a development tool can make it. The intended outcome is a
dramatic reduction in pre-authorization remediation time — fewer CVEs and POA&M
items at intake, faster credential/namespace negotiation, and a clean evidence
trail the platform team can read directly. The engine is designed to support an
Army move toward continuous Authority to Operate (cATO).

### 1.3 What Secure Builder is NOT (non-goals — read this first)

- **It is not an ATO and does not grant authorization to operate.** The platform
  team for each target network remains the sole approval authority.
- **It is not a replacement for the platform team's pipeline or review.** It is a
  shift-left accelerator that runs *upstream* of that authority.
- **It is not a substitute for a senior security reviewer.** Its human gate keeps
  a person in the loop; it does not confer that person's judgment.
- **It does not deploy to or connect to secure networks.** It produces artifacts
  that are handed off through existing, authorized channels.

---

## 2. Core Guarantees

*This is the heart of the document and the original intellectual property of the
engine. Every other section exists to enforce one of these.*

1. **No self-approval.** No artifact produced by an AI agent is approved by an AI
   agent. Final approval is a human act. Self-approval is a protocol violation
   regardless of how correct the work is.
2. **No commit without a complete gate chain.** Nothing commits without, in order:
   Quality gate PASS, Security gate PASS, Manual security review CLEAR, and
   explicit human approval. No step may be skipped, reordered, or auto-approved. How
   this is *enforced* depends on `GATE_ENFORCEMENT` (§9): in `ci-enforced` mode the
   chain is a server-side merge wall — branch protection rejects any merge to the
   integration branch without passing CI gate checks and a matching gate-log entry,
   which an operator cannot bypass from their workstation; in `local-attested` mode
   (air-gapped, no remote CI) the chain rests on a local pre-commit hook plus the
   append-only audit trail and operator discipline — defense-in-depth, not an
   unbypassable wall. Either way, the downstream platform team re-runs its own checks
   (§6.1, §13).
3. **No implementation without a preceding failing test.** Every behavioral change —
   a feature or a bug fix — is produced by a two-commit TDD sequence: a test-only
   commit that demonstrably fails, then an implementation commit. (Non-code stories —
   docs, ADRs, pipeline config — are exempt by nature.) Absence of the prior
   failing-test commit on a code-bearing story is an automatic FAIL regardless of any
   agent's assertion.
4. **Every security check traces to controlling text from an authoritative corpus.**
   Each gate check maps to a specific control (NIST 800-53 Rev 5, DISA STIG, or other
   authoritative source). Sentinel retrieves the controlling text verbatim from a
   curated compliance corpus rather than paraphrasing it, so every citation is grounded
   in a source a reviewer can open. Retrieval grounds the *citation*; the *mapping
   judgment* — that a given check satisfies a given control — remains human-confirmed
   (see §4.4, §13). Confirmed mappings are cached in `CONTROLS-MAPPING.md` and reused, so
   a human ratifies each check-type's mapping once rather than every story. Mapping
   quality is bounded by the corpus's coverage and currency.
5. **No agent acts outside its declared lane.** Each agent has a single
   responsibility and a defined set of owned artifacts. Action outside that lane
   is a finding (application-layer treatment of OWASP LLM08, Excessive Agency).
   File-ownership is checked deterministically by diffing touched files against the
   agent's owned-artifact globs; semantic over-reach — e.g., a decision buried inside
   an allowed file — remains Sentinel's judgment (see §3.2).
6. **All evidence is append-only by protocol; git history is the tamper record.**
   Gate logs, the issue lifecycle ledger, and the ADR log are only ever appended to —
   corrections are new entries, never edits or deletions. These are tracked files, so
   the enforcement is not a write-protected store but the commit history: any rewrite
   is itself a recorded, attributable change a reviewer can see. Where a stronger
   guarantee is required (IL6 audit logs, AU-9(2)), a tamper-evident store is specified
   separately in §5.4 — the two are not the same thing.
7. **Sensitive infrastructure values never enter agent context.** Real account
   IDs, ARNs, secrets, and environment values are kept out of the agent's accessible
   workspace, and are never repeated or stored in tracked files; placeholders are used
   everywhere. Structural separation — keeping those values outside the repo the agent
   can see, not relying on ignore-files — is the primary control (see §11).
8. **No endpoint without negative authorization tests.** Every endpoint ships with
   tests proving it *rejects* the unauthenticated caller (401), the wrong-role caller
   (403), the cross-tenant caller (IDOR), and the malformed request (400) — not merely
   that it serves the authorized one. A passing happy-path test is not sufficient
   evidence an endpoint is safe.


---

## 3. Agent Manifest

All agents are custom personas layered on a base orchestration framework. Each
owns specific artifacts, operates within a defined lane, and cannot act outside
that lane (enforced at gate time — OWASP LLM08 compliance).

| Agent | Persona | Lane (single responsibility) | Owned Artifacts |
|---|---|---|---|
| John | Product Manager | PRD, epics, high-level story scoping | `docs/PRD.md`, story headers |
| Tori | Story Analyst | Story writing, refinement, gap analysis, story-vs-contract alignment | Story files |
| Bob | Scrum Master | Sprint dispatch, gate enforcement, sprint artifacts | `_bmad-output/planning-artifacts/`, `_bmad-output/NEXT_PROMPT.md` |
| Winston | Architect | ADR decisions, DB schema, API contract design | `docs/architecture/ADR-LOG.md`, `API_CONTRACT.md`, `DB_SCHEMA_v2.md` |
| Sally | UX Designer | UX/UI design — interaction patterns, component specs, accessibility, frontend design specs (web track) | `docs/UX-SPEC.md`, design-spec files |
| Amelia | Developer | TDD implementation — tests first, always | All `src/` implementation files |
| Murat | Test Architect | Test strategy, ATDD, coverage gates, quality gates | `docs/QUALITY_GATE.md` |
| Frank | DevSecOps | Pipeline, Helm, Terraform, image compliance, STIG | `docs/architecture/DEVSECOPS_SPEC.md`, `helm/`, Terraform |
| Sentinel | Security Gatekeeper | Security, architecture, dependency gate — binary verdicts only | `docs/architecture/DEPENDENCY_POLICY.md`, `_bmad-output/gate-log.md` |
| Paige | Tech Writer | User- and developer-facing documentation; doc curation and indexing | `README.md`, user/developer guides under `docs/` (excluding governance, architecture, and security docs owned by other lanes), doc index |

> **Murat** is a single Test Architect persona whose lane is delivered through a
> *cluster* of test-architecture skills (test design, ATDD mapping, coverage analysis,
> quality-gate evaluation, flaky-test detection, and related) rather than one
> monolithic skill — one agent, many skills.

### 3.1 Agent Activation

Agents are activated by invoking a per-agent skill; the persona persists through the
session until dismissed, and nested skill calls inherit the active persona.

On the current substrate, the planning, design, implementation, and documentation
personas (John, Winston, Sally, Amelia, Paige) are layered onto the base framework's
stock agent skills (`bmad-agent-pm`, `-architect`, `-ux-designer`, `-dev`,
`-tech-writer`). The orchestration and gatekeeper personas — Tori (story analyst),
Bob (scrum master), Murat (test architect), Frank (DevSecOps), and Sentinel (security
gatekeeper) — have no stock equivalent and are **custom skills built to the §7
scaffold**; building them is part of Phase 2 (see §14). Invocation names are an
implementation detail of the substrate, not a guarantee — the §10 orchestration spec
requires only that a named persona can be activated on demand.

### 3.2 Lane Boundary Enforcement

Sentinel enforces lane boundaries as a gate check on every story. If an agent took
actions outside its defined scope — a developer making ADR decisions, a scrum
master writing code — Sentinel flags it as a finding. This is the application-layer
implementation of OWASP LLM08 (Excessive Agency).

Owned-artifact sets are expressed as **file-path globs** (the Owned Artifacts column
in §3 is the basis). At gate time Sentinel diffs the story's touched files against the
acting agent's glob set; any file changed outside that set is a lane-boundary finding.
This makes Guarantee #5 *partially* machine-checkable: the **file-ownership** dimension
is a deterministic `git diff`-vs-glob check, while the **semantic** dimension — e.g., a
developer burying an architectural decision inside an allowed `src/` file — still
requires Sentinel's judgment. State the split honestly; do not claim full automation.

---

## 4. Workflow — Story Lifecycle and Gate Sequence

Every story executes this sequence exactly. No step may be skipped, reordered, or
auto-approved.

1. **Dispatch.** Bob routes the story to the correct first agent per the routing
   table (§4.1).
2. **Implementation.** The assigned agent implements. For Amelia, the TDD
   two-commit sequence is mandatory (test-only failing commit precedes
   implementation commit).
3. **Quality gate (Murat).** FAIL → back to implementer for remediation, re-run.
   PASS → proceed.
4. **Security gate (Sentinel).** FAIL → agent remediates, re-run. PASS → proceed.
5. **Manual security review (human + the AI assistant).** Findings → back to implementer with
   remediation notes, then full re-gate. CLEAR → proceed.
6. **Human approval (hard stop).** Explicit "approved" required. Approval → commit.
7. **Handoff.** Bob dispatches the next story and writes the handoff prompt (§4.3).

**Nothing commits without: Quality PASS + Security PASS + Manual CLEAR + explicit
human approval.** The AI model cannot approve its own work; self-approval is a
protocol violation regardless of how correct the underlying work is.

### 4.1 Agent routing

| Story Type | First Agent | Then |
|---|---|---|
| New story writing | John | Tori (refinement) |
| Story refinement / gap analysis | Tori | Bob (dispatch) |
| Schema change / new ADR | Winston | Amelia |
| UI/frontend feature with design surface | Sally | Amelia → Murat → Sentinel |
| Feature / API endpoint | Amelia | Murat → Sentinel |
| DevSecOps / pipeline / Helm | Frank | Sentinel |
| New dependency | Sentinel (DP review) | Amelia |
| All stories, post-implementation | Murat | Sentinel → manual review |

### 4.2 Mandatory Read Protocol

Every agent receives a mandatory read list before starting work. Skipping a
mandatory read is a gate failure at Murat or Sentinel.

| Agent | Mandatory Reads |
|---|---|
| John | `docs/STORY_TEMPLATE.md`, `docs/PRD.md` |
| Tori | Story file(s), `STORY_TEMPLATE.md`, `PRD.md`, `API_CONTRACT.md`, `DB_SCHEMA_v2.md`, `DEPENDENCY_POLICY.md` |
| Amelia | Story file, `API_CONTRACT.md`, `DB_SCHEMA_v2.md`, `DEPENDENCY_POLICY.md` |
| Murat | Story file, `QUALITY_GATE.md` |
| Sentinel | `CLAUDE.md` (always in context), `DEPENDENCY_POLICY.md` |
| Frank | `DEVSECOPS_SPEC.md`, `DEPENDENCY_POLICY.md`, provider-specific STIG checklist |
| Winston | `ADR-LOG.md`, `DB_SCHEMA_v2.md`, `API_CONTRACT.md` |
| Sally | Story file, `PRD.md`, `API_CONTRACT.md` |
| Paige | `PRD.md`, the source/story files being documented, existing doc index |

**Verification status — human-attested, not machine-verified (stated honestly).**
There is no reliable way to prove an agent *read and used* a file versus the file
merely being present in its context window. An agent can also assert it read
something it did not meaningfully process. Therefore the mandatory-read gate is
**human-attested**: the operator confirms the required artifacts were supplied to the
agent before work began, and gate reviewers (Murat/Sentinel) treat an obvious
contradiction with a mandatory source (e.g., output that conflicts with
`API_CONTRACT.md`) as evidence the read did not occur. This is a *negative* check —
it can catch a missed read by its consequences, but it cannot positively verify one.
Do not describe this gate as "verified." See the residual risk in §13.

### 4.3 Sprint Continuity — Handoff Prompts

Bob writes a clipboard-ready handoff prompt after every commit. The next session
has no memory of the current one, so the handoff must be fully self-contained. Two
handoff streams exist:

- `_bmad-output/NEXT_PROMPT.md` — written after each **S-prefix (story)** commit.
- `_bmad-output/NEXT_PROMPT_FRAMEWORK.md` — written after each **F-prefix
  (framework)** commit.

> Note for Secure Builder's own development: building the engine itself is
> framework work and uses the F-prefix track.

### 4.4 Gate verification (how each gate is *proven*, not just claimed)

> A gate that cannot be falsified is theater. For each gate, state the
> machine-checkable evidence. Where a gate is necessarily human-attested, mark it
> so honestly.

| Gate | Verified by | Machine-checkable? |
|---|---|---|
| TDD two-commit | Test-only commit precedes impl commit in `git log`; no `it.skip`/`test.skip`/`xit`/`xtest`; no DB mocks (integration tests hit real PostgreSQL via testcontainers) | Yes |
| Coverage thresholds | Coverage report vs. configured minimums, measured on the story diff (not project average) | Yes |
| Lint / typecheck / no skipped tests | `npm run lint` exits 0; `npm run typecheck` exits 0; `npm test` exits 0; no `console.log`/`console.error`/debug in production paths | Yes |
| Flaky-test check | Non-deterministic tests pass 3 consecutive runs | Yes |
| ATDD | Every acceptance criterion maps by name to ≥1 test | Partially |
| Control mapping | Each check links to cited control text | Partially — mapping correctness is human-confirmed |
| Mandatory reads | Operator attests required artifacts were supplied before work began; reviewers treat output that contradicts a mandatory source as evidence of a missed read (negative check only — see §4.2) | No — human-attested by design |
| Manual security review | Human attestation against §6 contract | No — human-attested by design |

> **On the "Yes" rows:** these are deterministic for their *named* patterns — git-log
> ordering, exit codes, coverage numbers, and the listed skip annotations
> (`it.skip`/`xit`/etc.). Two sub-checks are heuristic, not exhaustive: "no DB mocks"
> relies on import/mock-pattern detection, and skip-detection catches the named
> annotations but not a test trivially neutered without them (e.g.,
> `expect(true).toBe(true)`). The manual gate (§5.5, §6) is the backstop for what the
> heuristics miss.

---

## 5. Testing Strategy

### 5.1 TDD — enforced, not preferred (Amelia's lane)

TDD is enforced by a mandatory two-commit sequence. Amelia's verbal assertion of
compliance is not accepted; Murat requires verifiable git artifacts.

- **Red phase (commit 1):** write all test files for the story's acceptance
  criteria; run tests — they MUST fail (passing-before-implementation tests are
  vacuous); paste first 20–30 lines of failures into the story file under
  `### TDD Red-Phase Evidence`; commit test files only (`[S-XXX/tests] failing
  tests for <description>`).
- **Green phase (commit 2):** write implementation; all tests MUST pass; commit
  implementation files only (`[S-XXX/impl] implementation for <description>`).
- If no test-only commit predates the implementation commit in `git log`, Murat
  returns TDD FAIL regardless of any agent assertion.

### 5.2 Quality Gate — Murat's criteria (`docs/QUALITY_GATE.md`)

Runs after Amelia, before Sentinel. Binary — PASS or FAIL. No partial credit.

- **TDD compliance:** two-commit sequence in `git log`; red-phase evidence in story
  file; no skipped tests; no DB mocks.
- **Coverage thresholds (minimum line coverage, measured on story diff):**

  | Layer | Minimum |
  |---|---|
  | Service layer | 80% |
  | Repository layer | 80% |
  | Route handlers | 70% |
  | Middleware | 80% |

- **Negative test coverage (every endpoint story):** 401 (no token), 403 (valid
  token, wrong role), IDOR (user A cannot reach user B's resource), invalid-input
  (malformed/missing/out-of-range → 400), conflict (uniqueness/mutual-exclusivity
  under concurrent/duplicate requests).
- **ATDD compliance:** every acceptance criterion maps by name to ≥1 test;
  untested ACs block PASS.
- **CI quality stage:** `npm run lint` = 0; `npm run typecheck` = 0; `npm test` = 0
  with no skipped tests; no debug statements in production paths.
- **Flaky-test check:** non-deterministic tests pass 3 consecutive runs.

**Murat Verdict Format:** QUALITY GATE VERDICT [PASS/FAIL]; TDD compliance; per-layer
coverage with PASS/FAIL; negative tests present; ATDD [x/x ACs covered]; CI stage;
flaky check [PASS/FAIL/N/A]; open findings count; blocking findings count.

### 5.3 Android Track Quality Gate

When `APP_TRACK=android`, additional checks before Murat issues PASS: ktlint zero
violations; Detekt zero `error`-severity issues; JUnit 5 coverage meets the same
thresholds as web; TDD two-commit sequence with the same red-phase JUnit failure
requirement (both commit hashes required in the gate record).

### 5.4 Security Gate — Sentinel's checklist (`CLAUDE.md` / `CONTROLS-MAPPING.md`)

Runs after Murat. Every gate check traces to a NIST SP 800-53 Rev 5 control ID in
`CONTROLS-MAPPING.md`. Binary — PASS or FAIL. No partial credit, no deferred
findings. Checks activate conditionally on the initialization variables (§9).

**IL4 Baseline Checks (always active)** — examples, each mapped to a control:
no hardcoded secrets (IA-5, CM-6); all endpoints require valid Keycloak token
(IA-2, AC-3); auth middleware registered before route handlers (AC-3, SA-8);
negative auth test required (CA-2, SA-11); RBAC scoping correct per role lanes
(AC-2, AC-3, AC-6); negative RBAC tests / IDOR (AC-3, AC-4); last-admin guard at
API layer (AC-2, AC-5); SQL injection prevented — parameterized queries only
(SI-10); query-view not base-table reads (AC-3, SA-8); mutations via dedicated
PATCH endpoints (CM-5, AC-3); `SELECT FOR UPDATE` on concurrent-sensitive endpoints
(AC-3, SI-10); soft-delete/archive filters on active-record queries (AC-3, SI-12);
computed columns never written by app code (CM-5, SA-8); custom error handler — no
stack traces in responses (SI-11); file uploads use memory storage (SC-28, CM-6);
API-proxied downloads, no presigned S3 URLs (AC-3, SC-8); no server-side token
storage or session middleware (IA-5, SC-23); all new dependencies in approved list
(SA-12, CM-3, SR-3).

**IL6 Additional Checks (active when `SECURITY_TIER=IL6`):** FIPS 140-3 validated
crypto only (IA-7, SC-13); classification banner header on all API responses
(SC-16); no unclassified external calls at runtime (SC-7(8)); audit logs to
tamper-evident append-only store (AU-9(2)); CDS integration points documented and
not bypassed (SC-16(1)); clearance level not stored in app DB (IA-4, AC-2); FIPS
140-3 module list verified (SC-13, IA-7).

**Android Track Checks (active when `APP_TRACK=android`):** TLS 1.2 minimum (DISA
Mobile STIG); no sensitive data to external storage (NIST SP 800-124 Rev 2); no
sensitive data in logcat (DISA Mobile STIG); auth token in Android KeyStore (NIST
SP 800-163 Rev 1); `Authorization: Bearer` header on API calls (DISA Mobile STIG);
certificate pinning evaluated and documented (NIST SP 800-163 Rev 1); no hardcoded
credentials or base URLs (DISA Mobile STIG); exported components minimized and
justified (DISA Mobile STIG); `minSdkVersion` documented and justified (DISA Mobile
STIG); ATAK plugin manifest minimum version ≥ 5.6 when `APP_TYPE=atak` (TAK SDK).

**Tactical Provider Checks (active when `PROVIDER=tactical`):** TLS termination
documented at reverse-proxy layer (ADR-023); no plaintext secrets in provisioning
scripts/config (IA-5); audit log destination satisfies 365-day retention (AU-11);
data-at-rest encryption documented, LUKS or equivalent (SC-28); firewall rules
documented, only required ports open (SC-7); OS and runtime packages current
(SI-2); deployment authorization documented (CA-6).

**Sentinel Verdict Format:** GATE VERDICT [PASS/FAIL] | SECURITY_TIER [IL4/IL6];
open findings count; blocking findings count.

### 5.5 Manual Security Review (Step 5)

After Sentinel PASS, the human and the AI assistant conduct a manual review targeting
logic-layer vulnerabilities automated checklists cannot detect (authorization
logic, business-rule bypass, multi-step attack chains, IDOR, privilege
escalation). If no logic flaws are found, the review is noted CLEAR in the story
record. Any findings return the story to Amelia with remediation notes, then back
to Sentinel for a full re-gate. (Full contract in §6.)

### 5.6 Dependency Vulnerability Management

Owned by Sentinel. Reference: `docs/architecture/DEPENDENCY_POLICY.md`.

| Severity | Action | Timeline |
|---|---|---|
| Critical | Block — do not ship; update/replace immediately; initiate POA&M if no fix | 0 days |
| High | Block — update/replace before merge; POA&M within 24h if no fix | 24 hours |
| Medium | Flag — document in PR; update at next maintenance cycle | Next sprint |
| Low | Log — non-blocking | Quarterly review |

`npm audit` runs in the `quality:lint` CI stage (web track). On the Android track the
equivalent supply-chain scan runs in the same stage — OWASP Dependency-Check (or an
equivalent SCA) against the resolved Gradle dependency graph — applying the same
severity matrix and the same block-on-critical/high rule. PRs with unresolved
critical/high findings that are not POA&M-allowlisted are blocked from merge,
regardless of track.

**License Policy (IL4):** MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, CC0-1.0
approved. GPL-2.0, GPL-3.0, AGPL-3.0 prohibited. LGPL requires review. No unlicensed
packages.

---

## 6. Human-in-the-Loop Contract

> This is the load-bearing wall of the entire engine. It is specified, not assumed.
> Written honestly, this is also the section that protects you when you brief
> leadership or a platform team.

### 6.1 What the human is

**Operating mode (stated plainly).** Secure Builder is operated by a small,
junior-staffed development team that builds applications for deployment to an
external platform team on one of three secure networks. That external platform team
is the final approval authority; we are not. The tool is team-owned but **driven by a
single operator per session** — so within any one story's lifecycle the operator who
implements is, by default, the same human who approves. The engine therefore does
**not** provide separation of duties internally at all; the four-gate structure is a
structured self-check, not separation of duties. The genuine separation of duties in this model is
the external platform team's independent review, which runs downstream of everything
this engine produces. Secure Builder is explicitly a pre-flight accelerator upstream
of that authority — its purpose is to reduce the remediation back-and-forth with the
platform/DevOps team and to streamline movement toward continuous ATO (cATO).

Where a story is security-sensitive (auth, RBAC, new endpoints, data-boundary
changes) and a second qualified person is available, the approver *should* be someone
other than the implementer. When that is not possible, the limitation is recorded as
a known risk (§13), not papered over.

### 6.2 What the human attests to at the manual gate

For each story, the human confirms — by typing answers, not checking boxes — that
they personally evaluated:

- **Authorization logic:** can a user reach data or actions outside their role via
  an unexpected call sequence?
- **Business-rule bypass:** can any acceptance criterion be satisfied in a way that
  violates a PRD "SHALL NOT" constraint?
- **Multi-step attack chains:** does a sequence of individually valid calls produce
  an unauthorized state?
- **IDOR:** are all resource lookups scoped to the authenticated user's ownership
  before returning data?
- **Privilege escalation:** can any endpoint or combination let a lower-privileged
  role gain higher-privileged capability?

For security-sensitive stories, the contract requires the human to **name the
specific endpoints** touched and state, in their own words, *who can call each one
and what stops everyone else.*

### 6.3 Anti-rubber-stamp measures

- The review prompt names concrete endpoints/resources from the diff; it does not
  present a generic checklist.
- The human types findings or an explicit "CLEAR" with reasoning; a bare approval
  is not accepted for security-sensitive stories.
- The recorded approval states *what was reviewed*, so the audit trail never
  asserts more diligence than actually occurred.

### 6.4 What the approval evidences (honesty clause)

The gate log records human approval as evidence of a human review **of the depth
defined in §6.2.** It does not assert senior-level security sign-off unless a
qualified senior reviewer performed it. In this team's context, "approved" means
**one developer's structured self-check against the §6.2 contract — not senior
security sign-off and not separation of duties.** A downstream platform-team
assessor should read it as exactly that: a documented pre-flight review by the
implementing team, performed before handoff, with the call sequence and endpoint
reasoning recorded. It is an input to the platform team's independent review, never a
substitute for it.

---

## 7. Custom Agent Builder

New domain-specific agents are built from a template scaffold in
`.github/skills/bmad-agent-builder/assets/`:

| Template | Purpose |
|---|---|
| `BOND-template.md` | Agent's working relationship with the team |
| `CAPABILITIES-template.md` | What the agent can and cannot do |
| `CREED-template.md` | Agent principles and non-negotiables |
| `INDEX-template.md` | Agent skill index |
| `MEMORY-template.md` | Session memory structure |
| `PERSONA-template.md` | Identity, voice, communication style |
| `PULSE-template.md` | Agent health/state tracking |
| `SKILL-template.md` | Base skill scaffold |
| `SKILL-template-bootloader.md` | Activation bootloader |

To create a new agent: copy the relevant templates, fill in the persona, define
owned artifacts and lane boundaries, and place in
`.github/skills/<agent-name>/SKILL.md`.

> This template system is a Track B reproduction target: when you build your own
> orchestration layer (§10), this scaffold is part of what you are rebuilding.

---

## 8. Audit and Evidence Artifacts

Three documents form the audit backbone, answering the questions an ATO assessor,
a security reviewer, or a new team member will ask: *what security decisions were
made and why; what was tested and what did it find; which code-level checks satisfy
which federal controls.*

### 8.1 Gate Log — `_bmad-output/gate-log.md`

Append-only record of every story that passed the full gate sequence. RMF evidence
artifact feeding the SSP under CA-2 (Control Assessments) and SA-11 (Developer
Testing).

- **Quick Ledger:** one row per story — Date | Story | Murat | Sentinel | Manual
  Security | Human | Commit.
- **Detailed Ledger:** full verdict tuple (Murat/Sentinel/Manual/Human), blocking
  vs. non-blocking finding counts, pointer to the story's `## Gate Results`
  section, a concrete risk note (what the finding was and why it matters), and an
  explicit follow-up owner when anything is left open.
- **Issue Lifecycle Ledger:** every non-zero finding gets an Issue ID
  (`GL-YYYY-MM-DD-###`) and a permanent lifecycle: `DETECTED` (gate where found), then
  exactly one terminal event — `REMEDIATED` (gate where fix verified) **or** `ACCEPTED`
  (documented carry-forward / POA&M, recording the accepting human and the rationale).
  A finding is never closed by deletion; an `ACCEPTED` finding later fixed gains an
  additional `REMEDIATED` event. Findings are never deleted or rewritten; lifecycle
  history is permanent.
- A story does not appear in the log until it has passed all four gates. Stories in
  progress have no entries.

**Verdict vocabulary (Quick Ledger):** Murat PASS = coverage met, TDD two-commit
verified, no skipped tests. Sentinel PASS (0 findings) = all gate checks clear.
Sentinel PASS (1 non-blocking) = passed with documented carry-forward (see Issue
Lifecycle Ledger). Sentinel PASS (1 remediated) = blocking finding caught and fixed
in-session before final verdict. Manual CLEAR = logic-layer review found no auth
bypass, IDOR, privilege escalation, or business-rule bypass. Human APPROVED =
explicit "approved" in conversation — the only thing that unlocks a commit.

**Update protocol:** after every commit, Bob appends one Quick Ledger row, one
Detailed Ledger row, a `DETECTED` row for any new finding, and the matching terminal
row when a prior finding closes — `REMEDIATED` if fixed, `ACCEPTED` if carried forward
as documented risk (never edit the `DETECTED` row). Append-only; do not rewrite,
delete, or retroactively edit. Corrections are new entries.

### 8.2 ADR Log — `docs/architecture/ADR-LOG.md`

A running record of every architectural decision: what was decided, what was
rejected, and why. Major process violations or security incidents get a prose
incident narrative (what happened, how discovered, what was rolled back or
remediated, who authorized it).

### 8.3 Controls Mapping — `docs/security/controls/CONTROLS-MAPPING.md`

Every Sentinel gate check mapped to its NIST 800-53 Rev 5 control ID — the ATO
cross-reference and SSP implementing-mechanism reference. Mappings cite controlling
text (Guarantee #4).

### 8.4 Document Reference — Engine Governance

**Core governance documents:** `CLAUDE.md` (engine constitution — all agent rules,
gate sequences, routing, commit protocol); `docs/PRD.md`; `docs/STORY_TEMPLATE.md`;
`docs/DEFINITION_OF_DONE.md`; `docs/QUALITY_GATE.md`;
`docs/agent-usage-guidelines.md`; `docs/agent-cve-poam-guidelines.md`.

**Architecture documents:** `ADR-LOG.md`; `API_CONTRACT.md`; `DB_SCHEMA_v2.md`;
`DEPENDENCY_POLICY.md`; `DEVSECOPS_SPEC.md`; `sentinel-gate-log.md`.

**Security documents:** `docs/security/README.md` (two-layer overview, ADR-020/022/
023); `controls/IL4-baseline.md`; `controls/IL6-delta.md`; `controls/CONTROLS-
MAPPING.md`; `controls/CDS-guidance.md`; provider implementation + STIG-checklist
files under `providers/{aws,azure,android,tactical}/`.

**Sprint output artifacts** (all in `_bmad-output/`): `gate-log.md` (Bob, after
Sentinel PASS + human approval); `NEXT_PROMPT.md` (Bob, after each S-prefix commit);
`NEXT_PROMPT_FRAMEWORK.md` (Bob, after each F-prefix commit);
`planning-artifacts/` (Bob, John — epics, sprint plan, retrospectives).

---

## 9. Configuration / Initialization Variables

Set once at clone time via a guided decision tree. These are design-time constants,
not runtime flags.

| Variable | Values | Description |
|---|---|---|
| `APP_TRACK` | `web` \| `android` | Primary stack. `web` = React + backend API + PostgreSQL, containerized, Kubernetes. `android` = Kotlin/MVVM native. |
| `SECURITY_TIER` | `IL4` \| `IL6` | Impact level. `IL4` = NIST 800-53 Rev 5 Moderate + DoD CC SRG v1r4 (CUI). `IL6` = High baseline additions (SECRET; classified network required). Android always IL6. |
| `PROVIDER` | `aws` \| `azure` \| `tactical` | Deployment target. `tactical` = team-owned classified perimeter network, Android-only; no managed cloud services. |
| `APP_TYPE` | `native` \| `atak` | Android track only. `native` = standalone APK/MDM. `atak` = TAK SDK plugin, WatchTower distribution. |
| `GATE_ENFORCEMENT` | `ci-enforced` \| `local-attested` | How the §2 gate chain is enforced. `ci-enforced` = server-side branch protection + required CI status checks — a true merge wall (requires a Git remote with CI). `local-attested` = local pre-commit hook + append-only audit + operator discipline, for air-gapped/offline targets with no remote CI. Determines the honest strength of Guarantee #2 (see §13). |

**Decision tree:** Web → impact level (IL4/IL6) → cloud provider (aws/azure).
Android → `SECURITY_TIER=IL6` (always), `PROVIDER=tactical` (always), app type
(native/atak). All tracks → gate enforcement (`ci-enforced` where a remote CI exists,
`local-attested` for air-gapped targets).

---

## 10. Orchestration Requirements (substrate-agnostic)

> Deliberately written without naming any framework. It is the spec the current
> substrate satisfies *and* the spec your own future engine must satisfy. Writing
> it this way makes the eventual "100% mine" port a known target instead of a blank
> page, and documents which behaviors are yours versus the framework's.

The orchestration layer must:

- **Activate personas.** Load a named agent persona (identity, lane, capabilities,
  owned artifacts) on demand via a slash-command-style invocation and keep it
  active across a session until dismissed; nested skill calls inherit the persona.
- **Provide a skill-file format** (`SKILL.md`) defining agent personas,
  capabilities, and owned artifacts, plus an activation bootloader pattern.
- **Provide the agent-builder template scaffold** (§7) for creating new agents.
- **Enforce lanes.** Make an agent's owned-artifact set and scope available at gate
  time so out-of-lane actions can be detected and flagged (OWASP LLM08).
- **Pass artifacts between agents.** Hand story files, gate results, and handoff
  prompts from one agent to the next deterministically.
- **Sequence gates.** Execute the §4 lifecycle in fixed order with no skip path,
  routing FAIL/CLEAR/PASS outcomes per the rules.
- **Persist session state and handoff.** Produce fully self-contained handoff
  artifacts (S-prefix and F-prefix streams) so a fresh session with no memory of
  the prior one can continue.
- **Enforce mandatory-read lists per agent** before work begins (see §4.2 for the
  honesty caveat on verification).
- **Provide core workflow skills:** sprint planning, story creation, retrospectives,
  brainstorming, code review, gap analysis, PRD creation/validation,
  implementation-readiness checks.

### 10.1 What the current substrate provides (the Track-B rebuild inventory)

The design in this document — the guarantees (§2), the gate sequence (§4), the agent
lanes and their content (§3), the control mappings (§8.3) — is **yours**. What the
current substrate (an agent runtime plus a skill/persona framework layered on it)
provides for free is the *plumbing* underneath. Track B replaces that plumbing without
changing the design. This is the honest inventory of what would have to be rebuilt or
adopted, ordered from heaviest to lightest. Treat it as a **living list** — add to it
every time you notice the substrate doing something for you.

**Tier 1 — the agent runtime (heaviest; adopt, don't hand-build).** The model
conversation loop (API calls, streaming, retries), tool-call dispatch, the tool suite
agents rely on (file read/write/edit, search, shell/git execution), context-window
management, and the permission/safety layer. *Scoping note:* you almost certainly do
**not** rebuild this from zero — you adopt an agent SDK that provides the loop + tools
and build only the layers below on top. Rebuilding a coding agent from scratch is not
Track B; it would sink it.

**Tier 2 — the skill/persona system (the real Track-B work).** Skill discovery and
invocation routing (name → skill definition), the skill-file format and activation
bootloader, persona persistence across a session, and persona inheritance into nested
skill calls. This is the layer that makes §3 and §10's persona requirements work, and
it's the layer most worth owning.

**Tier 3 — the workflow-skill library (broad but mechanical).** The prebuilt workflow
skills your agents compose — sprint planning, story creation, retrospectives,
brainstorming, code review, gap analysis, PRD/architecture/epics creation,
implementation-readiness checks, project documentation. Each is replaceable
individually; the cost is breadth, not depth. The agent-builder scaffold (§7) lives
here too.

**Tier 4 — state & continuity (a gap you already work around).** The substrate does
**not** persist session state, which is *why* the handoff-prompt streams (§4.3) exist —
they are your workaround for a framework limitation, not a feature you'd want to keep.
A Track-B orchestrator you own could persist real run state and **retire the
handoff-prompt dance entirely.** Flag this as an upgrade opportunity, not just a
rebuild.

**Tier 5 — integration surface (lightest).** External-tool/MCP connections and the
IDE/CLI/terminal integration. Adopt or stub as needed.

> **Sequencing reminder (Track B is gated on Track A).** None of this is built until
> the design is provably correct on the current substrate (§14). Debugging a novel
> design and a novel runtime at the same time is out of scope by deliberate choice.

---

## 11. AI Agent Security Rules

The following rules apply in every session, regardless of task. They are defined in
`CLAUDE.md` and cannot be overridden by story instructions.

- Never read, summarize, or reference `helm/values-dev.yaml`,
  `helm/values-prod.yaml`, `helm/values-staging.yaml`, or any `*.tfvars` file.
- Never repeat or confirm AWS account IDs, ARNs, security group IDs, RDS endpoints,
  S3 bucket names, or Keycloak client secrets.
- Never suggest storing real infrastructure values in any tracked file — always use
  placeholders (`<ACCOUNT_ID>`, `<CERT_ARN>`).
- Do not open or read POA&M files, Anchore scan results, or vulnerability reports.
- **Structural separation is the primary control** for keeping sensitive values out
  of agent context — not `.copilotignore` or workspace settings (which are
  supplementary and agent-specific only).

See `docs/agent-usage-guidelines.md` for the full guide applicable to all AI coding
agents (Copilot, Claude Code, and others) on IL4/classified projects.

---

## 12. Security Framework and Compliance Reference

### 12.1 Two-layer security architecture

Defined in `docs/security/README.md` (ADR-020, extended by ADR-022, ADR-023).

- **Layer 1 — Cloud-Agnostic Control Baseline** (`docs/security/controls/`): defines
  *what* must be controlled, independent of provider. The engine's application of
  NIST 800-53 to the code layer.
- **Layer 2 — Provider-Specific Implementation** (`docs/security/providers/`): maps
  Layer 1 controls to *how* they are satisfied on each provider (`aws`, `azure`,
  `tactical`).

### 12.2 Impact Level Ceiling by Provider

| Provider | Max Impact Level | Authorization Basis |
|---|---|---|
| AWS GovCloud (`us-gov-east-1`) | IL4 | FedRAMP High P-ATO (inherited) |
| AWS C2S / SC2S | IL6 | NSS classified cloud authorization |
| Azure Government | IL4 | FedRAMP High (inherited) |
| Azure Government Secret | IL5 (ceiling — Azure does not reach IL6 under DoD CC SRG) — **not a current deployment target; IL5 is not represented in §9's `SECURITY_TIER` by design. Add the tier if/when IL5 deployment is adopted.** | DoD IL5 PA |
| Tactical (classified perimeter network) | IL6 | Android-only; team-owned server on an authorized classified perimeter network, no managed cloud provider. Ceiling rests on the network's own authorization, not an inherited cloud P-ATO. |

### 12.3 Authoritative Compliance References

**DoD and Federal Standards:** NIST SP 800-53 Rev 5 (primary control catalog);
NIST SP 800-53B (control baselines — Moderate/IL4, High/IL6); NIST SP 800-37 Rev 2
(RMF — the ATO process this engine supports); NIST FIPS 199 (security
categorization); NIST FIPS 200 (minimum security requirements); DoD Cloud Computing
SRG v1r4 (DoD overlay — IL2/IL4/IL5/IL6); DISA Mobile Application STIG (Android
track); NIST SP 800-163 Rev 1 (mobile app vetting); NIST SP 800-124 Rev 2 (mobile
device security); CNSSP-15 (FIPS 140-3 requirement for IL6 crypto).

**Supply Chain:** NIST SP 800-161 Rev 1 (supply-chain risk — grounds the dependency
policy, SR family); 48 CFR § 227.7103 (government purpose rights — basis for
GPL/AGPL prohibition).

**Android / ATAK:** DISA Mobile Application STIG; TAK SDK documentation; WatchTower
distribution requirements.

**Application Security:** OWASP Top 10 (current — informs Sentinel gate checks);
OWASP LLM Top 10 (current — LLM08 Excessive Agency grounds lane-boundary
enforcement).

### 12.4 ATO Package Support

This engine produces artifacts that support an ATO submission:

| Artifact | Controls Evidenced |
|---|---|
| `_bmad-output/gate-log.md` | CA-2, SA-11 — record of what was tested and the result per story |
| Story files with gate results | SA-11, CA-2 — test phase + implementation phase commit hashes |
| `DEPENDENCY_POLICY.md` | SR-3, SR-5, SI-2, CM-10 — supply-chain inspection and CVE management |
| `DEVSECOPS_SPEC.md` | SA-15, SA-11 — developer security architecture |
| `ADR-LOG.md` | SA-8 — security engineering principles in design |
| `CONTROLS-MAPPING.md` | All controls — SSP implementing-mechanism cross-reference |

**Inherited controls:** controls implemented by the platform ATO, Keycloak, or
cloud infrastructure are documented as "inherited" in the SSP; application teams
confirm inheritance rather than re-implement. Control families addressed at the
organizational/operational level (not by application gate checks): AT, CP, IR, MA,
MP, PE, PL, PM, PS, partial CA.

**Inheritance source (ownable build).** This version names the inheritance source
generically as "the platform ATO." In an internal build, replace this with the
specific authorizing system/boundary name(s) for the target network. Do not record
real boundary names in any copy of this document kept on non-authorized hardware.

---

## 13. Non-Goals and Explicit Risks

*A PRD that names its own risks reads as competence. State these plainly.*

- **Not an ATO; platform team is the authority.** (Restated from §1.3 because it is
  the most important boundary in the document.)
- **Logic-layer review is human and fallible.** Automated gates reliably catch
  mechanical issues (lint, CVEs, coverage, STIG items). They do not reliably catch
  IDOR, auth-bypass-by-call-sequence, or business-rule violations. The manual gate
  exists *because* automation cannot — and is only as strong as the reviewer.
- **Separation-of-duties limit (single-operator engine).** The engine runs one
  operator per session, so the implementer and approver of a story are the same
  person by default — the four gates do **not** constitute separation of duties; they
  are a structured self-check (§6.1, §6.4). What compensates: the external platform team's
  independent review is the genuine separation of duties, and it runs downstream of
  everything this engine produces. Secure Builder is pre-flight only. The mitigation
  *within* the team is to assign a second qualified reviewer to security-sensitive
  stories (auth, RBAC, new endpoints, data-boundary changes) whenever staffing
  allows, and to record when it was not possible.
- **Gate-chain enforcement strength depends on environment (`GATE_ENFORCEMENT`).** In
  `ci-enforced` mode the gate chain is a server-side merge wall an operator cannot
  bypass from their workstation. In `local-attested` mode (air-gapped) it rests on a
  local hook, which a single operator with repository access can bypass; what
  compensates is the append-only gate log and git history — a skipped gate is visible
  and attributable after the fact — and the downstream platform team's independent
  re-check. A local hook prevents an *accidental* skip, not a *deliberate* one. Note
  the unfavorable overlap: air-gapped targets carry the weaker enforcement and are also
  where misses are least affordable (see offline-model degradation below), so they need
  correspondingly more human rigor.
- **Control-mapping false confidence.** A plausible-but-wrong control mapping is
  worse than none. Mappings are drafts for human confirmation, with cited text.
- **Mandatory-read verification gap.** Until reads are machine-verifiable, the read
  gate is human-attested; do not over-claim it (see §4.2).
- **Offline-model degradation (future).** A local model is weaker at exactly the
  security-reasoning the gates lean on. The offline build needs *more* human rigor,
  not the same — and is deployed where misses are least affordable.

---

## 14. Roadmap / Phases

**Track A — Harden the engine on the existing substrate.**
Formalize this PRD → run one real app through a full story lifecycle and record
where gates mislead → strengthen the manual-review gate (§6) — including evaluating
the risk-tiered light/full attestation model (a machine-gated light path for
non-security-sensitive stories, full §6.2 contract forced whenever the diff touches
security-sensitive surface) once the real per-story review load is known → make
control mappings cite text (§8.3).

**Track B — Own the orchestration layer.**
Only after the design is provably correct on the current substrate: build the
orchestration layer to the §10 spec (including the §7 template scaffold) and port
the proven design onto it. Debugging a novel design and a novel framework
simultaneously is explicitly out of scope for this phase.

**Track C — Offline / air-gapped transition.**
Local model (e.g., Ollama + Qwen) on owned hardware. Begin by measuring the
output-quality gap on an already-working app before redesigning anything. RAG over
a governance-document corpus for Sentinel: retrieval first (achievable), judgment
stays human. Start the corpus small (800-53 + the relevant SRG), not "every
document."

---

## Appendix A — Glossary

| Term | Definition |
|---|---|
| **ATO** | Authority to Operate. A formal authorization decision allowing an information system to operate in a given environment, issued by an authorizing official after risk review. |
| **cATO** | Continuous Authority to Operate. An evolution of ATO where authorization is sustained through continuous monitoring and automated control evidence rather than periodic re-authorization. |
| **RMF** | Risk Management Framework (NIST SP 800-37 Rev 2). The process by which federal systems are categorized, controlled, assessed, authorized, and monitored — the process this engine produces evidence for. |
| **SSP** | System Security Plan. The document describing a system's security controls and how each is implemented; gate evidence here feeds its implementing-mechanism references. |
| **POA&M** | Plan of Action and Milestones. A tracked remediation plan for known security weaknesses that cannot be fixed immediately, with owners and timelines. |
| **IL2 / IL4 / IL5 / IL6** | Impact Levels under the DoD Cloud Computing SRG. IL2 = public/non-critical; IL4 = Controlled Unclassified Information (CUI); IL5 = higher-sensitivity CUI / NSS; IL6 = classified up to SECRET. |
| **STIG** | Security Technical Implementation Guide (DISA). Configuration standards that harden a product or platform to DoD requirements. |
| **DISA** | Defense Information Systems Agency. The DoD agency that publishes STIGs, the Cloud Computing SRG, and related standards. |
| **DoD CC SRG** | DoD Cloud Computing Security Requirements Guide. The DoD overlay defining cloud impact levels (IL2/IL4/IL5/IL6) on top of FedRAMP. |
| **TDD** | Test-Driven Development. Writing a failing test before the implementation that makes it pass — enforced here as a two-commit sequence (Guarantee #3). |
| **ATDD** | Acceptance Test-Driven Development. Deriving tests directly from acceptance criteria so every criterion maps by name to at least one test. |
| **IDOR** | Insecure Direct Object Reference. An authorization flaw where a user can access another user's resource by manipulating an identifier not scoped to their ownership. |
| **RBAC** | Role-Based Access Control. Authorization model granting permissions to roles, which are assigned to users. |
| **CDS** | Cross-Domain Solution. A controlled mechanism for moving data between networks of different classification levels. |
| **FIPS 140-3** | Federal Information Processing Standard for cryptographic modules. IL6 requires validated FIPS 140-3 crypto (per CNSSP-15). |
| **CNSSP** | Committee on National Security Systems Policy. CNSSP-15 specifies approved cryptography for national security systems. |
| **NSS** | National Security System. A system handling classified or otherwise nationally sensitive information, subject to CNSS policy. |
| **ATAK / TAK SDK** | Android Team Awareness Kit and its Software Development Kit. ATAK is a geospatial situational-awareness app; plugins are built against the TAK SDK and distributed via WatchTower. |
| **OWASP LLM08** | "Excessive Agency," item 8 of the OWASP Top 10 for LLM Applications. The risk that an LLM agent acts beyond its intended scope — the basis for lane-boundary enforcement (Guarantee #5). |
| **P-ATO** | Provisional Authority to Operate. A FedRAMP authorization issued by the Joint Authorization Board that agencies may inherit/leverage. |
| **FedRAMP** | Federal Risk and Authorization Management Program. The US government program standardizing cloud security authorization; its High baseline underpins several impact-level ceilings here. |
| **ADR** | Architecture Decision Record. A dated, append-only entry capturing one architectural decision, what was rejected, and why. |
| **CVE** | Common Vulnerabilities and Exposures. A publicly catalogued software vulnerability identifier, tracked by the dependency policy. |
| **CUI** | Controlled Unclassified Information. Sensitive but unclassified information requiring safeguarding; the IL4 data category. |
| **MVVM** | Model-View-ViewModel. The Android architectural pattern specified for the Kotlin/native track. |
