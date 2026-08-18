# F-PREP-07 — `CLAUDE.md` slicing map

## Header  *(Charter — PM lane)*
- **Story ID:** F-PREP-07
- **Epic:** EPIC-PREP — Make the gates real
- **Intent element(s):** IE-4 (portable), IE-5 (runs where it ships)
- **Type:** new ADR
- **Security-sensitive?** No application surface — but it decides which security rules reach
  Sentinel. A slice that drops a rule silently removes a control. Sentinel reviews.
- **Routing:** Keystone → Sentinel

## Mandatory Reads
- [ ] `CLAUDE.md` in full — this story is about its structure
- [ ] `CLAUDE.md` §5.1 rules 1–3 (budget, sliceable, self-contained)
- [ ] `docs/architecture/MODEL-PROFILES.md` — per-profile context budgets
- [ ] `agents/manifest.json` — per-agent mandatory reads

## User Story
As the harness, I need to know which `CLAUDE.md` sections each agent role receives, so that
I can assemble a context that fits the measured budget instead of injecting a constitution
that does not fit.

## The measured problem
`CLAUDE.md` is **~13,035 tokens** — over budget for whole-file injection, and growing. An
assembled gate context already burns ~20k tokens before it sees a single line of diff, and
the `laptop-resident` profile has roughly 40k of usable context total. Meanwhile §3.2 lists
`CLAUDE.md` as "always in context" for Sentinel, which is true of today's runtime and
**false of llama.cpp/Ollama**, which has no auto-load mechanism. Slicing is known work, not
a contingency (§5.1 rule 2). None has been done.

## Acceptance Criteria
- **AC-1 — A per-role slice map exists as data.** For each of the eleven agents, the
  `CLAUDE.md` sections that role receives, in a parseable file (§5.1 rule 4) — not prose.
- **AC-2 — Every slice is measured.** Token count per slice and per assembled role context,
  measured with a stated counting method, recorded against each `COMPUTE_PROFILE` budget in
  `MODEL-PROFILES.md`.
- **AC-3 — Every assembled context fits, with headroom stated.** For `laptop-resident`, each
  role's assembled instruction context fits the measured budget leaving room for the actual
  work (the diff, the control text). A slice map where the instructions fit but nothing else
  does is a FAIL.
- **AC-4 — Slices are self-contained.** No slice depends on a section the role does not
  receive. Where a rule is needed but out-of-slice, it is **restated in one line** (§5.1
  rule 3). → checkable: every `§x.y` cross-reference inside a slice either resolves within
  the role's own slice set or is accompanied by a restatement.
- **AC-5 — No security rule is dropped silently.** §8 security rules and §1 guarantees are
  traced: for each, the roles that must carry it are named, and it appears in each of their
  slice sets. A rule reaching nobody is a blocking finding.
- **AC-6 — Sentinel's "always in context" row is resolved honestly.** §3.2's entry is either
  rewritten as a harness requirement or given a concrete slice set. It must no longer read as
  a property of the environment.
- **AC-7 — Feeds F-PREP-06.** The map states, per role, which rules a skill file **restates**
  versus **references** — the dependency that blocks skill authoring.

## SHALL NOT constraints
- **SHALL NOT** solve the budget by deleting governance from `CLAUDE.md`. Slicing changes
  what is *delivered per role*, never what the constitution *says*. Shrinking the law to fit
  the model is the inverse of the intended design.
- **SHALL NOT** record a token count from a model card or an estimate. Measured, per §5.1.
- **SHALL NOT** edit `CLAUDE.md` itself in this story beyond the §3.2 correction in AC-6 —
  and that edit requires the operator's express permission (standing rule).
- **SHALL NOT** assume usable context equals advertised context. It is a hardware property;
  the KV cache competes with the weights (`MODEL-PROFILES.md`).

## Endpoints touched
N/A.

## Negative authorization tests planned
N/A — non-code story.

## TDD Red-Phase Evidence
`N/A — non-code story.`

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
