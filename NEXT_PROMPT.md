# NEXT PROMPT — Secure Builder (session handoff)

> Paste this to the agent at the start of the next session. It is self-contained: the
> next session has no memory of the last one. (Memory files under
> `~/.claude/projects/c--dev-secure-builder/memory/` also carry this context.)

---

## Where we are

We're building the **clean-room rebuild** of my Secure Builder engine (an AI
multi-agent code-gen engine that produces compliant/tested/control-mapped code for DoD
secure pipelines to cut the cATO remediation bottleneck). The design is already proven:
I built a "frankenstein" version at work that generated a 76-story backend that compiled
first try. This repo is the clean, ownable rebuild.

**The spec is `SECURE_BUILDER_PRD.md`** — it was locked, and is now **deliberately
amended** for the two-context architecture (see below); CLAUDE.md was kept in sync. We
are **executing the build plan** (`SECURE_BUILDER_BUILD_PLAN.md`), at the **Week 1 →
Week 2 boundary** (governance backbone done; agents next).

**Hard rule:** clean-room. Build from the PRD spec and my descriptions only — never
paste my work artifacts (real CLAUDE.md, ADRs, real boundary/account names). OPSEC: only
aggregate/releasable metrics ever touch this laptop.

**End state (not the current scaffolding):** Claude + BMAD are temporary scaffolding to
prove the design. The target is **own-orchestration (Track B) + local models on owned
hardware (Track C)** — **US/allied open-weight only** under the standing provenance rule
(no adversarial-nation base weights; **Qwen retired** — ADR-0003, CLAUDE.md §8.2): the
**build context on Devstral Small 2** (Mistral/FR) and the **gate context on a
different-lineage model — Gemma 4** on the laptop, scaling to **Llama 3.3 70B** on an
external GPU (`COMPUTE_PROFILE`, `docs/architecture/MODEL-PROFILES.md`) — so the bias
firewall is reinforced by different weights, not just different sessions. Both tracks are
deliberately *out* of the 4-week window, gated on Track A proving the design first.

**Goal:** demoable clean engine + public repo + 3-min video in ~4 focused weeks, then
run ≥2 real apps through it before I separate (~June 2027), using the platform team's
intake findings as third-party proof.

## What we did last session

**Amended the engine for an agentic two-context (build vs. gate) architecture** — commit
**`ede5912` `[F-008/docs]`** (8 files, no AI trailer). The change, mirrored across
`CLAUDE.md` and the (now-amended) `SECURE_BUILDER_PRD.md`:

- **Two context windows per story with an information barrier.** **CW1 (Build):** Bob
  dispatch → Amelia TDD (local working commits) → write `NEXT_PROMPT_GATES.md`. **CW2
  (Gates):** Murat → Sentinel scan the *diff only*, **blind to the builder's reasoning**
  → capped self-healing loop → manual security review + human approval. This is
  **context-isolated independent review** — a fresh set of eyes scans the artifact, not
  the author's justifications.
- **Self-healing loop capped at 3 rounds**, then escalates to a human (anti-runaway +
  anti-Goodhart). Human gates (manual review, approval) are terminal and unchanged.
- **Sentinel forced read-and-attest** (§3.2): Sentinel must open/read each skill file —
  incl. **adversarial testing** — and echo an attestation before judging. Fixes the
  observed failure where it *improvised* a skill instead of executing it.
- **Guarantee #2 re-scoped** "no commit" → "**no promotion**": local TDD commits are
  permitted in CW1 as tamper-evident audit evidence; the gate chain + approval gate
  *promotion* (DONE/push/merge), not the local checkpoint commit.
- **New `NEXT_PROMPT_GATES.md`** intra-story handoff (template added under
  `docs/templates/`; live instance gitignored under `_bmad-output/`).
- **Gate-log authorship fixed Bob → Sentinel** (resolves the §2-manifest vs §7.2
  contradiction — Sentinel already owns the file).
- Framed throughout as **independent review, explicitly NOT internal separation of
  duties** — the honesty doctrine (§9 / PRD §6.1, §13) is preserved intact.

