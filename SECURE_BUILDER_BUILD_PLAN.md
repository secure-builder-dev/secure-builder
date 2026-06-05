# Secure Builder — 4-Week Clean-Room Build Plan

**Goal:** a demoable, clean-room-owned engine + clean public repo + 3-min demo video,
built from the PRD spec (never by copying work artifacts), with an evidence pipeline
that captures **platform-team intake findings** from real apps as third-party proof of
cATO-bottleneck reduction.

**Owner:** C.J. Houle · **Target demo-ready:** ~4 focused weeks from 2026-06-04
(buffer to ~Dec 2026 for evidence accumulation before separation ~June 2027).

**The bet:** the design is already proven (frankenstein engine built a 76-story
backend that compiled first-try). This is reproduction from a spec, not invention —
so it should be *faster* than the original 3-week build.

**Rules of the build:**
- Clean-room: rebuild from the PRD + your own knowledge. Do NOT paste work code,
  CLAUDE.md, ADRs, controls mappings, or real boundary/account/network names.
- Track A only. Track B (own the orchestration layer) and Track C (offline/RAG) are
  explicitly out of this window — note them, don't build them.
- Stop polishing the PRD once it's "good enough to build from" (see Week 0).
- Tags: **[HEADS-DOWN]** = focused weekend/evening block · **[SLOTTABLE]** = fits
  around the day job in small pieces.

---

## Week 0 — Cap the spec + scaffold the repo  *(this week, light)*

- [ ] **[SLOTTABLE] Close the open §2 decisions** — the 3 honesty tweaks (#3/#5/#7) +
  decide on Guarantee #8 (negative-authz-test). Reword in your voice.
- [ ] **[SLOTTABLE] Fill §10 orchestration** — list what the current substrate does
  for you that a future port must replace. This is the only PRD section still a stub
  that matters for the build.
- [ ] **[SLOTTABLE] Glossary + final read.** Then STOP editing the PRD.
- [ ] **[SLOTTABLE] Init the clean repo:** folder skeleton, choose init variables for
  App #1 (`APP_TRACK`, `SECURITY_TIER`, `PROVIDER`, `GATE_ENFORCEMENT`), `git init`,
  first commit. Keep it private until packaging (Week 4).

## Week 1 — Governance backbone  *(the engine's constitution)*

- [ ] **[HEADS-DOWN] `CLAUDE.md`** — engine constitution: agent rules, gate sequence
  (§4), routing (§4.1), commit protocol, AI security rules (§11). This is the spine.
- [ ] **[HEADS-DOWN] Gate definition docs:** `QUALITY_GATE.md` (Murat §5.2),
  `DEFINITION_OF_DONE.md`, `STORY_TEMPLATE.md`, `DEPENDENCY_POLICY.md`.
- [ ] **[HEADS-DOWN] `CONTROLS-MAPPING.md` starter** — static control table for the
  IL4 baseline checks (§5.4). RAG corpus is a *fast-follow*, not a blocker — a curated
  static mapping is enough to demo. (RAG = stretch / post-window.)
- [ ] **[SLOTTABLE] `gate-log.md` schema** + handoff-prompt templates (`NEXT_PROMPT*`).
- [ ] **[HEADS-DOWN] Enforcement mechanics (the machine-checkable guarantees):**
  - Pre-commit hook: TDD two-commit check (git log), secret scan, lint/typecheck/test,
    no-skipped-tests. (This is `local-attested` mode from §9.)
  - Lane-enforcement script: `git diff` touched files vs. each agent's owned-artifact
    globs (§3.2) → flag out-of-lane changes.
  - (If App #1 has a remote/CI: also wire `ci-enforced` branch-protection checks.)

## Week 2 — Agents  *(rebuild the manifest as skills)*

- [ ] **[SLOTTABLE] Customize built-in personas** onto stock skills: John (pm),
  Winston (architect), Sally (ux-designer), Amelia (dev), Paige (tech-writer).
- [ ] **[HEADS-DOWN] Build custom skills from the §7 scaffold:** Tori (story analyst),
  Bob (scrum master), Murat (test architect — one persona, cluster of test skills),
  Frank (DevSecOps), **Sentinel** (security gatekeeper — the §5.4 checklist + control
  lookup against `CONTROLS-MAPPING.md`).
- [ ] **[SLOTTABLE] Smoke-test each agent** in isolation on a throwaway story before
  wiring them together.

## Week 3 — Wire + first real run  *(prove the clean version reproduces the behavior)*

- [ ] **[HEADS-DOWN] Drive App #1 through the full §4 lifecycle** for 5–10 real
  stories: dispatch → implement → Murat → Sentinel → manual review → approval → commit
  → handoff. Fix orchestration friction as it surfaces.
- [ ] **[HEADS-DOWN] Confirm the gates actually fire:** TDD two-commit enforced,
  coverage measured on the diff, Sentinel catches a real planted issue, gate-log fills,
  handoff prompts carry context to a fresh session.
- [ ] **[SLOTTABLE] Capture friction notes** → feed back into §10 (the "what to rebuild"
  list) for the future Track B port.

## Week 4 — Instrument, package, evidence

- [ ] **[HEADS-DOWN] Metrics instrumentation:** gate pass/fail, findings count by
  severity, coverage, TDD compliance — summarized from the gate-log. This is what
  produces the value-prop numbers.
- [ ] **[HEADS-DOWN] Clean public repo:** README that opens with the **cATO problem**
  (not the tech), the sanitized PRD, an architecture overview, a quickstart.
- [ ] **[HEADS-DOWN] 3-minute demo video:** one story going story → failing test →
  impl → quality gate → security gate → control-mapped → human approval → commit, with
  the gate-log filling in live. The single most valuable interview artifact.
- [ ] **[SLOTTABLE] Stand up the evidence pipeline** (see below).

---

## Evidence strategy — the third-party proof (the long pole)

The differentiator isn't "it compiles" — it's **the platform team's intake findings**.
Two real apps built with the engine, with the platform's pipeline findings as
*independent* proof.

- [ ] For each app, record **aggregate** intake results: finding counts by severity,
  control-mapping gaps, POA&M items, and remediation-cycle time.
- [ ] Get a **baseline** to compare against (an app NOT built with the engine, or your
  team's historical norm) — "N → M findings" needs both numbers.
- [ ] **Capture the work-POC metrics NOW** — you can't reconstruct them after you
  separate. This has a hard deadline tied to your exit.

### ⚠️ OPSEC guardrail on evidence (read before exporting anything)
Pipeline findings from a secure network can themselves be sensitive — they describe
real vulnerabilities in a real system on a classified perimeter. **Only ever take
aggregate, releasable metrics off the network** (counts, severities, categories,
cycle-time) — never raw findings, system names, or boundary identifiers. When unsure
whether a number is releasable, leave it out. Confirm with your security office that
even the aggregate metrics are cleared for release before they touch this laptop.

---

## Explicitly NOT in this window (so scope stays honest)
- Track B — owning the orchestration layer (build only after the design is proven
  clean here).
- Track C — offline/air-gapped model + full RAG corpus. (Static `CONTROLS-MAPPING.md`
  stands in for RAG during the window.)
- The risk-tiered light/full manual gate (F9) — revisit after real review-load data.
- IL5 tier, additional providers — add when actually needed.
