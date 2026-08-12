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

**The spec is `SECURE_BUILDER_PRD.md`** — it was locked, and has since been **deliberately
amended** three times (two-context architecture F-008; Phase-0 + corpus F-010; model
provenance F-011). `CLAUDE.md` is the operational encoding and is kept in sync. We are
**executing the build plan** (`SECURE_BUILDER_BUILD_PLAN.md`), still at the **Week 1 →
Week 2 boundary** (governance backbone done; agents next).

**Hard rule:** clean-room. Build from the PRD spec and my descriptions only — never
paste my work artifacts (real CLAUDE.md, ADRs, real boundary/account names). OPSEC: only
aggregate/releasable metrics ever touch this laptop.

**End state (not the current scaffolding):** Claude + BMAD are temporary scaffolding to
prove the design. The target is **own-orchestration (Track B) + local models on owned
hardware (Track C)** — **US/allied open-weight only** under the standing provenance rule
(no adversarial-nation base weights; **Qwen retired** — ADR-0003, CLAUDE.md §8.2, PRD
§11.1): the **build context on Devstral Small 2** (Mistral/FR) and the **gate context on a
different-lineage model — Gemma 4** on the laptop, scaling to **Llama 3.3 70B** on an
external GPU (`COMPUTE_PROFILE`, `docs/architecture/MODEL-PROFILES.md`) — so the bias
firewall is reinforced by different weights, not just different sessions. The real Track-C
target is **complete-airgap codebase modification, forward-deployed at a unit in a DDIL
environment**; SWaP and air-gap simplicity drive hardware picks. Both tracks are
deliberately *out* of the 4-week window, gated on Track A proving the design first.

**Goal:** demoable clean engine + public repo + 3-min video in ~4 focused weeks, then
run ≥2 real apps through it before I separate (~June 2027), using the platform team's
intake findings as third-party proof.

## What we did last session (2026-08-11 — three commits + a cohesion pass)

**1. `336ebf0` `[F-010/framework]` — Phase-0 contextualization workflow + governance corpus**
(ADR-0001, ADR-0002; `ADR-LOG.md` created as the append-only engine ADR log):

- **Atlas**, a new Contextualization Lead persona owning only `docs/context/**`, who
  **triggers** the lane owners (John/Winston/Sentinel) to write the document matrix into
  *their* artifacts so Guarantee #5 lane boundaries hold.
- **Phase 0 is a prerequisite** (CLAUDE.md §2.3, PRD §15): **no story runs** until a
  hardened **document matrix**, an **intent-traceable backlog**, and the project's
  **cohesion-gate criteria** exist *and a human has ratified them.* Matrix = fixed core +
  needed-only additions (**cap 3, target ≤ 2, default zero**, each justified by a named
  build failure). Staged: intake/pre-fill → guided authoring → Gap-Analysis Gate (Tori) →
  backlog (John) → Intent-Traceability Gate (Tori) → cohesion criteria (Atlas).
- **Epic-boundary cohesion gate** (CLAUDE.md §3.5, PRD §4.5) — `COHERENT` / `DRIFT`,
  fires at every epic close, catches intent drift the per-story gates structurally cannot.
- **Governance reference corpus** `docs/security/corpus/` — verbatim controlling text,
  **read-on-demand keyed by control ID, explicitly NOT a vector store / RAG** (ADR-0002).
  **Vendored:** 800-53r5 all 20 families (1,196 controls, from NIST OSCAL) + 53B IL4/IL6
  baselines + the IL4→IL6 delta; DISA ASD STIG V6R4 (286 rules, from XCCDF); OWASP Top 10,
  ASVS v5.0, LLM Top 10 v2.0, MASVS. **Not vendored** (honest, tracked in
  `corpus/MANIFEST.md`): CC SRG / App SRG / Mobile App STIG (`SOURCE-NEEDED`) and the
  PDF-only prose standards (`SKELETON`). Converters in `scripts/vendor/` (Node `.mjs`,
  written before Python was available), re-runnable offline.

**2. `f56496a` + `d2ad293` `[F-011/arch]` — retire Qwen; US/ally open-weight models (ADR-0003)**

