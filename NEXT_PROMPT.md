# NEXT PROMPT — Secure Builder (session handoff)

> Paste this to the agent at the start of the next session. It is self-contained: the
> next session has no memory of the last one. (Memory files under
> `~/.claude/projects/c--dev-secure-builder/memory/` also carry this context.)
>
> **Artifact budget (CLAUDE.md §5.1 rule 1): ≤ 4,000 tokens.** This file is a prompt.

---

## Where we are

We're building the **clean-room rebuild** of my Secure Builder engine — an AI multi-agent
code-gen engine that produces compliant, tested, control-mapped code for DoD secure
pipelines, to cut the cATO remediation bottleneck. The design is already proven: I built a
"frankenstein" version at work that generated a 76-story backend that compiled first try.
This repo is the clean, ownable rebuild.

**The spec is `SECURE_BUILDER_PRD.md`.** `CLAUDE.md` is its operational encoding and is kept
in sync. We are **executing `SECURE_BUILDER_BUILD_PLAN.md`**, still at the **Week 1 → Week 2
boundary** (governance backbone done; agents next).

**Hard rule:** clean-room. Build from the PRD and my descriptions only — never paste my work
artifacts. OPSEC: only aggregate/releasable metrics touch this laptop.

### The end goal, stated plainly (PRD §14)

**100% owned · 100% local · 100% runnable on my laptop (24 GB VRAM).**

- **Owned** = no third-party framework in the **runtime path**. Using BMAD to *build* this is
  Track A working as designed — build-time scaffolding comes down; run-time dependency is what
  must be gone. "Owned" ≠ hand-writing everything: adopt an SDK for the model loop and tools
  (PRD §10.1 Tier 1), own Tiers 2–4.
- **Local** = no network at run time. Models, corpus, and toolchain provisioned and
  hash-verified at base. Real target: complete-airgap codebase modification, forward-deployed
  at a unit in a DDIL environment.
- **Laptop-runnable** = fits `laptop-resident` (24 GB): build on **Devstral Small 2**, gate on
  **Gemma 4**, hot-swapped, never co-resident. **`egpu-70b` / Llama 3.3 70B stays documented
  as an option but is NOT the plan** — it needs a budget increase we don't expect. Do not
  propose removing it from the docs; do not propose buying hardware to fix a design problem.

**The governing consequence:** on fixed 24 GB the model's capability is a *constraint, not a
variable*. **Rigor comes from workflow structure, not from scale.**

## What we did last session (2026-08-11 — commit `900720b`, `[F-013/arch]`)

**1. ADR-0004 — own-coined callsign personas.** Nine of eleven personas carried BMAD's names.
Renamed to callsigns, keeping the two we'd already coined:

Charter (PM) · Scribe (Story Analyst) · Marshal (Scrum Master) · **Atlas** (Contextualization)
· Keystone (Architect) · Prism (UX) · Forge (Dev) · Crucible (Test Architect) · Bastion
(DevSecOps) · **Sentinel** (Security) · Codex (Tech Writer)

Title Case, ungendered (it/its), `agents/manifest.json` is the source of record. Done now
because the gate log is append-only and still empty — Crucible is a literal column header in
`GATE_LOG_SCHEMA.md`. **Personas are now engine IP; the substrate they run on is not.**

**2. ADR-0005 — instruction artifacts are prompts, not documents.** Measured, and the numbers
decided it: `CLAUDE.md` is **~11.8k tokens** and is declared "always in context" for the
security gate; an assembled gate context burns **~20k tokens before seeing any diff**; the
largest 800-53 family file is **~39.2k tokens**, so grounding one citation by opening it
**exceeds the laptop gate model's practical context outright.** Nine authoring rules landed in
**PRD §10.2** and **CLAUDE.md §5.1**. **Rules 1–6 bind now; rules 7–9 are harness behavior
that does not exist yet** and are marked so in CLAUDE.md §0.

