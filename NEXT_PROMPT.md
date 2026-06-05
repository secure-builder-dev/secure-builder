# NEXT PROMPT — Secure Builder (session handoff)

> Paste this to Claude at the start of the next session. It is self-contained: the
> next session has no memory of the last one. (Memory files under
> `~/.claude/projects/c--dev-secure-builder/memory/` also carry this context.)

---

## Where we are

We're refining **`SECURE_BUILDER_PRD.md`** — the build contract for a **clean-room
rebuild** of my Secure Builder engine (an AI multi-agent code-gen engine that produces
compliant/tested/control-mapped code for DoD secure pipelines to cut the cATO
remediation bottleneck). The design is already proven: I built a "frankenstein" version
at work that generated a 76-story backend that compiled first try. This repo is the
clean, ownable rebuild.

**Hard rule:** clean-room. Build from the PRD spec and my descriptions only — never
paste my work artifacts (CLAUDE.md, ADRs, real boundary/account names). OPSEC: only
aggregate/releasable metrics ever touch this laptop.

**Goal:** demoable clean engine + public repo + 3-min video in ~4 focused weeks, then
run ≥2 real apps through it before I separate (~June 2027), using the platform team's
intake findings as third-party proof. Plan lives in **`SECURE_BUILDER_BUILD_PLAN.md`**.

## What we did last session

Hardened the PRD's honesty/consistency layer — its whole credibility rests on not
over-claiming. Resolved 11 findings + added a guarantee:

- **§2 Core Guarantees:** #4 now RAG-grounded (citation machine-verified, mapping
  human-confirmed); #2 two-tier enforcement; #6 git-history tamper record; #3 covers
  bug fixes; #5 machine-vs-judgment split; #7 softened "never read"; **added #8 — no
  endpoint without negative authorization tests.**
- **§3 Agent Manifest:** completed — added **Sally (UX)**, filled **Paige (tech
  writer)**, clarified Murat (one persona, many test skills), made activation names
  honest (custom agents = Phase-2 builds), operationalized lane enforcement as
  glob-diff.
- **§4/§5/§8/§9/§12:** `ACCEPTED` finding lifecycle state; Android/Gradle supply-chain
  scan; heuristic-check caveats; new **`GATE_ENFORCEMENT`** init variable
  (`ci-enforced`|`local-attested`); IL5 scoped out.
- **§10:** filled the Track-B "rebuild inventory" (what the substrate provides vs.
  what's mine).
- Created **`SECURE_BUILDER_BUILD_PLAN.md`** (4-week plan).

## Decisions locked (don't relitigate)

- Operating mode: **team-owned, single-operator-per-session.**
- RAG corpus is a **fast-follow**, NOT in the 4-week window — static
  `CONTROLS-MAPPING.md` is enough to demo (already proven at work).
- F9 (risk-tiered light/full manual gate): **deferred** to after real review-load data
  (captured in §14 Track A).
- Track B (own orchestration) and Track C (offline/RAG): **out of the 4-week window.**

## What's next (pick up here)

**Finish Week 0 of the build plan, then start Week 1.**

1. **Last PRD item:** sanity-pass the **Glossary (Appendix A)** — add `GATE_ENFORCEMENT`,
   negative-authorization-testing, and confirm every acronym is spelled out. Then
   **STOP editing the PRD** (it's ~done; resist polishing).
2. **Begin Week 1 — governance backbone:** start drafting the fresh **`CLAUDE.md`**
   engine constitution (agent rules, gate sequence §4, routing §4.1, commit protocol,
   AI security rules §11) — built clean-room from the PRD.
3. Open question to decide when I'm fresh: whether to track `_bmad/` and `.claude/`
   (the framework) in git or gitignore them — left untracked for now.

## Key files

- `SECURE_BUILDER_PRD.md` — the spec / build contract (8 core guarantees in §2)
- `SECURE_BUILDER_BUILD_PLAN.md` — 4-week build plan + evidence/OPSEC strategy
- `SECURE_BUILDER_PRD_WORKLIST.md` — original refinement worklist (mostly done now)