**Carried over from Week 1 (still true):** the governance docs (F-002…F-005) and the
`local-attested` enforcement mechanics (F-006) are built. **⚠️ The F-006 gate scripts
are still UNVERIFIED** — this laptop has **no real Python** (only the Windows Store
stub), hooks are **not installed**, and the `pre-commit` hook is fail-closed.

## Decisions locked (don't relitigate)

- **Two-context split is independent review, NOT separation of duties.** Never describe
  it as SoD in a README/briefing. Genuine SoD remains the external platform team.
- **Loop cap = 3 rounds**, then escalate to human.
- **Promotion (not commit) is the gated event**; local TDD commits are audit evidence.
- **Sentinel authors the gate log**, live in CW2 + the DONE row on approval. Bob owns the
  `NEXT_PROMPT*` handoffs only.
- **Track C model split: Devstral Small 2 (build) / Gemma 4 (gates), scaling to Llama 3.3 70B on eGPU** — US/ally open-weight only, Qwen retired (ADR-0003); target, out of the 4-week window.
- Operating mode: **team-owned, single-operator-per-session.**
- **Gitignore the framework** (`_bmad/`, `_bmad-output/`, `.claude/`) — done. Evidence
  schema/templates tracked here; live instances live in the consuming app's repo (OPSEC).
- RAG corpus, F9 risk-tiered manual gate, Track B/C: **out of the 4-week window.**

## What's next (pick up here)

**0. Verify the F-006 scripts** (still UNEXECUTED — no Python on the box). Install Python,
then smoke-test `scripts/gates/check_lanes.py` / `check_tdd.py` / `secret_scan.py` (see
prior handoff for exact commands), fix anything, optionally `sh scripts/install-hooks.sh`.
Or, if staying air-gapped, port the three checks to POSIX `sh`.

**Then Week 2 — Agents — must now implement the two-context flow:**
- **[SLOTTABLE]** Customize built-in personas onto stock skills: John, Winston, Sally,
  Amelia, Paige.
- **[HEADS-DOWN]** Build the custom skills (no stock equivalent): Tori, Bob, **Murat**
  (one persona, cluster of test skills), Frank, **Sentinel**. The gate skills must
  encode the new mechanics:
  - **Sentinel/Murat run in CW2 against the diff only** — wire the `NEXT_PROMPT_GATES.md`
    handoff as their entry (template: `docs/templates/NEXT_PROMPT_GATES-template.md`).
  - **Sentinel forced read-and-attest** of all its skill files incl. adversarial testing
    — fill the `<path>` placeholders in the gates template, and add those skill paths to
    `Sentinel.mandatory_reads` in `agents/manifest.json` once the files exist.
  - **The capped (3-round) self-healing loop** and Sentinel-authored live gate-log writes.
- **[SLOTTABLE]** Smoke-test each agent in isolation on a throwaway story before wiring.

**Watch for:** keep marking honestly enforced-today vs Phase-2; independent-review ≠ SoD;
forced-read is stronger than ambient context but still not positive proof of *application*.
Generic placeholders only; never invent real infra.

## Key files

- `CLAUDE.md` — **engine constitution (governing law + auto-loaded).** §3 = two-context
  lifecycle; §3.2 = Sentinel forced-read; §7 = promotion/commit protocol.
- `SECURE_BUILDER_PRD.md` — the amended spec / build contract. §4 = two-context lifecycle.
- `docs/templates/NEXT_PROMPT_GATES-template.md` — the CW2 (gate context) entry prompt.
- `docs/QUALITY_GATE.md`, `docs/DEFINITION_OF_DONE.md`, `docs/GATE_LOG_SCHEMA.md` — gate docs.
- `docs/architecture/DEPENDENCY_POLICY.md` — Sentinel severity matrix + IL4 license policy.
- `docs/security/controls/CONTROLS-MAPPING.md` — check → NIST 800-53 control mapping (DRAFT).
- `agents/manifest.json` — §2 lanes/owned_globs/reads as data (Sentinel owns gate-log).
- `SECURE_BUILDER_BUILD_PLAN.md` — 4-week build plan + evidence/OPSEC strategy.