- **Standing model-provenance rule** (CLAUDE.md §8.2, now also PRD §11.1): no model whose
  **base weights** originate in a foreign-adversary nation, in the engine or in anything it
  produces. **Binds on base-weight origin, not the uploader** — Western fine-tunes/distills
  of excluded bases are still excluded, **including embedding and reranker models**.
- **`COMPUTE_PROFILE`** init variable (§5 / PRD §9) + `docs/architecture/MODEL-PROFILES.md`:
  `laptop-resident` (24 GB — Devstral Small 2 build / Gemma 4 gate, hot-swapped) vs.
  `egpu-70b` (gate scales to Llama 3.3 70B). The gate profile is a **recorded choice, never
  a silent auto-scale.**
- Deck: `html-presentations/track-c-substrate.html`.

**3. Cohesion pass (this session, uncommitted at handoff time — intended as `[F-012/docs]`)**
— swept the whole project against those three commits and fixed the stale/contradicting
instances: gate-log schema owner (Bob → **Sentinel**) + a new **Epic Cohesion Ledger**;
`CONTROLS-MAPPING.md` de-RAG'd and re-pointed at real corpus anchors; build plan de-RAG'd
and given Phase 0 + Atlas; **Atlas added to both routing tables**; story template gained an
**Intent element** field; DoD gained an **epic-close bar**; `scripts/README.md` documents
`vendor/`; PRD §11.1 (model provenance) + §12.3 (ASD STIG, ASVS/MASVS, C-SCRM basis);
`DEPENDENCY_POLICY.md` §5 (**a model is a dependency** — provenance + weight-license gate);
CLAUDE.md §10 now separates *exists here* / *per-app* / *not yet written*.

**4. Python landed on this box (2026-08-11)** — CPython **3.12.13** via `uv`
(`uv python install 3.12 --default --preview`); shims in `C:\Users\cjhou\.local\bin`, which
precedes the Windows Store stub. **This reverses the constraint the earlier work was built
around.** A shell started before the install has a stale PATH — prepend that dir or restart
the shell. Keep gate scripts **stdlib-only, no pip deps** (Track C is air-gapped; a
uv-managed interpreter is itself an artifact to stage).

**Carried over:** governance docs (F-002…F-005) and `local-attested` enforcement mechanics
(F-006) are built. **⚠️ The F-006 gate scripts are still UNVERIFIED — but no longer
*unverifiable*.** They were committed reviewed-but-unexecuted because nothing could run
them; Python now can. Hooks are still **not installed** and the `pre-commit` hook is
fail-closed, so install them only after the scripts actually pass a smoke test.

## Decisions locked (don't relitigate)

- **Two-context split is independent review, NOT separation of duties.** Never describe
  it as SoD in a README/briefing. Genuine SoD remains the external platform team.
- **Loop cap = 3 rounds**, then escalate to human.
- **Promotion (not commit) is the gated event**; local TDD commits are audit evidence.
- **Sentinel authors the gate log**, live in CW2 + the DONE row on approval. Bob owns the
  `NEXT_PROMPT*` handoffs only.
- **Phase 0 is a prerequisite, not an option** — and its output is a *draft* until a human
  ratifies it. Agent self-ratification is a protocol violation, exactly like self-approval.
- **The corpus is a read-on-demand git folder, not RAG** (ADR-0002). Semantic search is at
  most a later discovery aid, never the citation path.
- **No adversarial-nation base weights, ever** (ADR-0003) — human-confirmed judgment, no
  official approved-model list exists.
- **Track C model split:** Devstral Small 2 (build) / Gemma 4 (gates) → Llama 3.3 70B on
  eGPU; out of the 4-week window.
- Operating mode: **team-owned, single-operator-per-session.**
- **Gitignore the framework** (`_bmad/`, `_bmad-output/`, `.claude/`) — done. Evidence
  schema/templates tracked here; live instances live in the consuming app's repo (OPSEC).
- F9 risk-tiered manual gate, Track B/C: **out of the 4-week window.**

## What's next (pick up here)

