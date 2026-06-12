# STORY_TEMPLATE.md — Story file structure

> **Lane:** Core governance. **Read by:** John (authoring), Tori (refinement), Amelia
> (implementation), Murat / Sentinel (gates). **Source of record:**
> `SECURE_BUILDER_PRD.md` §4, §5.1, §8.1. **Operationalized by:** `CLAUDE.md` §3, §4.
>
> Copy everything below the line into `docs/stories/S-XXX-<slug>.md` (or
> `F-XXX-<slug>.md` for engine/framework work) and fill it in. The **header** is John's
> lane; **ACs and refinement** are Tori's; the **TDD Red-Phase Evidence** and code are
> Amelia's; the **Gate Results** are written by the gates. A section left as a `TODO`
> placeholder when a gate runs is itself a finding.

---

```markdown
# S-XXX — <short story title>

## Header  *(John — PM lane)*
- **Story ID:** S-XXX
- **Epic:** <epic name / id>
- **Type:** <feature | endpoint | schema change | UI | devsecops | dependency | docs>
- **Security-sensitive?** <yes/no — yes if it touches auth, RBAC, new endpoints, or a
  data boundary. Drives the §4.4 manual-review depth.>
- **Routing:** first agent → then (per CLAUDE.md §3.1)

## Mandatory Reads  *(per CLAUDE.md §3.2 — operator attests these were supplied)*
- [ ] <list the reads required for this story's assigned agent(s)>

## User Story
As a <role>, I want <capability>, so that <outcome>.

## Acceptance Criteria  *(Tori — each AC is named; each maps to ≥1 test by name)*
- **AC-1:** <criterion>
- **AC-2:** <criterion>
- ...

## SHALL NOT constraints  *(business rules the implementation must not violate)*
- <e.g., "a non-admin SHALL NOT reach another tenant's record">

## Endpoints touched  *(required for security-sensitive stories)*
| Endpoint | Who can call it | What stops everyone else |
|---|---|---|
| <METHOD /path> | <role(s)> | <auth + RBAC + ownership scoping> |

## Negative authorization tests planned  *(Guarantee #8 — every endpoint)*
- [ ] 401 (no token)
- [ ] 403 (valid token, wrong role)
- [ ] IDOR (user A cannot reach user B's resource)
- [ ] 400 (malformed / missing / out-of-range input)
- [ ] conflict (uniqueness / mutual-exclusivity under concurrent/duplicate requests)

---

### TDD Red-Phase Evidence  *(Amelia — paste before the impl commit)*
Commit (tests only): `<hash>`  →  `[S-XXX/tests] failing tests for <description>`
```
<first 20–30 lines of the failing-test run output>
```

### Implementation note  *(Amelia)*
Commit (impl only): `<hash>`  →  `[S-XXX/impl] implementation for <description>`
<brief note on approach; any decision that belongs in an ADR goes to Winston, not here>

---

## Gate Results  *(written by the gates — append, do not overwrite)*

### Quality Gate — Murat
```
QUALITY GATE VERDICT [PASS/FAIL]
<full verdict per QUALITY_GATE.md §4>
```

### Security Gate — Sentinel
```
GATE VERDICT [PASS/FAIL] | SECURITY_TIER [IL4/IL6]
open findings: [n]   blocking findings: [n]
<each finding → control ID + cited text reference>
```

### Manual Security Review — human + AI assistant
- Authorization logic: <reviewed — finding | CLEAR>
- Business-rule bypass: <...>
- Multi-step attack chains: <...>
- IDOR: <...>
- Privilege escalation: <...>
- **For security-sensitive stories:** per-endpoint "who can call it / what stops everyone
  else" stated in the reviewer's own words above.
- **Verdict:** [CLEAR | FINDINGS → returned to Amelia]

### Human Approval  *(hard stop — Guarantee #1)*
- **APPROVED by:** <name>  —  <what was reviewed, in their words>
- Final commit: `<hash>`
```

---

## Notes on use

- **Append-only at the gate stages.** Once a `## Gate Results` subsection is written, a
  re-gate adds a new dated entry beneath it — it does not overwrite the prior verdict
  (mirrors the gate-log discipline, Guarantee #6).
- **Non-code stories** (docs, ADRs, pipeline config) are exempt from the TDD Red-Phase
  Evidence and negative-test sections by nature; mark them `N/A — non-code story`.
- A story is **not** "done" and does **not** enter the gate log until all four gates pass
  (see `DEFINITION_OF_DONE.md`).
