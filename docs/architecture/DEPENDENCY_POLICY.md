# DEPENDENCY_POLICY.md — Supply-chain & dependency policy

> **Owner:** Sentinel (Security Gatekeeper). **Read by:** Tori, Amelia, Frank, Sentinel
> (mandatory reads, `CLAUDE.md` §3.2). **Source of record:** `SECURE_BUILDER_PRD.md`
> §5.6, §12.3. **Controls evidenced:** SR-3, SR-5, SI-2, CM-10 (grounded in NIST SP
> 800-161 Rev 1; GPL/AGPL basis 48 CFR § 227.7103).
>
> **Today's reality (Phase 1):** Sentinel is a Phase-2 automated agent (PRD §3.1). Until
> built, this policy is applied by the operator running the scan and the matrix by hand;
> the block/flag decisions and the verdict are recorded the same way.

A new dependency is itself a story routed **Sentinel (DP review) → Amelia** (`CLAUDE.md`
§3.1). No dependency enters the codebase without passing this policy.

---

## 1. Vulnerability severity matrix

| Severity | Action | Timeline |
|---|---|---|
| **Critical** | **Block** — do not ship; update/replace immediately; initiate POA&M if no fix exists | 0 days |
| **High** | **Block** — update/replace before merge; POA&M within 24h if no fix exists | 24 hours |
| **Medium** | **Flag** — document in the PR; update at next maintenance cycle | Next sprint |
| **Low** | **Log** — non-blocking | Quarterly review |

**Merge rule:** PRs with unresolved **critical or high** findings that are **not
POA&M-allowlisted** are blocked from merge — regardless of track. A POA&M entry is a
documented, accepted carry-forward (recorded in the gate log's issue lifecycle as
`ACCEPTED`, with the accepting human and rationale), not a way to silence a finding.

---

## 2. Where the scan runs

- **Web track (`APP_TRACK=web`):** `npm audit` runs in the `quality:lint` CI stage.
- **Android track (`APP_TRACK=android`):** the equivalent SCA — **OWASP Dependency-Check**
  (or equivalent) against the resolved Gradle dependency graph — runs in the same stage,
  applying the **same severity matrix** and the **same block-on-critical/high** rule.

The scan result is part of the Quality/Security evidence for the story; a clean scan is
necessary but not sufficient (the rest of the Sentinel checklist still applies).

---

## 3. License policy (IL4)

| Status | Licenses |
|---|---|
| **Approved** | MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, CC0-1.0 |
| **Prohibited** | GPL-2.0, GPL-3.0, AGPL-3.0 |
| **Requires review** | LGPL (any variant) |
| **Prohibited** | Unlicensed / no license declared |

The GPL/AGPL prohibition rests on government purpose rights (48 CFR § 227.7103): copyleft
terms are incompatible with delivering government-purpose-rights software. An LGPL
dependency is reviewed case-by-case (dynamic-linking boundary, distribution model) before
approval.

---

## 4. Approved-list discipline

- Every new dependency must appear on the approved list before use (Sentinel IL4 baseline
  check: *all new dependencies in approved list* → SA-12, CM-3, SR-3).
- Adding a dependency is a deliberate, reviewed act — not a side effect of an
  implementation story. If Amelia needs a package mid-story, it routes back through
  Sentinel DP review first.
- Transitive dependencies are in scope: the scan evaluates the **resolved** graph, not
  just direct declarations.

---

## 5. Verdict record

For each dependency review Sentinel records:

```
DEPENDENCY REVIEW [APPROVED/BLOCKED] — <package>@<version>
- Vulnerabilities: critical [n] | high [n] | medium [n] | low [n]
- License: <SPDX id> → [approved | prohibited | review]
- Decision basis: <matrix action + any POA&M id>
```

Blocked → the dependency is not added; the story finds another path or a POA&M is opened
with justification. Approved → the package is added to the approved list and the
implementation proceeds.
