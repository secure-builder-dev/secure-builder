# CONTROLS-MAPPING.md — Sentinel check → NIST 800-53 Rev 5 control mapping

> **Owner:** Sentinel (Security Gatekeeper). **Source of record:**
> `SECURE_BUILDER_PRD.md` §5.4, §8.3. **Implements:** Guarantee #4 (every security check
> traces to controlling text from an authoritative corpus). **Feeds:** the SSP
> implementing-mechanism cross-reference; ATO package (PRD §12.4).
>
> This is the **static starter mapping** — a curated table of each Sentinel gate check to
> its NIST SP 800-53 Rev 5 control ID(s). It is **enough to demo and to gate against
> today.** Retrieval of the **verbatim controlling text** from a curated corpus (the
> "Cited text" column) is a **fast-follow** (RAG — PRD §14 Track C), not a blocker.

---

## How to read this table — and what it does and does NOT assert (Guarantee #4 honesty)

Guarantee #4 has two distinct parts, and they have different strength:

- **The citation** (control ID + the controlling text) is meant to be *grounded* — an
  assessor can open the source. Today the **ID and official title are recorded** (stable
  catalog identifiers); the **verbatim text** is marked `⟶ corpus` and is filled when the
  retrieval corpus lands. **Do not paraphrase a control and present it as the cited
  text.**
- **The mapping judgment** — that a given check actually *satisfies* a given control —
  **remains human-confirmed.** Every row starts as `DRAFT` and becomes `RATIFIED` only
  when a human confirms it (logged in §6). A human ratifies each **check-type's** mapping
  **once**, and it is reused across stories — not re-confirmed every story.

**A plausible-but-wrong mapping is worse than none** (PRD §13). Treat every `DRAFT` row as
a proposal, not a fact. Mapping quality is bounded by the corpus's coverage and currency.

Columns: **Check** (the Sentinel gate check) · **Control(s)** (Rev 5 ID) · **Control title**
(official catalog title) · **Status** (`DRAFT` / `RATIFIED`) · **Cited text** (`⟶ corpus`
until retrieval lands).

---

## 1. IL4 Baseline checks — always active

| Check | Control(s) | Control title | Status | Cited text |
|---|---|---|---|---|
| No hardcoded secrets | IA-5; CM-6 | Authenticator Management; Configuration Settings | DRAFT | ⟶ corpus |
| All endpoints require a valid identity token | IA-2; AC-3 | Identification & Authentication (Org Users); Access Enforcement | DRAFT | ⟶ corpus |
| Auth middleware registered before route handlers | AC-3; SA-8 | Access Enforcement; Security & Privacy Engineering Principles | DRAFT | ⟶ corpus |
| Negative authorization test required (per endpoint) | CA-2; SA-11 | Control Assessments; Developer Testing & Evaluation | DRAFT | ⟶ corpus |
| RBAC scoping correct per role lanes | AC-2; AC-3; AC-6 | Account Management; Access Enforcement; Least Privilege | DRAFT | ⟶ corpus |
| Negative RBAC tests / IDOR | AC-3; AC-4 | Access Enforcement; Information Flow Enforcement | DRAFT | ⟶ corpus |
| Last-admin guard at the API layer | AC-2; AC-5 | Account Management; Separation of Duties | DRAFT | ⟶ corpus |
| SQL injection prevented — parameterized queries only | SI-10 | Information Input Validation | DRAFT | ⟶ corpus |
| Query-view reads, not base-table reads | AC-3; SA-8 | Access Enforcement; Security & Privacy Engineering Principles | DRAFT | ⟶ corpus |
| Mutations via dedicated PATCH endpoints | CM-5; AC-3 | Access Restrictions for Change; Access Enforcement | DRAFT | ⟶ corpus |
| `SELECT FOR UPDATE` on concurrent-sensitive endpoints | AC-3; SI-10 | Access Enforcement; Information Input Validation | DRAFT | ⟶ corpus |
| Soft-delete / archive filters on active-record queries | AC-3; SI-12 | Access Enforcement; Information Management & Retention | DRAFT | ⟶ corpus |
| Computed columns never written by app code | CM-5; SA-8 | Access Restrictions for Change; Security & Privacy Engineering Principles | DRAFT | ⟶ corpus |
| Custom error handler — no stack traces in responses | SI-11 | Error Handling | DRAFT | ⟶ corpus |
| File uploads use memory storage | SC-28; CM-6 | Protection of Information at Rest; Configuration Settings | DRAFT | ⟶ corpus |
| API-proxied downloads, no presigned object-store URLs | AC-3; SC-8 | Access Enforcement; Transmission Confidentiality & Integrity | DRAFT | ⟶ corpus |
| No server-side token storage or session middleware | IA-5; SC-23 | Authenticator Management; Session Authenticity | DRAFT | ⟶ corpus |
| All new dependencies on the approved list | SA-12 → SR-3; CM-3 | Supply Chain Protection (Rev-5 successor SR-3 Supply Chain Controls & Processes); Configuration Change Control | DRAFT | ⟶ corpus |

> The listed checks are **examples drawn from PRD §5.4**, not an exhaustive enumeration.
> Add a row whenever a new baseline check is introduced; a check with no row is a gap, and
> shipping an unmapped check is itself a finding.

