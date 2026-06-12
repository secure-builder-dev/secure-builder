# GATE_LOG_SCHEMA.md — Gate log structure & update protocol

> **Owner:** Bob (Scrum Master) appends; Sentinel owns the file. **Source of record:**
> `SECURE_BUILDER_PRD.md` §8.1. **Operationalized by:** `CLAUDE.md` §7.2. **Controls
> evidenced:** CA-2 (Control Assessments), SA-11 (Developer Testing).
>
> This file is the **schema** — the tracked, public-safe specification of the gate log's
> structure. The **live gate log** (`_bmad-output/gate-log.md`) lives in the consuming
> app's working repo, where it is tracked so that git history is its tamper record
> (Guarantee #6). It is **not** tracked in this engine repo (`_bmad-output/` is gitignored
> here) because a real app's gate log records real findings and is OPSEC-sensitive — only
> aggregate, releasable metrics ever leave that repo.

The gate log is an **append-only** record of every story that passed the **full** four-gate
sequence. A story appears **only after** Quality PASS + Security PASS + Manual CLEAR +
Human APPROVED. Stories in progress have **no** entries. Nothing is ever edited, deleted,
or retroactively rewritten — corrections are new entries (Guarantee #6).

---

## 1. Three ledgers in one file

### 1.1 Quick Ledger — one row per story

| Date | Story | Murat | Sentinel | Manual Security | Human | Commit |
|---|---|---|---|---|---|---|
| 2026-06-11 | S-001 | PASS | PASS (0 findings) | CLEAR | APPROVED | `<impl-hash>` |

*(row above is an illustrative example, not real data)*

### 1.2 Detailed Ledger — one row per story

Full verdict tuple + risk context:

| Date | Story | Verdict (Murat / Sentinel / Manual / Human) | Blocking | Non-blocking | Gate Results ptr | Risk note | Follow-up owner |
|---|---|---|---|---|---|---|---|
| 2026-06-11 | S-001 | PASS / PASS / CLEAR / APPROVED | 0 | 0 | `stories/S-001#gate-results` | none | — |

The **risk note** is concrete: *what the finding was and why it matters*, not "see above."
A **follow-up owner** is named whenever anything is left open.

### 1.3 Issue Lifecycle Ledger — one permanent history per finding

Every **non-zero** finding gets an Issue ID `GL-YYYY-MM-DD-###` and a permanent lifecycle:
a `DETECTED` event, then **exactly one** terminal event — `REMEDIATED` **or** `ACCEPTED`.

| Issue ID | Event | Date | Gate | Detail | Accepting human (ACCEPTED only) |
|---|---|---|---|---|---|
| GL-2026-06-11-001 | DETECTED | 2026-06-11 | Sentinel | <what the finding was> | — |
| GL-2026-06-11-001 | REMEDIATED | 2026-06-11 | Sentinel (re-gate) | <how it was fixed/verified> | — |

- `DETECTED` records the gate where the finding was found.
- `REMEDIATED` records the gate where the fix was verified.
- `ACCEPTED` records a documented carry-forward / POA&M — the accepting human **and** the
  rationale are mandatory.
- A finding is **never** closed by deletion. An `ACCEPTED` finding later fixed gains an
  **additional** `REMEDIATED` event (it does not replace the `ACCEPTED` row). Lifecycle
  history is permanent.

---

## 2. Verdict vocabulary (Quick Ledger values)

| Token | Meaning |
|---|---|
| **Murat PASS** | Coverage met, TDD two-commit verified, no skipped tests. |
| **Sentinel PASS (0 findings)** | All gate checks clear. |
| **Sentinel PASS (1 non-blocking)** | Passed with a documented carry-forward (see Issue Lifecycle Ledger). |
| **Sentinel PASS (1 remediated)** | Blocking finding caught and fixed in-session before the final verdict. |
| **Manual CLEAR** | Logic-layer review found no auth bypass, IDOR, privilege escalation, or business-rule bypass. |
| **Human APPROVED** | Explicit "approved" in conversation — the only thing that unlocks a commit. |

---

## 3. Update protocol (Bob, after every commit)

After each commit, Bob appends — in this order — and **never** rewrites prior rows:

1. one **Quick Ledger** row;
2. one **Detailed Ledger** row;
3. a **`DETECTED`** row for any new finding;
4. the matching **terminal** row when a prior finding closes — `REMEDIATED` if fixed,
   `ACCEPTED` if carried forward as documented risk (never edit the `DETECTED` row).

Append-only, always. Corrections are new entries. Git history is the tamper record.

---

## 4. Relationship to other artifacts

- Each Detailed Ledger row points at the story file's `## Gate Results` section
  (`STORY_TEMPLATE.md`).
- `ACCEPTED` findings correspond to POA&M items and follow the dependency/severity
  timelines in `DEPENDENCY_POLICY.md` where applicable.
- The gate log is the primary evidence artifact feeding the SSP and the ATO package
  (PRD §12.4) under CA-2 and SA-11.
