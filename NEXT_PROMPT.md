# NEXT PROMPT — Secure Builder (session handoff)

> Paste this to the agent at the start of the next session. It is self-contained: the
> next session has no memory of the last one. (Memory files under
> `~/.claude/projects/c--dev-secure-builder/memory/` also carry this context.)
>
> **Artifact budget (CLAUDE.md §5.1 rule 1): ≤ 4,000 tokens.** This file is a prompt.

---

## Read these two rules before you touch anything

1. **You commit three things and nothing else:** the **red-phase** TDD commit
   (`[X-XXX/tests]`, tests demonstrably failing), the **green-phase** implementation commit
   (`[X-XXX/impl]`), and **`NEXT_PROMPT.md`** (this file — keep it current every time).
2. **Everything else is a final commit and it is mine.** Stage it, then give me a review
   packet with **two parts, every time**: (a) a **technical readout** — what changed, which
   files, what verification actually ran, what it found; and (b) a **junior-developer
   explanation that teaches** — what was done, what the code actually looks like, *why* it
   was done that way, and the **rejected alternatives** with why each lost. Then stop.
   **I review, I commit, I push.**
3. **You NEVER push.** Ever — no phrasing, no urgency, no authorization. Also never merge,
   tag, amend, or force-anything. "Finish the task" or "and commit it" is **not**
   authorization for a final commit. Reading git history is always free.
4. **Once the two-context workflow is flowing (F-PREP-12), no edits to settings config or
   governance docs without my express per-edit permission.** Not armed yet, but write as
   if it is close. Governance = `CLAUDE.md`, PRD, build plan, ADR log, gate docs,
   `agents/manifest.json`, `docs/security/controls/**`, skill files, `.claude/settings*`,
   git hooks. **Reading them is always fine.**
5. **Do not propose building a commit-enforcement hook.** Three real apps shipped through
   this framework without one. The control is my eyes on the diff plus the teaching
   writeup — that is deliberate, not a gap.

Also: **run read-only Bash without asking** (navigation, inspection, `git log`/`status`/
`diff`, the gate scripts). Ask only to install, or to modify/add/delete files outside
work I've already scoped. The allowlist is in `.claude/settings.local.json`.

## Where we are

We're building the **clean-room rebuild** of my Secure Builder engine — an AI multi-agent
code-gen engine producing compliant, tested, control-mapped code for DoD secure pipelines,
to cut the cATO remediation bottleneck. The design is already proven: a "frankenstein"
version at work generated a 76-story backend that compiled first try. This repo is the
clean, ownable rebuild.

**Spec is `SECURE_BUILDER_PRD.md`; `CLAUDE.md` is its operational encoding.**

**Hard rule:** clean-room. Build from the PRD and my descriptions only — never paste my
work artifacts. OPSEC: only aggregate/releasable metrics touch this laptop.

### The end goal (PRD §14)

**100% owned · 100% local · 100% runnable on my laptop (24 GB VRAM).** Owned = no
third-party framework in the *runtime* path (adopting an SDK for the model loop is fine —
PRD §10.1 Tier 1). Local = no network at run time; real target is complete-airgap codebase
modification forward-deployed at a unit in a DDIL environment. Laptop-runnable = build on
**Devstral Small 2**, gate on **Gemma 4**, hot-swapped, never co-resident.
**`egpu-70b`/Llama 3.3 70B stays documented but is NOT the plan** — don't propose removing
it, and don't propose buying hardware to fix a design problem.

**Governing consequence:** on fixed 24 GB, model capability is a *constraint, not a
variable*. **Rigor comes from workflow structure, not scale.**

## What changed last session (2026-08-17)

**F-016 `269b88c` — the gate scripts were executed for the first time and had six defects,
three of which defeated the guarantee the script enforces.** Fixed and hooks are now live
and verified: unicode crash on Windows; `secret_scan` scanning CLEAN on a line containing
the word "example" (a real ARN + account id + password slipped through); `check_tdd`
anchoring on the *last* impl commit so a later remediation commit cured a TDD violation;
`fnmatch` giving different lane verdicts per OS; exit-code conflation of finding vs.
config error; hooks resolving the Microsoft Store python shim.

**F-017 `fc64d6c` — EPIC-PREP written.** `docs/epics/EPIC-PREP.md` + 12 stories in
`docs/stories/F-PREP-01..12`. Traceability verified both directions; template conformance
verified; secret scan clean.

**F-016, F-017 and F-018 were reviewed and APPROVED by C.J. Houle on 2026-08-17.** Do not
re-litigate them. Recorded here because the gate log does not exist yet — F-PREP-12 AC-1
creates it, and this line is a stopgap, **not** gate-log evidence. **The IE-1..IE-6 intent
elements in EPIC-PREP are also RATIFIED**; the epic's cohesion criteria are **not**.

**Models verified:** Gemma 4 (Apr 2026, E2B/E4B/26B-A4B MoE/31B dense, Apache-2.0, 256K)
and Devstral Small 2 (Dec 2025, 24B, Apache-2.0, 256K, 68% SWE-bench) match ADR-0003. No
change to `MODEL-PROFILES.md` math. **Still unanswered:** does Devstral's chat template
relocate the system prompt to the last user turn? If so prefix caching buys nothing
(tracked as F-PREP-09 AC-8).

