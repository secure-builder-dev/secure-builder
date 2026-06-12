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

**Started Week 1. Drafted `CLAUDE.md` — the engine constitution.** Clean-room from the
PRD only. It is both the engine's governing law and the file the runtime auto-loads.

- **Honest now-vs-Phase-2 split (§0):** binds today = no self-approval, human approval
  before commit, TDD two-commit, append-only evidence, no AI co-author trailer,
  clean-room/OPSEC security rules. Phase 2 = the automated gate agents (Murat, Sentinel),
  the machine lane-diff script, and the `ci-enforced` merge wall. Their checklists still
  apply today — run by hand.
- **Encoded:** 8 Core Guarantees (§1); agent manifest + activation + the honest lane-
  enforcement split (§2); 7-step lifecycle, routing, mandatory-read protocol marked
  *human-attested not verified*, gate-verification table (§3); the four gate criteria
  incl. the load-bearing manual review + anti-rubber-stamp rules (§4); init variables (§5);
  `GATE_ENFORCEMENT` strength honesty (§6); commit protocol incl. the standing no-AI-
  trailer rule + append-only gate-log update (§7); AI security rules + clean-room rule
  (§8); the no-over-claiming doctrine (§9); governance doc index (§10).
- Committed as F-track (framework). No AI co-author trailer.

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

## What's next (pick up here) — Week 1: the gate definition docs

With the constitution drafted, build the docs it points to (all clean-room from the PRD):

1. **`docs/QUALITY_GATE.md`** — Murat's full criteria (PRD §5.2 / CLAUDE.md §4.2):
   TDD compliance, the per-layer coverage table, negative-test matrix, ATDD, CI stage,
   flaky check, and the exact Murat verdict format.
2. **`docs/DEFINITION_OF_DONE.md`** — the four-gate "done" bar (Quality PASS + Security
   PASS + Manual CLEAR + human APPROVED) plus the commit/handoff obligations.
3. **`docs/STORY_TEMPLATE.md`** — story file structure incl. `### TDD Red-Phase Evidence`
   and `## Gate Results` sections the gates write into.
4. **`docs/architecture/DEPENDENCY_POLICY.md`** — the severity matrix (Critical/High block;
   Medium/Low flag) + IL4 license policy (PRD §5.6).
5. **`docs/security/controls/CONTROLS-MAPPING.md` starter** — static control table for the
   IL4 baseline checks (PRD §5.4), each check → NIST 800-53 Rev 5 control ID. RAG is a
   fast-follow; a curated static mapping is enough to demo.

Then (still Week 1): `gate-log.md` schema + `NEXT_PROMPT*` templates, and the enforcement
mechanics (pre-commit hook: TDD two-commit / secret scan / lint-typecheck-test / no-skip;
lane-enforcement diff script).

**Watch for:** keep marking honestly what's enforced-today vs Phase-2 — don't write docs
that assume Murat/Sentinel exist as automated agents yet. Use only generic placeholders
(`<ACCOUNT_ID>`, `<CERT_ARN>`); never invent real infra.

## Key files

- `CLAUDE.md` — **engine constitution (governing law + auto-loaded).** Drafted this session.
- `SECURE_BUILDER_PRD.md` — the spec / build contract (8 core guarantees in §2) — **LOCKED.**
- `SECURE_BUILDER_BUILD_PLAN.md` — 4-week build plan + evidence/OPSEC strategy.
- `SECURE_BUILDER_PRD_WORKLIST.md` — original refinement worklist (done).