**0. Verify the F-006 scripts** — now unblocked (Python 3.12.13 via `uv`; ensure
`C:\Users\cjhou\.local\bin` is on PATH). Smoke-test `scripts/gates/check_lanes.py` /
`check_tdd.py` / `secret_scan.py` against real ranges in this repo, fix what breaks, then
`sh scripts/install-hooks.sh` **only after they pass** (the `pre-commit` hook is
fail-closed and will block every commit if a script errors). Keep them stdlib-only.

**Then Week 2 — Agents — which now must carry the two-context flow *and* Phase 0:**
- **[SLOTTABLE]** Customize built-in personas onto stock skills: John, Winston, Sally,
  Amelia, Paige.
- **[HEADS-DOWN]** Build the custom skills (no stock equivalent): Tori, Bob, **Atlas**
  (Phase-0 workflow — PRD §15; the stock seeds are `bmad-document-project`, PRD/architecture
  creation, epics/stories, implementation-readiness), **Murat** (one persona, cluster of
  test skills), Frank, **Sentinel**. The gate skills must encode:
  - **Sentinel/Murat run in CW2 against the diff only** — wire `NEXT_PROMPT_GATES.md` as
    their entry (template: `docs/templates/NEXT_PROMPT_GATES-template.md`).
  - **Sentinel forced read-and-attest** of all its skill files incl. adversarial testing —
    fill the `<path>` placeholders in the gates template and add those skill paths to
    `Sentinel.mandatory_reads` in `agents/manifest.json` once the files exist.
  - **Control lookup resolves into `docs/security/corpus/`** (family file → `## <ID>`
    anchor), never from memory; `corpus/MANIFEST.md` says what is actually openable.
  - **The capped (3-round) self-healing loop** and Sentinel-authored live gate-log writes.
- **[SLOTTABLE]** Smoke-test each agent in isolation on a throwaway story before wiring.

**Watch for:** keep marking honestly enforced-today vs Phase-2; independent-review ≠ SoD;
forced-read is stronger than ambient context but still not positive proof of *application*;
a `✓` corpus citation means the text is openable, **not** that the mapping is right.
Generic placeholders only; never invent real infra.

## Key files

- `CLAUDE.md` — **engine constitution (governing law + auto-loaded).** §2.3 = Phase 0;
  §3 = two-context lifecycle; §3.2 = Sentinel forced-read; §3.5 = cohesion gate;
  §7 = promotion/commit protocol; §8.2 = model provenance.
- `SECURE_BUILDER_PRD.md` — the amended spec / build contract. §4 = lifecycle,
  §4.5 = cohesion gate, §11.1 = model provenance, §15 = Phase 0.
- `docs/architecture/ADR-LOG.md` — ADR-0001 (Phase 0), ADR-0002 (corpus ≠ RAG),
  ADR-0003 (model provenance).
- `docs/architecture/MODEL-PROFILES.md` — `COMPUTE_PROFILE` binding (Track C).
- `docs/security/corpus/` — vendored controlling text; `MANIFEST.md` = status ledger,
  `VENDORING_PROMPT.md` = how to vendor the rest (no-fabrication rule).
- `docs/templates/NEXT_PROMPT_GATES-template.md` — the CW2 (gate context) entry prompt.
- `docs/QUALITY_GATE.md`, `docs/DEFINITION_OF_DONE.md`, `docs/GATE_LOG_SCHEMA.md` — gate docs.
- `docs/architecture/DEPENDENCY_POLICY.md` — severity matrix, IL4 licenses, model provenance.
- `docs/security/controls/CONTROLS-MAPPING.md` — check → 800-53 control mapping (DRAFT).
- `agents/manifest.json` — §2 lanes/owned_globs/reads as data.
- `SECURE_BUILDER_BUILD_PLAN.md` — 4-week build plan + evidence/OPSEC strategy.
- `html-presentations/sprint-board.html` — persistent checkbox tracker for the backlog
  above (browser `localStorage`; export/import JSON). **Convenience tracker, not evidence**
  — a checked box is not a gate verdict; the gate log and git history remain the audit
  trail. The stale `SECURE_BUILDER_PRD_WORKLIST.md` it replaced was deleted in F-012.