**Decided: the laptop goes dual-boot Ubuntu LTS**, ~1 TB Linux / ~900 GB Windows.
**Nothing installed yet — the disk is untouched.** Real hardware: **RTX 5090 Laptop GPU
(24 GB)**, 64 GB RAM, 2 TB NVMe (~1.79 TB free), UEFI, Acer **PH18-73**.

## Decisions locked (don't relitigate)

- 24 GB laptop is the target; Llama 3.3 70B stays on the books, unfunded.
- **Devstral (build) + Gemma (gate) — different lineage is the bias firewall. Never run
  Mistral on both sides.**
- Two-context split is **independent review, NOT separation of duties.** Never call it SoD.
- Loop cap = 3 rounds, then escalate to human.
- **Promotion is the gated event**; and per rule 1 above, *no commit at all* without review.
- Sentinel authors the gate log; Marshal owns the `NEXT_PROMPT*` handoffs only.
- Phase 0 is a prerequisite; its output is a *draft* until a human ratifies it.
- Corpus is a read-on-demand git folder, **not RAG** (ADR-0002).
- No adversarial-nation base weights, ever (ADR-0003).

## What's next — EXECUTE EPIC-PREP

**Read `docs/epics/EPIC-PREP.md` first.** It has the intent elements, epic-level
SHALL NOTs, scope, the dependency-ordered story table, and the cohesion criteria.

**Start with F-PREP-01 (`docs/stories/F-PREP-01-dual-boot-ubuntu.md`) — dual-boot Ubuntu.**
Bastion's lane. Every story after it produces evidence, and evidence produced on Windows
has to be re-earned; F-016 proved the platform-determinism defect class is real, not
hypothetical. **The partitioning is mine to execute — write the plan, don't run it.**
Gotchas already scoped in the story: Windows will refuse to shrink `C:` near its
free-space figure (unmovable files); Blackwell needs the **open** NVIDIA module variant;
Secure Boot needs MOK enrollment or the module won't load; the PH18-73 has a **MUX switch**
to decide before install; `PredatorSense` has no Linux equivalent (`Linuwu-Sense`).

Then **F-PREP-02** (gate-script test suite — TDD, so *two* review stops) and **F-PREP-03**
(lane ownership ADR). Critical path: 01 → 02 → 04 in parallel with 06 → 07 → 08 → 09.
**F-PREP-12 closes the epic** and arms rule 2 above.

## Open items (carried)

- **The intent elements IE-1..IE-6 and the cohesion criteria in EPIC-PREP are DRAFTS
  awaiting my ratification.** Phase 0 has never been run on Secure Builder itself, so there
  is no ratified document matrix. An agent ratifying them is a protocol violation, same as
  self-approval. **Ask me.**
- **Cohesion criteria belong to Atlas, which doesn't exist.** Charter drafted them so the
  epic is closeable; Atlas must own them once built.
- **Lane gate fires on every multi-lane F-commit.** F-017 is a live instance (Charter owns
  `docs/epics/**`, Scribe owns `docs/stories/**`; their union covers the commit exactly but
  neither is in-lane alone). Accepted exception, recorded in the commit body. F-PREP-03 AC-6
  fixes it — don't "fix" it by widening a glob.
- **`CLAUDE.md` is ~13,035 tokens** — over budget for whole-file injection. F-PREP-07.
- **Rule 10 not yet written**: static-prefix-first call ordering. F-PREP-09 AC-7. Adding it
  to `CLAUDE.md` §5.1 needs my express permission.
- `.claude/settings.local.json` has Windows-specific python paths needing Linux equivalents
  after the migration.
- `html-presentations/engine-workflow.html` carries the persona roster — re-sweep on any
  rename.

**Watch for:** mark honestly enforced-today vs Phase-2; independent-review ≠ SoD;
forced-read is stronger than ambient context but not proof of *application*; a `✓` corpus
citation means the text is openable, **not** that the mapping is right; **portable ≠
equivalent**. Generic placeholders only; never invent real infra.

## Key files

- `CLAUDE.md` — **engine constitution.** §0 enforced-today vs Phase-2 · §2.3 Phase 0 · §3
  two-context lifecycle · §3.2 Sentinel forced-read · §3.5 cohesion gate · §5.1 portability
  · §7 promotion · §8.2 model provenance · §9 no-over-claiming.
- `docs/epics/EPIC-PREP.md` + `docs/stories/F-PREP-*.md` — **the active backlog.**
- `SECURE_BUILDER_PRD.md` — §4 lifecycle · §10.1 Track-B tiers · §10.2 portability · §14 end state · §15 Phase 0.
- `docs/architecture/ADR-LOG.md` — 0001 Phase 0 · 0002 corpus≠RAG · 0003 models · 0004 personas · 0005 portability.
- `docs/architecture/MODEL-PROFILES.md` — `COMPUTE_PROFILE`, context budgets (supply-side table still unfilled — measure on real hardware).
- `scripts/gates/*.py` — the deterministic layer. Hooks installed and live.
- `agents/manifest.json` — lanes / owned globs / mandatory reads as data.
- `docs/security/corpus/MANIFEST.md` — what's actually openable.
