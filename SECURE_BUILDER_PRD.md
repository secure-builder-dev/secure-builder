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
2. **No promotion without a complete gate chain.** Local TDD working commits (the §5.1
   test-only and implementation commits) are permitted during the build context as audit
   evidence — they are themselves tamper-evident in git history (Guarantee #6). But
   nothing is *promoted* — recorded DONE in the gate log, pushed, or merged to the
   integration branch — without, in order: Quality gate PASS, Security gate PASS, Manual
   security review CLEAR, and explicit human approval. No step may be skipped, reordered,
   or auto-approved. How this is *enforced* depends on `GATE_ENFORCEMENT` (§9): in
   `ci-enforced` mode the
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
| Atlas | Contextualization Lead | **Phase-0 inception (§15):** guide authoring + gap-hardening of the document matrix, backlog generation + intent-traceability, cohesion-gate criteria; orchestrate lane owners for reverse-engineered current-state — writes no other lane's artifact | `docs/context/**` (matrix index, current-state pre-fill, traceability map, cohesion criteria) |
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
Bob (scrum master), Atlas (contextualization lead), Murat (test architect), Frank
(DevSecOps), and Sentinel (security gatekeeper) — have no stock equivalent and are
**custom skills built to the §7 scaffold**; building them is part of Phase 2 (see §14). Invocation names are an
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

Every story executes this sequence exactly, across **two context windows** with a
deliberate information barrier between them. No step may be skipped, reordered, or
auto-approved.

**Why two contexts (the bias firewall).** The build context and the gate context are
separate sessions — separate model context windows. The gate context receives only the
story file and the code diff, never the builder's reasoning or self-assessment, so a
fresh set of eyes scans the artifact cold and cannot be talked into the author's framing.
This is **context-isolated independent review**; it strengthens the *independence* of the
automated self-check but is **not** separation of duties — still AI reviewing AI under one
operator with one human approver (§6.1, §13). Target substrate (Phase 2 / Track C, §14):
the build context runs on one local model and the gate context on a *different* one; on
the current substrate both run on the same model in two separate sessions.

**Context Window 1 — Build** (entered cold from `NEXT_PROMPT.md`):

1. **Dispatch.** Bob routes the story to the correct first agent per the routing
   table (§4.1).
2. **Implementation.** The assigned agent implements. For Amelia, the TDD two-commit
   sequence is mandatory (test-only failing commit precedes implementation commit, §5.1).
   These are **local working commits** — audit evidence, not approval and not promotion
   (Guarantee #2, §8.1).
3. **Gate handoff.** The build context ends by writing `NEXT_PROMPT_GATES.md` (§4.3),
   pointing the gate context at the story and the diff. The build context does not gate
   its own work.

**Context Window 2 — Gates** (entered cold from `NEXT_PROMPT_GATES.md`, blind to CW1's reasoning):

4. **Quality gate (Murat).** FAIL → remediation note back to the builder, re-run.
   PASS → proceed.
5. **Security gate (Sentinel).** Sentinel first loads and attests its full skill set —
   including adversarial testing (§4.2) — before judging. FAIL → remediation note back to
   the builder, re-run. PASS → proceed. The FAIL→fix→re-scan loop is **capped at 3
   rounds**, then escalates to the human rather than auto-remediating indefinitely.
6. **Manual security review (human + the AI assistant) — hard stop.** Findings → back to
   the builder with remediation notes, then full re-gate. CLEAR → proceed (§5.5, §6).
7. **Human approval (hard stop).** Explicit "approved" — the only thing that unlocks
   promotion. On approval: Sentinel appends the gate-log DONE row (§8.1), then Bob writes
   the next story's handoff (§4.3).

**Nothing is promoted without: Quality PASS + Security PASS + Manual CLEAR + explicit
human approval.** The AI model cannot approve its own work; self-approval is a
protocol violation regardless of how correct the underlying work is.

### 4.1 Agent routing

| Story Type | First Agent | Then |
|---|---|---|
| **Phase-0 project inception (§15) — before any story** | **Atlas** | John/Winston/Sentinel (matrix) → Tori (gap + traceability gates) → human ratification |
| New story writing | John | Tori (refinement) |
| Story refinement / gap analysis | Tori | Bob (dispatch) |
| Schema change / new ADR | Winston | Amelia |
| UI/frontend feature with design surface | Sally | Amelia → Murat → Sentinel |
| Feature / API endpoint | Amelia | Murat → Sentinel |
| DevSecOps / pipeline / Helm | Frank | Sentinel |
| New dependency | Sentinel (DP review) | Amelia |
| All stories, post-implementation | Murat | Sentinel → manual review |
| **Epic complete (cohesion gate, §4.5)** | **Atlas** | `COHERENT` → epic closes · `DRIFT` → correct-course |

### 4.2 Mandatory Read Protocol

Every agent receives a mandatory read list before starting work. Skipping a
mandatory read is a gate failure at Murat or Sentinel.

| Agent | Mandatory Reads |
|---|---|
| John | `docs/STORY_TEMPLATE.md`, `docs/PRD.md` |
| Tori | Story file(s), `STORY_TEMPLATE.md`, `PRD.md`, `API_CONTRACT.md`, `DB_SCHEMA_v2.md`, `DEPENDENCY_POLICY.md` |
| Atlas | `PRD.md`, `STORY_TEMPLATE.md`, the target repo/source (brownfield current-state), the existing governing docs in the matrix, `docs/context/**` |
| Amelia | Story file, `API_CONTRACT.md`, `DB_SCHEMA_v2.md`, `DEPENDENCY_POLICY.md` |
| Murat | Story file, `QUALITY_GATE.md` |
| Sentinel | `CLAUDE.md` (always in context), `DEPENDENCY_POLICY.md`, **all Sentinel gate skill files — incl. adversarial testing — loaded and attested (see below)** |
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

**Sentinel skill-load protocol (forced read-and-attest).** Sentinel's checks live in its
skill files and are not to be improvised or recalled from memory. At the start of the gate
context, Sentinel must open and read each skill file — quality- and security-gate checks,
control lookup against `CONTROLS-MAPPING.md`, the dependency policy, and adversarial
testing — and echo a one-line attestation of each before judging any code. A gate run that
did not load and attest its skills is invalid and re-runs. Forcing the read pulls the skill
instructions into context rather than trusting the model to recall them; this is stronger
than ambient presence but, like the read gate above, is still not positive proof the
instructions were *applied* (§13).

### 4.3 Sprint Continuity — Handoff Prompts

The next session has no memory of the current one, so every handoff must be fully
self-contained. Three handoff artifacts exist, on two axes:

**Inter-story (a completed story → the next story's session), written by Bob:**

- `_bmad-output/NEXT_PROMPT.md` — written after each **S-prefix (story)** commit.
- `_bmad-output/NEXT_PROMPT_FRAMEWORK.md` — written after each **F-prefix
  (framework)** commit.

**Intra-story (a story's build context → its gate context), written by the build
context:**

- `_bmad-output/NEXT_PROMPT_GATES.md` — written at the end of implementation to hand the
  story and its diff to the gate context (§4 CW2). It carries a single story
  mid-lifecycle, is overwritten each story, points the fresh gate context at exactly what
  to scan without leaking the builder's reasoning, and enumerates Sentinel's mandatory
  skill-loads (§4.2).

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

### 4.5 Epic-boundary Cohesion Gate

The §4 gates above judge a *single story*. They cannot catch **intent drift across an
epic** — a set of stories that each passed its own gates but, assembled, no longer
fulfills what the document matrix (§15.1) said the epic was for. The cohesion gate closes
that gap.

- **Standing, universal.** It fires at the completion of **every** epic, on every project
  — a fixed tier of the lifecycle, not opt-in.
- **Per-project criteria.** *What* it checks is generated from that project's matrix during
  Phase 0 (§15.2, step 5), the same universal-gate / conditional-content pattern the
  security gate uses with the §9 init variables.
- **What it asks.** Does the assembled, gate-passed epic still satisfy its intent elements
  in the matrix? Did any story satisfy an acceptance criterion in a way that violates a
  matrix `SHALL NOT` (a business-rule bypass surfacing only at the epic level)? Is every
  intent element the epic owns covered by shipped work?
- **Verdict.** Binary — `COHERENT` / `DRIFT`. `DRIFT` blocks epic close and returns to
  correct-course (re-scope, add a story, or amend intent with a recorded ADR) before the
  epic is recorded done. Owned by **Atlas** (defines the criteria in Phase 0); it runs in
  the build phase and its verdict is recorded like any other gate.

> Like every other gate here, it is a structured self-check, not proof — AI-assisted intent
> comparison with a human confirming. It does not certify intent; it flags divergence for a
> human (§6, §13).

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
platform/DevOps team and to streamline movement toward continuous ATO (cATO). The
two-context build/gate split (§4) does not change this: isolating the gate reviewer from
the builder's reasoning strengthens the independence of the automated self-check, but it
is still AI reviewing AI under one operator with one human approver — independent review,
not separation of duties.

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
explicit "approved" in conversation — the only thing that unlocks promotion.

**Update protocol:** Sentinel owns the gate log (§3 manifest) and authors every row — its
verdict and finding rows live during the gate context, the terminal rows on approval
(earlier drafts assigned this to Bob, which contradicted the manifest; corrected here). It
appends one Quick Ledger row, one Detailed Ledger row, a `DETECTED` row for any new
finding, and the matching terminal row when a prior finding closes — `REMEDIATED` if fixed, `ACCEPTED` if carried forward
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
`DEPENDENCY_POLICY.md`; `DEVSECOPS_SPEC.md`; `MODEL-PROFILES.md` (Track-C local-model
binding, `COMPUTE_PROFILE` — ADR-0003). *(The gate log is a sprint-output artifact,
below — `_bmad-output/gate-log.md`, Sentinel-owned; it is not an architecture doc.)*

**Project context (Phase 0, §15):** `docs/context/` — matrix index, reverse-engineered
current-state pre-fill, intent-traceability map, and cohesion-gate criteria (Atlas-owned).
The fixed-core matrix lives in its lane documents (PRD, architecture, security).

**Security documents:** `docs/security/README.md` (two-layer overview, ADR-020/022/
023); `controls/IL4-baseline.md`; `controls/IL6-delta.md`; `controls/CONTROLS-
MAPPING.md`; `controls/CDS-guidance.md`; provider implementation + STIG-checklist
files under `providers/{aws,azure,android,tactical}/`; verbatim authoritative source text
under `corpus/` (NIST / DISA / OWASP / DoD-AI, read on demand — §15.4; ledger in
`corpus/MANIFEST.md`).

**Sprint output artifacts** (all in `_bmad-output/`): `gate-log.md` (Sentinel — verdict
and finding rows live in the gate context, terminal DONE row on approval); `NEXT_PROMPT.md`
(Bob, after each S-prefix commit); `NEXT_PROMPT_FRAMEWORK.md` (Bob, after each F-prefix
commit); `NEXT_PROMPT_GATES.md` (build context — intra-story build→gate handoff);
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
| `COMPUTE_PROFILE` | `laptop-resident` \| `egpu-70b` | Track-C local substrate binding (US/ally open-weight only, §14; ADR-0003). `laptop-resident` (24 GB VRAM) = build **Devstral Small 2** + gate **Gemma 4**, hot-swapped (contexts are sequential). `egpu-70b` (external GPU/dedicated box) = build Devstral Small 2 on the internal GPU + gate **Llama 3.3 70B** on the external card. Design-time constant; full binding in `docs/architecture/MODEL-PROFILES.md`. Applies once Track C is active. |

**Decision tree:** Web → impact level (IL4/IL6) → cloud provider (aws/azure).
Android → `SECURITY_TIER=IL6` (always), `PROVIDER=tactical` (always), app type
(native/atak). All tracks → gate enforcement (`ci-enforced` where a remote CI exists,
`local-attested` for air-gapped targets) → (Track C only) compute profile (`egpu-70b`
where a second GPU is attached, else `laptop-resident`).

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

### 11.1 Model provenance (standing rule — binds the engine *and* every app it produces)

**No model whose base weights originate in a foreign-adversary nation may be used in the
Secure Builder engine or embedded in any application it produces.** This sits alongside
the OPSEC rules above — standing, and not relaxable by a story instruction. Decision of
record: **ADR-0003**; binding config: `docs/architecture/MODEL-PROFILES.md`
(`COMPUTE_PROFILE`, §9).

- **It binds on the base weights' origin, not the uploader.** A Western fine-tune,
  distill, or merge of an adversarial-nation base model is still excluded — **including
  embedding and reranker models.** Excluded (non-exhaustive): Qwen, DeepSeek and any
  R1-distill, Yi, GLM/CodeGeeX, InternLM, Baichuan, MiniCPM, Skywork, Hunyuan, Ernie,
  Stepfun; embeddings BGE (BAAI) and GTE (Alibaba).
- **Acceptable origin is US or allied-nation open-weight.** Track C's binding is build =
  Mistral Devstral Small 2 (🇫🇷, Apache-2.0), gate = Google Gemma 4 (🇺🇸, Apache-2.0),
  scaling the gate to Llama 3.3 70B on an external GPU (§14).
- **The judgment is human-confirmed, not machine-verified** (§13). It rests on the
  supply-chain principles in §12.3, **not** an official approved-model list — none exists.
  Re-confirm on every model add or change; a model is a dependency and goes through
  Sentinel's dependency review (§5.6) like any other.

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

**Application Security:** DISA Application Security & Development STIG (the web-track
application STIG); OWASP Top 10 (informs Sentinel gate checks); OWASP ASVS (verification
requirements); OWASP LLM Top 10 (LLM08 Excessive Agency grounds lane-boundary
enforcement); OWASP MASVS (Android track).

**Model provenance / supply chain (§11.1, ADR-0003):** NIST SP 800-161 Rev 1 (C-SCRM);
SP 800-53 Rev 5 SR-3 / SR-4 / SR-11; and the covered-nation statutory framework
(Section 889, FASC/FASCSA, Commerce ICTS) as *principles* — there is **no** official
approved-model list, so the acceptable-origin judgment is human-confirmed, not
machine-verified.

> **Where the text lives.** These are the documents the engine cites; the verbatim
> controlling text is vendored under `docs/security/corpus/` and read on demand by
> control ID (§15.4, ADR-0002). Which of them are actually vendored — versus deliberately
> deferred — is tracked honestly in `corpus/MANIFEST.md`. Listing a document here is not a
> claim that its text is local; check the manifest before asserting a citation is
> openable.

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
  allows, and to record when it was not possible. (The two-context build/gate split in §4
  sharpens the independence of the automated self-check but does not create internal
  separation of duties — it remains AI reviewing AI under one operator.)
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
Local models on owned hardware, one per context window, **US/allied-nation open-weight
only** under the standing provenance rule (no adversarial-nation base weights — decision of
record **ADR-0003**, binding config `docs/architecture/MODEL-PROFILES.md`): the **build
context** on **Mistral Devstral Small 2** (🇫🇷, Apache-2.0) and the **gate context** on a
*different-lineage* model — **Google Gemma 4** (🇺🇸, Apache-2.0) on the 24 GB laptop, scaling
to **Llama 3.3 70B** on an external GPU — so the §4 bias firewall is reinforced by genuinely
different weights, not just different sessions. The hardware binding is the `COMPUTE_PROFILE`
init variable (§9): `laptop-resident` (hot-swap on one GPU, the forward/DDIL profile) vs.
`egpu-70b` (beefy gate on an attached GPU). The real target is **complete-airgap codebase
modification, forward-deployed at a unit in a DDIL environment**, which is why SWaP and
air-gap simplicity drive the hardware choice. Begin by measuring the output-quality gap on
an already-working
app before redesigning anything. A **curated governance reference corpus** for Sentinel
(`docs/security/corpus/`, §12.4): verbatim authoritative source text (NIST, DISA, OWASP,
DoD AI) the security gate **reads on demand**, keyed by control ID — not a vector store. It
is version-controlled and vendored into the repo so it works offline; the check→control
*mapping judgment* stays human. Start small (800-53 + the relevant SRG for the active
tiers), not "every document"; semantic retrieval is an *optional later* discovery aid over
the same files, never the citation path.

---

## 15. Project Contextualization Workflow (Phase 0 — prerequisite)

> **This workflow runs before any story.** The §4 lifecycle silently assumes the
> project's governing context already exists — the intent an epic is built toward, the
> `SHALL NOT` rules the manual gate (§5.5) and cohesion gate (§4.5) check against, the
> target contracts a story is written to. That context is not code; it is a **document
> matrix** — the PRD and its supporting governing documents, capturing current state,
> the desired delta, and the end-state intent. For greenfield it is authored fresh; for
> **brownfield it must be built and hardened before the engine can be handed to a
> peer.** This workflow is the engine's own onboarding, automated: it guides a user
> through producing a build-ready project so the person who *knows how to set up the
> context is no longer required to be in the loop.*

**What Phase 0 delivers** (three artifacts; nothing downstream is valid without them):

1. a **hardened document matrix** — the governing context the build reasons from;
2. an **intent-traceable backlog** — epics and stories proven to fulfill the matrix;
3. the project's **cohesion-gate criteria** — the per-project intent-integrity checks the
   §4.5 gate runs at each epic boundary.

**The labor inversion.** Phase 0 does not ask the human to author the matrix from a blank
page. It **guides via structured elicitation** — it asks the questions an expert knew to
ask — and, for brownfield, pre-fills the *current-state* half by reverse-engineering the
existing code (OPSEC-filtered, §11), so the human confirms and supplies intent rather than
transcribes. Encoding that tacit question-and-check sequence *is* the automation.

### 15.1 The document matrix — fixed core + needed-only additions

**Fixed core (always produced),** written by the existing lane owners, not Atlas:

| Document | Captures | Lane |
|---|---|---|
| PRD / intent | Current state, desired delta, end-state intent | John |
| Target architecture + API/DB contracts | The system the build is moving *toward* | Winston |
| Target security posture | Impact level, enclave/boundary target, control baseline | Sentinel |
| Migration / delta plan | The path from current state to end-state (brownfield) | John + Winston |

**Needed-only additions (capped, human-approved).** After the core is drafted, a needs-
analysis inspects the project and may recommend *additional* governing documents —
**hard cap 3, target ≤ 2, default zero.** A document is recommended **only if the
recommendation names the specific build failure or intent-gap that occurs without it.**
If that failure cannot be stated, it is not recommended. The cap is a ceiling, never a
quota; **no fluff** — the matrix stays as small as the build allows. The human accepts or
declines each recommendation.

Atlas owns only the `docs/context/**` artifacts — the matrix index, the reverse-engineered
current-state pre-fill, the traceability map, and the cohesion criteria — and **triggers**
the lane owners to write the governing documents into their own artifacts, so Guarantee #5
lane boundaries hold.

### 15.2 The workflow (staged, gated between stages)

Orchestrated by **Atlas** (§3) — the Phase-0 analogue of Bob, coordinating the lane owners.

0. **Intake & current-state pre-fill.** Greenfield or brownfield; point at the repo. For
   brownfield, deterministic extraction (file walk, AST parse, route/schema introspection,
   dependency scan) pre-fills the current-state fields; the OPSEC filter (§11) strips
   sensitive values to placeholders before anything is written. Facts are provenance-tagged
   (`[extracted: path@commit]` / `[human-asserted]`). *(Greenfield: thin — little code yet.)*
1. **Author the matrix (guided).** Structured elicitation drives John/Winston to capture
   the delta and end-state intent. The needs-analysis then runs and presents its capped,
   needed-only recommendations (§15.1) for human decision.
2. **Harden — Gap-Analysis Gate.** Gap analysis runs across **every** document in the
   matrix, checking two properties: **coherence** (no document contradicts another) and
   **completeness** (no intent element left unspecified). Driver: **Tori** (gap analysis is
   her lane). Loops with findings until the matrix is clean.
3. **Generate the backlog.** Epics and stories derived from the hardened matrix, each
   stamped with the intent element(s) it traces to. Driver: **John**.
4. **Pressure-test — Intent-Traceability Gate.** Bidirectional: **every story maps to an
   intent element** (no rogue work) and **every intended delta is covered by ≥ 1 story**
   (no gap). Driver: **Tori**. Failures return to step 3.
5. **Establish cohesion criteria.** Atlas generates the per-epic intent-integrity checklist
   from the matrix and wires it into the §4.5 epic-boundary gate.

**Handoff.** Hardened matrix + intent-traceable backlog + cohesion criteria = a build-ready
project. A peer runs the §4 engine to the end-state without the original context author.

### 15.3 Guarantees and honest limits

These extend the §2 doctrine to the context layer; they do not replace it.

- **Human-ratified, not auto-trusted** (mirrors Guarantee #1). The matrix and backlog are
  AI-assisted *drafts*; intent is human-owned. Neither is authoritative until a human
  ratifies it. Self-ratification by an agent is a protocol violation, as self-approval is.
- **Provenance on reverse-engineered facts** (mirrors Guarantee #4). Every current-state
  fact cites its source or is tagged `[human-asserted]`.
- **OPSEC-filtered extraction** (mirrors Guarantee #7, §11). Reverse-engineering a real
  secure codebase is exactly where infra values leak; filtering to placeholders precedes
  any write, and structural separation remains the primary control.
- **The three Phase-0 gates are structured self-checks, not proof.** Gap-Analysis,
  Intent-Traceability, and Cohesion (§4.5) are AI-assisted comparisons with a human
  confirming — the same honesty caveat as every other gate (§4.4, §13). Ratified ≠ verified.
- **Needed-only, no fluff.** The needs-analysis recommends a document only against a named
  build failure; zero is the default and common outcome.
- **The build inherits the matrix.** If intent is wrong or incomplete, the backlog and code
  inherit it — but *visibly*, because it is drafted, provenance-tagged, and ratified.

### 15.4 Relationship to the governance reference corpus

Keep two bodies of text separate. (1) The **governance reference corpus**
(`docs/security/corpus/`) — verbatim NIST / DISA / OWASP / DoD-AI source text — is external
authoritative controlling text the security gate **reads on demand**, keyed by control ID,
to ground citations (Guarantee #4). It is a version-controlled folder, **not** a vector
store; the full catalog is never loaded into a prompt. (2) The **document matrix** is
per-project governing intent, *loaded* into agent context via mandatory-reads (§4.2) — and
semantic-retrieval recall failure on an intent element (a silently un-retrieved `SHALL NOT`)
is exactly the failure a security build cannot tolerate, which is why neither body relies on
fuzzy retrieval for its authoritative path. Vector/semantic search is at most a *later,
optional discovery aid* (finding a control when its ID is unknown; searching a large
brownfield source tree during Phase 0 step 0) — never the citation path or the home of the
matrix.

### 15.5 Implementation (substrate-agnostic)

- **Storage.** Version-controlled, human-diffable governing documents (the core matrix in
  their lane artifacts) plus Atlas's `docs/context/**` — matrix index, current-state
  pre-fill with inline provenance, traceability map, cohesion criteria, and an append-only
  ratification ledger.
- **Construction.** The §15.2 pipeline: extraction → OPSEC filter → guided authoring +
  needs-analysis → gap-hardening → backlog → traceability → cohesion criteria.
- **Consumption.** The matrix feeds the build through the §4.2 mandatory-read lists; the
  traceability map drives the §4.5 cohesion gate.
- **Current substrate.** Seeds already exist as framework skills — project documentation
  (`bmad-document-project`), PRD and architecture creation, epics/stories creation, and
  implementation-readiness/gap checks; Phase 0 orchestrates them into one guided flow with
  the two new gates. **Target substrate (Track B/C, §14):** own the pipeline and the
  elicitation scripts; the governance corpus (§15.4) stays a separate, read-on-demand body
  of text — never merged into the matrix.

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
| **GATE_ENFORCEMENT** | Initialization variable (§9) selecting how the §2 gate chain is enforced: `ci-enforced` (server-side branch protection + required CI status checks — a true merge wall, requires a Git remote with CI) or `local-attested` (local pre-commit hook + append-only audit + operator discipline, for air-gapped/offline targets with no remote CI). Sets the honest strength of Guarantee #2. |
| **Negative authorization test** | A test asserting that an *un*authorized actor is denied — e.g., user A cannot read user B's resource (IDOR), or a role lacking a permission is rejected. Guarantee #8 requires every endpoint to ship with these, not just positive happy-path tests. |
| **NIST** | National Institute of Standards and Technology. Publisher of the SP 800-series standards this engine produces evidence against — notably SP 800-53 (security controls) and SP 800-37 (RMF). |
| **SP** | Special Publication. NIST's standards series (e.g., SP 800-53 Rev 5, SP 800-37 Rev 2). |
| **RAG** | Retrieval-Augmented Generation. Grounding LLM output in retrieved source documents rather than model memory. **Explicitly rejected as the citation path for Guarantee #4** (ADR-0002): control text is read on demand from the corpus by control ID, not fuzzily retrieved. Semantic retrieval is at most a later *discovery* aid. |
| **Governance corpus** | `docs/security/corpus/` — verbatim authoritative source text (NIST/DISA/OWASP/DoD-AI), version-controlled and vendored so it works offline, read on demand keyed by control ID. Grounds Sentinel's citations (Guarantee #4). Not a vector store; not the document matrix (§15.4). |
| **Document matrix** | The per-project set of governing documents (current state, desired delta, end-state intent) produced and human-ratified in Phase 0 (§15). Loaded into agent context via mandatory reads. Distinct from the governance corpus. |
| **Intent element** | A single unit of intent in the document matrix. Every story is stamped with the intent element(s) it traces to; the Intent-Traceability Gate (§15.2) checks that mapping both directions. |
| **SCA** | Software Composition Analysis. Scanning resolved dependencies for known-vulnerable components and license violations. |
| **MCP** | Model Context Protocol. The protocol connecting agents to external tools and data sources; part of the integration surface in the Track-B rebuild inventory (§10.1). |
| **CFR** | Code of Federal Regulations. The codification of US federal agency regulations (e.g., 48 CFR § 227.7103, government purpose rights). |
| **APK** | Android Package. The installable Android application bundle; the `native` Android distribution artifact. |
| **MDM** | Mobile Device Management. Enterprise control plane for distributing and managing apps on devices; a `native` Android distribution channel. |
| **LUKS** | Linux Unified Key Setup. A disk-encryption specification cited as an example data-at-rest mechanism (SC-28). |