## 2. IL6 additional checks — active when `SECURITY_TIER=IL6`

| Check | Control(s) | Control title | Status | Cited text |
|---|---|---|---|---|
| FIPS 140-3 validated crypto only | IA-7; SC-13 | Cryptographic Module Authentication; Cryptographic Protection | DRAFT | ⟶ corpus |
| Classification banner header on all API responses | SC-16 | Transmission of Security & Privacy Attributes | DRAFT | ⟶ corpus |
| No unclassified external calls at runtime | SC-7(8) | Boundary Protection — Route Traffic to Authenticated Proxy Servers | DRAFT | ⟶ corpus |
| Audit logs to a tamper-evident append-only store | AU-9(2) | Protection of Audit Information — Store on Separate Components | DRAFT | ⟶ corpus |
| CDS integration points documented and not bypassed | SC-16(1) | Transmission of Security & Privacy Attributes — Integrity Verification | DRAFT | ⟶ corpus |
| Clearance level not stored in the app DB | IA-4; AC-2 | Identifier Management; Account Management | DRAFT | ⟶ corpus |
| FIPS 140-3 module list verified | SC-13; IA-7 | Cryptographic Protection; Cryptographic Module Authentication | DRAFT | ⟶ corpus |

## 3. Android track checks — active when `APP_TRACK=android`

> Android source standards are DISA Mobile Application STIG, NIST SP 800-163 Rev 1 (app
> vetting), NIST SP 800-124 Rev 2 (mobile device security), and the TAK SDK — not the
> 800-53 catalog. Recorded here by their authoritative source rather than a control ID.

| Check | Authoritative source | Status | Cited text |
|---|---|---|---|
| TLS 1.2 minimum | DISA Mobile Application STIG | DRAFT | ⟶ corpus |
| No sensitive data to external storage | NIST SP 800-124 Rev 2 | DRAFT | ⟶ corpus |
| No sensitive data in logcat | DISA Mobile Application STIG | DRAFT | ⟶ corpus |
| Auth token in Android KeyStore | NIST SP 800-163 Rev 1 | DRAFT | ⟶ corpus |
| `Authorization: Bearer` header on API calls | DISA Mobile Application STIG | DRAFT | ⟶ corpus |
| Certificate pinning evaluated and documented | NIST SP 800-163 Rev 1 | DRAFT | ⟶ corpus |
| No hardcoded credentials or base URLs | DISA Mobile Application STIG | DRAFT | ⟶ corpus |
| Exported components minimized and justified | DISA Mobile Application STIG | DRAFT | ⟶ corpus |
| `minSdkVersion` documented and justified | DISA Mobile Application STIG | DRAFT | ⟶ corpus |
| ATAK plugin manifest ≥ 5.6 (when `APP_TYPE=atak`) | TAK SDK | DRAFT | ⟶ corpus |

## 4. Tactical provider checks — active when `PROVIDER=tactical`

| Check | Control(s) / source | Control title | Status | Cited text |
|---|---|---|---|---|
| TLS termination documented at reverse-proxy layer | provider ADR (see `ADR-LOG.md`) | — | DRAFT | ⟶ corpus |
| No plaintext secrets in provisioning scripts/config | IA-5 | Authenticator Management | DRAFT | ⟶ corpus |
| Audit-log destination satisfies 365-day retention | AU-11 | Audit Record Retention | DRAFT | ⟶ corpus |
| Data-at-rest encryption documented (LUKS or equivalent) | SC-28 | Protection of Information at Rest | DRAFT | ⟶ corpus |
| Firewall rules documented, only required ports open | SC-7 | Boundary Protection | DRAFT | ⟶ corpus |
| OS and runtime packages current | SI-2 | Flaw Remediation | DRAFT | ⟶ corpus |
| Deployment authorization documented | CA-6 | Authorization | DRAFT | ⟶ corpus |

---

## 5. Mapping notes (flagged for human confirmation)

- **SA-12 is withdrawn in Rev 5.** The supply-chain check is carried as `SA-12 → SR-3`:
  SA-12 (Supply Chain Protection) was withdrawn in Rev 5 and incorporated into the **SR
  (Supply Chain Risk Management)** family; **SR-3 (Supply Chain Controls and Processes)**
  is the Rev-5 successor. Confirm the team's preferred citation (SR-3 alone, or SR-3 + the
  legacy SA-12 reference for continuity with prior SSP language) at ratification.
- **Enhancement titles** (e.g., SC-7(8), AU-9(2), SC-16(1)) should be confirmed against
  the catalog at ratification — base-control titles are stable; enhancement wording is the
  detail most worth verifying when the corpus lands.
- **Control titles are recorded; controlling text is not yet.** Every `⟶ corpus` cell is a
  deliberate gap, not an omission. The mapping is usable for gating now; the verbatim-text
  grounding is the RAG fast-follow.

---

## 6. Ratification log (append-only — Guarantee #6)

A check-type's mapping moves from `DRAFT` to `RATIFIED` only by a human entry here. One
ratification covers that check-type for all future stories until the mapping changes.
**Append-only**: a changed mapping is a new dated entry, never an edit of a prior one.

| Date | Check / check-set | Ratified by | Decision | Note |
|---|---|---|---|---|
| _(none yet — all rows DRAFT)_ | | | | |