**3. `MODEL-PROFILES.md`** gained context budgets, sizing rationale, model ceilings computed
from architecture, and a **deliberately unfilled** supply-side table to be measured on real
hardware. Key finding: **`egpu-70b` has *less* context headroom than `laptop-resident`**
(~20k vs ~40k) — the 70B's weights eat the added VRAM and its KV cache costs 2× per token.
More VRAM buys *judgment*, never *context*.

## Decisions locked (don't relitigate)

- **24 GB laptop ("Predator") is the target.** Llama 3.3 70B stays on the books, unfunded.
- **Keep the models: Devstral Small 2 (build) + Gemma 4 (gate).** Different lineage is the
  bias firewall — **never run Mistral on both sides**, that collapses it.
- **Two-context split is independent review, NOT separation of duties.** Never call it SoD.
- **Loop cap = 3 rounds**, then escalate to human.
- **Promotion (not commit) is the gated event**; local TDD commits are audit evidence.
- **Sentinel authors the gate log**; Marshal owns the `NEXT_PROMPT*` handoffs only.
- **Phase 0 is a prerequisite**, and its output is a *draft* until a human ratifies it.
- **The corpus is a read-on-demand git folder, not RAG** (ADR-0002).
- **No adversarial-nation base weights, ever** (ADR-0003).
- Operating mode: **team-owned, single-operator-per-session.**

## What's next (pick up here)

**0. Verify what actually shipped.** Confirm **Gemma 4** and **Devstral Small 2** exist as
ADR-0003 describes them (Gemma 4 as "31B dense or 26B-A4B MoE"). If a spec differs, the VRAM
and context math in `MODEL-PROFILES.md` changes. Also check whether **Devstral's chat template
relocates the system prompt to the last user turn** — if it does, prefix caching silently
buys nothing. (Gemma having no system role is a non-issue: ~5 lines in the per-model adapter.)

**1. Verify the F-006 gate scripts** — unblocked now (Python 3.12.13 via `uv`; ensure
`C:\Users\cjhou\.local\bin` is on PATH). Smoke-test `check_lanes.py` / `check_tdd.py` /
`secret_scan.py` against real ranges, fix what breaks, then `sh scripts/install-hooks.sh`
**only after they pass** (`pre-commit` is fail-closed). Keep them stdlib-only. **This is the
deterministic layer — every check a script owns is a check the small model never has to be
trusted with.**

**2. HARDEN THE STRUCTURE BEFORE ANY EPICS — this is the priority.** Decision (2026-08-11):
the engine's own structure gets nailed down and pressure-tested *before* a backlog is
generated. This is not a detour — it is **Phase 0's own ordering** (stage 3 Gap-Analysis Gate,
*then* stage 4 backlog). The engine follows the sequence it imposes on everything else.

*Structural decisions that do not yet exist, in dependency order:*
- **The skill-file format** — the keystone. Eleven personas, zero skill files; PRD §10 requires
  a defined format (persona, capabilities, owned artifacts, activation pattern) and it must now
  satisfy §5.1: declared budget, sliceable, self-contained, no runtime-specific syntax.
  Everything in Week 2 blocks on this.
- **The CLAUDE.md slicing map** — which §-slices each agent receives. Determines whether a
  skill file restates a rule or references it. Blocks skill authoring.
- **The check registry** — a gate run is currently prose. Mechanically it is a data file: check
  ID · the single question · input scope · **who answers (script / model / human)** · control ID
  · output schema. This is where the competence taxonomy lives.
- **The harness contract** — §5.1 rules 7–9 assume something assembles context, extracts control
  anchors, and constrains output. Nothing specifies that component's responsibilities.
- **Declared-but-absent docs** — CLAUDE.md §10 category (c) already lists them honestly.

*Pressure-test methods, cheapest first:*
- **Paper dry-run.** Walk one imaginary story end-to-end — dispatch → build → handoff → gate
  context → both gates → manual review → approval → gate log → next handoff — and record every
  point where you cannot actually proceed. Highest yield per hour.
