# F-PREP-03 — Lane ownership for the engine's own artifacts

## Header  *(Charter — PM lane)*
- **Story ID:** F-PREP-03
- **Epic:** EPIC-PREP — Make the gates real
- **Intent element(s):** IE-1 (gates executable), IE-3 (script-decidable), IE-6 (real evidence)
- **Type:** schema change / new ADR
- **Security-sensitive?** No application surface — but it changes an **enforcement** model
  (Guarantee #5), so Sentinel reviews it as a control change, not a doc change.
- **Routing:** Keystone (ADR) → Forge (manifest) → Crucible → Sentinel

## Mandatory Reads
- [ ] `docs/architecture/ADR-LOG.md`
- [ ] `agents/manifest.json`
- [ ] `CLAUDE.md` §2 (manifest), §2.2 (lane enforcement, the honest split), §10 (the three path categories)
- [ ] `scripts/gates/check_lanes.py`

## User Story
As the operator, I want the engine's own artifacts to have declared lane owners, so that
`check_lanes.py` produces a meaningful verdict on framework work instead of flagging
essentially every file for every agent.

## The defect
Run against F-013, `check_lanes.py` reports **16 of 17 files out of lane for every single
agent.** No agent in `agents/manifest.json` owns `CLAUDE.md`, `SECURE_BUILDER_PRD.md`,
`SECURE_BUILDER_BUILD_PLAN.md`, `docs/DEFINITION_OF_DONE.md`, `docs/GATE_LOG_SCHEMA.md`,
`docs/STORY_TEMPLATE.md`, `docs/templates/**`, `html-presentations/**`, `scripts/**`, or
`agents/manifest.json` itself.

This is coherent with `CLAUDE.md` §10 — the manifest was written for the **per-app**
artifacts of category (b), while these are category (a) engine files. But the consequence is
that **the lane gate is unusable on the entire F-track**, which is all the work being done
right now. A gate that fires on everything conveys as little as one that fires on nothing.

## Acceptance Criteria
- **AC-1 — Decision is recorded as an ADR.** Keystone writes an ADR stating how engine-own
  artifacts are laned, with the alternatives considered and their consequences. Buried in a
  manifest diff is not acceptable. → verified by the ADR's presence in `ADR-LOG.md`
- **AC-2 — Every tracked engine artifact has exactly one declared owner.** No path in
  category (a) is unowned; no path is owned by two agents. → asserted by a test
- **AC-3 — `check_lanes.py` gives a meaningful verdict on real F-commits.** Re-run against
  F-013, F-015 and F-016: an in-lane commit reports IN-LANE, and a deliberately
  cross-lane commit still reports a finding. → `test_lane_verdict_on_f_track`
- **AC-4 — The manifest stays the single source of record.** The owner set lives in
  `agents/manifest.json` as data (§5.1 rule 4), not in narrative prose. `CLAUDE.md` §2 is
  updated to match, and the two do not disagree.
- **AC-5 — The honest split survives.** Documentation still states plainly that only the
  *file-ownership* dimension is machine-checkable and the *semantic* dimension remains
  reviewer judgment (§2.2). This story must not be written up as "lane enforcement is now
  automated."
- **AC-6 — Multi-lane commits have a stated rule.** F-track commits legitimately touch
  several lanes at once. The ADR states how that is handled — a composite engine lane, a
  per-commit acting-agent declaration, or a recorded exception — rather than leaving it to
  case-by-case judgment.

## SHALL NOT constraints
- **SHALL NOT** solve this by giving one agent a glob that matches everything. That silences
  the gate instead of fixing it, and silencing a gate to make it pass is the failure mode
  this engine exists to prevent.
- **SHALL NOT** claim lane enforcement is fully automated (§2.2, §9).
- **SHALL NOT** let Forge make this decision inside an implementation file — that is
  precisely the semantic lane violation Guarantee #5 describes. The ADR is Keystone's.

## Endpoints touched
N/A.

## Negative authorization tests planned
N/A at the HTTP layer. Equivalent obligation: AC-3 requires a demonstrated **finding**, not
only a demonstrated pass.

## TDD Red-Phase Evidence  *(Forge — manifest/test portion)*
Commit (tests only): `<hash>` → `[F-PREP-03/tests] failing tests for engine lane ownership`
```
<failing run output>
```

## Implementation note
_TBD_

---

## Gate Results

### Quality Gate — Crucible
```
QUALITY GATE VERDICT [ ]
```

### Security Gate — Sentinel
```
GATE VERDICT [ ] | SECURITY_TIER [IL4]
open findings: [ ]   blocking findings: [ ]
```

### Manual Security Review
- Verdict: [ ]

### Human Approval
- **APPROVED by:** _pending_
