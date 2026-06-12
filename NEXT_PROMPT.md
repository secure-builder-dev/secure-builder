# NEXT PROMPT — Secure Builder (session handoff)

> Paste this to Claude at the start of the next session. It is self-contained: the
> next session has no memory of the last one. (Memory files under
> `~/.claude/projects/c--dev-secure-builder/memory/` also carry this context.)

---

## Where we are

We're building the **clean-room rebuild** of my Secure Builder engine (an AI
multi-agent code-gen engine that produces compliant/tested/control-mapped code for DoD
secure pipelines to cut the cATO remediation bottleneck). The design is already proven:
I built a "frankenstein" version at work that generated a 76-story backend that compiled
first try. This repo is the clean, ownable rebuild.

**The spec is done.** `SECURE_BUILDER_PRD.md` is locked (do **not** edit it — resist
polishing). We are **executing the build plan** (`SECURE_BUILDER_BUILD_PLAN.md`), in
**Week 1: the governance backbone.**

**Hard rule:** clean-room. Build from the PRD spec and my descriptions only — never
paste my work artifacts (real CLAUDE.md, ADRs, real boundary/account names). OPSEC: only
aggregate/releasable metrics ever touch this laptop.

**End state (not the current scaffolding):** Claude + BMAD are temporary scaffolding to
prove the design. The target is **own-orchestration (Track B — my own framework from
scratch, replacing BMAD) + local Ollama/Qwen models on owned hardware (Track C)**. Both
are deliberately *out* of the 4-week window, gated on Track A proving the design first.

**Goal:** demoable clean engine + public repo + 3-min video in ~4 focused weeks, then
run ≥2 real apps through it before I separate (~June 2027), using the platform team's
intake findings as third-party proof.

## What we did last session

**Built out the Week 1 governance backbone — all doc artifacts done.** Clean-room from
the PRD only. Four F-track commits:

- **`CLAUDE.md` — the engine constitution** (`F-002`). Governing law + auto-loaded file.
  Honest now-vs-Phase-2 split (§0): binds today = no self-approval, human approval before
  commit, TDD two-commit, append-only evidence, no AI trailer, clean-room/OPSEC; Phase 2 =
  the automated gate agents (Murat, Sentinel), the lane-diff script, the `ci-enforced`
  merge wall. Encodes all of: 8 guarantees, agent manifest, 7-step lifecycle + routing +
  human-attested reads, the four gate criteria, init vars, `GATE_ENFORCEMENT` honesty,
  commit protocol, AI security rules, no-over-claiming doctrine, governance index.
- **Gate docs** (`F-003`): `docs/QUALITY_GATE.md` (Murat), `docs/DEFINITION_OF_DONE.md`,
  `docs/STORY_TEMPLATE.md`, `docs/architecture/DEPENDENCY_POLICY.md` (Sentinel severity
  matrix + IL4 license policy).
- **Evidence docs** (`F-004`): `docs/security/controls/CONTROLS-MAPPING.md` (IL4 baseline
  + IL6/Android/tactical checks → NIST 800-53 Rev 5 IDs; control IDs+titles recorded,
  verbatim text marked corpus-pending = RAG fast-follow; every row DRAFT until human
  ratification; flags SA-12→SR-3 Rev-5 move), `docs/GATE_LOG_SCHEMA.md` (three-ledger
  append-only structure + verdict vocab + update protocol), and the two handoff templates
  under `docs/templates/`.
- All F-track, **no AI co-author trailer.**