- **Completeness script** (stdlib-only): verify every file path referenced in the docs exists.
  Catches §10 category-(c) drift automatically.
- **Coherence sweep**: docs that contradict each other (F-012 did one; the rename forced another).
- **Falsifiability check**: for each gate, can it actually FAIL? §3.4 has this table for the
  original gates; the newer ones (cohesion, portability) have not been through it.

**3. Then Week 2 — agents — built as decomposed checks, not one big review prompt.** The
design response to a fixed 24 GB substrate:
- **One narrow question per model call**, fanned out — not "review this diff."
- **Script everything decidable**; the model only sees genuine judgment calls.
- **Minimum context per call**: one function + one control's text + one question.
- **Ask adversarially** ("show me the call sequence that breaks this"), never "is this safe?"
- **Ask 3×, require agreement**; disagreement is a flag for the human, not a verdict.
- **A published competence taxonomy** — script-decidable / small-model-judgment / human-only.
  Multi-step auth bypass is human-only *by design*. **The model must be able to say "not my
  call" rather than emit a confident PASS.** This is the load-bearing guardrail.
- **Order fan-out calls to share the longest prompt prefix** (static first, variable last) so
  the KV cache is reused across the many small calls.

## Open items (carried, none blocking)

- **No epic/story backlog exists for building Secure Builder — deliberately deferred.** The
  build plan + F-track commits stand in for one. **Do not generate epics until the structure is
  hardened** (see "What's next" item 2) — operator decision 2026-08-11, and it matches Phase 0's
  own ordering: gap-hardening (stage 3) precedes backlog generation (stage 4). When it is time,
  the move is to run the engine's Phase 0 on itself and produce an intent-traceable backlog,
  including Track B decomposed against PRD §10.1 tiers.
- **CLAUDE.md is ~13,035 tokens — over budget for whole-file injection.** Slicing (rule 2) is
  known work, not a contingency. None done yet.
- **Rule 10 not yet written**: static-prefix-first + prefix-tree call ordering. Agreed useful;
  add to CLAUDE.md §5.1 when Week 2 starts.
- `html-presentations/engine-workflow.html` is now **tracked** — plain-English engine walkthrough
  for onboarding the team. Like the sprint board it is **explanatory, not evidence.** It carries
  the roster, so re-sweep it on any future rename (it was untracked during the F-013 sweep and
  had to be caught by hand).

**Watch for:** mark honestly enforced-today vs Phase-2; independent-review ≠ SoD; forced-read
is stronger than ambient context but not proof of *application*; a `✓` corpus citation means
the text is openable, **not** that the mapping is right; **portable ≠ equivalent** — the
authoring rules ensure instructions *reach* a local model and say nothing about its judgment.
Generic placeholders only; never invent real infra.

## Key files

- `CLAUDE.md` — **engine constitution (governing law, auto-loaded).** §2.3 Phase 0 · §3
  two-context lifecycle · §3.2 Sentinel forced-read · §3.5 cohesion gate · **§5.1 portability**
  · §7 promotion protocol · §8.2 model provenance.
- `SECURE_BUILDER_PRD.md` — the spec. §4 lifecycle · **§10.2 portability** · §11.1 provenance ·
  **§14 end state** · §15 Phase 0.
- `docs/architecture/ADR-LOG.md` — ADR-0001 Phase 0 · 0002 corpus≠RAG · 0003 model provenance ·
  **0004 personas** · **0005 instruction-artifact portability**.
- `docs/architecture/MODEL-PROFILES.md` — `COMPUTE_PROFILE`, context budgets, sizing rationale.
- `docs/security/corpus/` — vendored controlling text; `MANIFEST.md` = what's actually openable.
- `agents/manifest.json` — lanes / owned globs / mandatory reads as data.
- `docs/QUALITY_GATE.md`, `DEFINITION_OF_DONE.md`, `GATE_LOG_SCHEMA.md` — gate docs.
- `html-presentations/sprint-board.html` — checkbox tracker. **Convenience, not evidence.**
