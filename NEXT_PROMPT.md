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

## What's next (pick up here) — Week 1: enforcement mechanics (the last Week-1 item)

All Week-1 *docs* are done. The remaining item is **code** — the machine-checkable
guarantees from the build plan (this is `local-attested` mode, §9/§6). Two pieces:

1. **Pre-commit hook** — enforces, on the diff being committed:
   - TDD two-commit check (a `[S-XXX/tests]` commit precedes `[S-XXX/impl]` in `git log`);
   - secret scan (block on probable secrets / forbidden files per `CLAUDE.md` §8);
   - lint + typecheck + tests exit 0, no skipped tests, no debug statements.
2. **Lane-enforcement script** — `git diff` touched files vs. each agent's owned-artifact
   globs (§3.2 / `CLAUDE.md` §2.2) → flag out-of-lane changes. (File-ownership dimension
   only; semantic over-reach stays human judgment — don't over-claim.)

**Decisions this needs before writing** (ask the operator):
   - Hook mechanism: plain `.git/hooks` + a tracked `scripts/` dir, or a manager (husky /
     pre-commit)? Engine repo is docs-only today, so the hook is also a **template** App #1
     installs.
   - Language: POSIX `sh` vs Node — affects portability to air-gapped targets.
   - Where agent→glob ownership is declared as data (a tracked `agents.yaml`/JSON the
     lane script reads) vs. hard-coded from the §3 manifest.
   - (If App #1 gets a remote/CI: also wire `ci-enforced` branch-protection — otherwise
     `local-attested` only for now.)

**Watch for:** keep marking honestly what's enforced-today vs Phase-2. Generic
placeholders only (`<ACCOUNT_ID>`, `<CERT_ARN>`); never invent real infra.

## Key files

- `CLAUDE.md` — **engine constitution (governing law + auto-loaded).**
- `docs/QUALITY_GATE.md`, `docs/DEFINITION_OF_DONE.md`, `docs/STORY_TEMPLATE.md` — gate docs.
- `docs/architecture/DEPENDENCY_POLICY.md` — Sentinel severity matrix + IL4 license policy.
- `docs/security/controls/CONTROLS-MAPPING.md` — check → NIST 800-53 control mapping (DRAFT rows).
- `docs/GATE_LOG_SCHEMA.md` — gate-log structure; `docs/templates/NEXT_PROMPT*` — handoff templates.
- `SECURE_BUILDER_PRD.md` — the spec / build contract (8 core guarantees in §2) — **LOCKED.**
- `SECURE_BUILDER_BUILD_PLAN.md` — 4-week build plan + evidence/OPSEC strategy.