**Built the enforcement mechanics** (`F-006`) — the machine-checkable guarantees,
`local-attested` mode. Stdlib-only Python + thin `sh` hooks, works with/without the
`pre-commit` framework, no network deps:
- `agents/manifest.json` — §3 table as data (lanes, `owned_globs`, reads).
- `scripts/gates/check_lanes.py` (Guarantee #5 file-ownership), `check_tdd.py`
  (Guarantee #3 two-commit + msg prefix), `secret_scan.py` (Guarantee #7 backstop).
- `scripts/hooks/{pre-commit,commit-msg}` + `install-hooks.sh` + `.pre-commit-config.yaml`
  + `.gitattributes` (force LF so hooks stay runnable).

**⚠️ The scripts are UNVERIFIED.** This laptop has **no Python installed** (only the
Windows Store stub), so I could not execute the smoke test. The hooks are **not
installed** (committing still works). The `pre-commit` hook is **fail-closed** — it exits
1 if Python is absent — so do **not** run `scripts/install-hooks.sh` until Python is on
the box.

**Resolved a design tension (noted, not relitigated):** the live `gate-log.md` /
`NEXT_PROMPT*` live in `_bmad-output/` which is **gitignored here** — correct, because a
real app's gate log holds sensitive findings (OPSEC) and is tracked in *that app's* repo
where Guarantee #6 (git history = tamper record) holds. So this engine repo tracks the
**schema + templates**, not live instances.

## Decisions locked (don't relitigate)

- Operating mode: **team-owned, single-operator-per-session.**
- **Gitignore the framework** (`_bmad/`, `_bmad-output/`, `.claude/`) — decided, done.
- RAG corpus is a **fast-follow**, NOT in the 4-week window — static
  `CONTROLS-MAPPING.md` is enough to demo (already proven at work).
- F9 (risk-tiered light/full manual gate): **deferred** to after real review-load data
  (captured in §14 Track A).
- Track B (own orchestration) and Track C (offline/local Ollama+Qwen): **out of the
  4-week window**, gated on Track A.
- **`CLAUDE.md` is the source of *operations*; `SECURE_BUILDER_PRD.md` is the source of
  *record*.** Where they differ, the PRD governs and CLAUDE.md is the bug.
- **Evidence schema/templates are tracked here; live instances live in the consuming
  app's repo** (`_bmad-output/` is gitignored — OPSEC).

## What's next (pick up here) — verify the scripts, then Week 2 (agents)

**Week 1 is functionally complete** (governance docs + enforcement mechanics). Two things
before moving on, then Week 2:

0. **Install Python on the build box, then verify the F-006 scripts** (they are
   reviewed but UNEXECUTED — see warning above). Quick smoke test:
   - `python scripts/gates/check_lanes.py --list-agents`
   - `python scripts/gates/check_lanes.py --agent Amelia --range HEAD~1..HEAD`
     (docs-only commit → expect an OUT-OF-LANE finding, exit 1)
   - `python scripts/gates/check_tdd.py --staged-msg "[S-001/tests] x"` (expect OK)
   - `python scripts/gates/secret_scan.py --files README.md` (expect clean)
   Fix anything that surfaces, then optionally `sh scripts/install-hooks.sh`.
   - **Decision deferred:** if you'd rather not depend on Python (air-gap), say so and we
     port the three checks to POSIX `sh`. Otherwise Python stays.

**Then Week 2 — Agents (rebuild the §3 manifest as skills):**
- **[SLOTTABLE]** Customize built-in personas onto stock skills: John (pm), Winston
  (architect), Sally (ux-designer), Amelia (dev), Paige (tech-writer).
- **[HEADS-DOWN]** Build the custom skills from the §7 scaffold: Tori, Bob, Murat (one
  persona, cluster of test skills), Frank, **Sentinel** (the §5.4 checklist + control
  lookup against `CONTROLS-MAPPING.md`). These have no stock equivalent — they're the
  real Week-2 work.
- **[SLOTTABLE]** Smoke-test each agent in isolation on a throwaway story before wiring.
- The §7 agent-builder template scaffold lives at `.github/skills/bmad-agent-builder/
  assets/` per the PRD — confirm where the substrate expects skill files on this setup.

**Watch for:** keep marking honestly what's enforced-today vs Phase-2; the agents read the
governance docs as their mandatory reads (see `agents/manifest.json`). Generic
placeholders only; never invent real infra.

## Key files

- `CLAUDE.md` — **engine constitution (governing law + auto-loaded).**
- `docs/QUALITY_GATE.md`, `docs/DEFINITION_OF_DONE.md`, `docs/STORY_TEMPLATE.md` — gate docs.
- `docs/architecture/DEPENDENCY_POLICY.md` — Sentinel severity matrix + IL4 license policy.
- `docs/security/controls/CONTROLS-MAPPING.md` — check → NIST 800-53 control mapping (DRAFT rows).
- `docs/GATE_LOG_SCHEMA.md` — gate-log structure; `docs/templates/NEXT_PROMPT*` — handoff templates.
- `SECURE_BUILDER_PRD.md` — the spec / build contract (8 core guarantees in §2) — **LOCKED.**
- `SECURE_BUILDER_BUILD_PLAN.md` — 4-week build plan + evidence/OPSEC strategy.
