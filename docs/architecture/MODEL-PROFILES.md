# Model Profiles — Local Substrate Binding (Track C)

> **Keystone (Architect) lane.** Operational config for the Track-C local substrate: which
> concrete open-weight models fill the build and gate roles, selected by available hardware
> via the `COMPUTE_PROFILE` init variable (CLAUDE.md §5). Decision of record: **ADR-0003.**
> One engine, two profiles — **not** a forked second version.
>
> **Standing provenance rule (CLAUDE.md §8):** every model here is **US / allied-nation
> open-weight**, judged on **base-weight origin, not uploader.** No adversarial-nation base
> (or Western distill/merge thereof), ever — in the engine or in any app it produces. The
> "acceptable origin" judgment is **human-confirmed**, not machine-verified (there is no
> official approved-model list; see ADR-0003).

---

## Why two profiles

The §3 two-context split runs a **build** context (CW1, code-gen) and a separate **gate**
context (CW2, security review). They are **sequential, never concurrent** — CW1 finishes and
writes `NEXT_PROMPT_GATES.md` before CW2 starts — so a single GPU can **hot-swap** between the
two models, and each gets the full VRAM. When a larger GPU is attached, the **gate** scales up
to a 70B model (the §13 capability jump placed exactly where local-model weakness bites
hardest, and where async speed is acceptable); the **build** model stays fast on the internal
GPU.

Build and gate are deliberately **different lineage** (different company + nation + weights) so
the bias firewall is real, not two copies of one model.

---

## `COMPUTE_PROFILE` values

### `laptop-resident` — 24 GB VRAM (mobile / forward-deployed)

| Role | Model | Origin | License | Quant | ~VRAM | Notes |
|---|---|---|---|---|---|---|
| **Build** (CW1) | **Mistral Devstral Small 2** (24B dense) | 🇫🇷 Mistral | Apache-2.0 | Q4_K_M / Q5_K_M | ~14–17 GB | agentic coding; ~35–50 tok/s in-VRAM |
| **Gate** (CW2) | **Google Gemma 4** (31B dense *or* 26B-A4B MoE) | 🇺🇸 Google | Apache-2.0 | Q4_K_M | ~16–20 GB | different lineage; **hot-swapped** after build |
| Utility (opt, off) | Granite 4.1 3B / Gemma 4 E4B | 🇺🇸 | Apache-2.0 | Q4 | ~3 GB | only if a resident orchestration model is wanted |

Both models never resident at once — the gate loads after the build context ends. This is the
**forward / DDIL** profile: one RF-killed machine, simplest air-gap.

### `egpu-70b` — external GPU or dedicated box (garrison / augmented)

| Role | Model | Origin | License | Quant | ~VRAM | Notes |
|---|---|---|---|---|---|---|
| **Build** (CW1) | **Mistral Devstral Small 2** (24B) | 🇫🇷 Mistral | Apache-2.0 | Q4/Q5 | ~14–17 GB | **internal** GPU — stays interactive |
| **Gate** (CW2) | **Llama 3.3 70B** | 🇺🇸 Meta | ⚠️ Llama Community (AUP; not OSI) | Q4_K_M | ~40 GB | **external** GPU (eGPU 48 GB combined, or mini-PC); async, ~4–6 tok/s |

**Llama license caveat:** Llama 3.3 70B **passes the provenance rule** (US-origin) but ships
under Meta's custom Llama Community License (Acceptable-Use Policy + 700M-MAU clause), not an
OSI license. Acceptable for internal DoD tooling; flagged for honesty. If a cleaner license is
later preferred, Apache-2.0 alternatives for the beefy gate: **gpt-oss-120b** (OpenAI, MoE) or
a larger **Gemma 4 / OLMo 3-Think 32B**.

---

## Hardware notes (grounding the quant/VRAM targets)

- **VRAM ≈ params × quant-factor + ~2 GB context.** Q4_K_M ≈ 0.60 · Q5_K_M ≈ 0.73 · Q8_0 ≈
  1.06 GB per 1B params. On 24 GB: ≤14B any quant; 24B at Q4/Q5; 27–32B at Q4 (tight).
- **Offload cliff:** past 24 GB VRAM, weights spill to system RAM (~90 GB/s, ~10× slower than
  the 896 GB/s VRAM). A 70B on the laptop via offload runs ~2–4 tok/s — usable for an **async
  gate**, miserable for interactive build. Hence the 70B gate belongs on a real second GPU.
- **eGPU:** the Thunderbolt link is **not** the decode bottleneck (weights stay resident on the
  card); total VRAM across GPUs is what matters. Combine internal 24 GB + eGPU 24 GB = 48 GB
  for 70B Q4 via **layer split** (never tensor-parallel across the slow link).
- **Dedicated box** (GB10 / Strix Halo, 128 GB unified) can hold **both** models co-resident
  (true parallel two-context) and runs big MoE fast; single-stream dense decode is modest
  (~273 GB/s).

---

## Context budgets (the constraint that binds the instruction artifacts)

**Usable working context is a property of this hardware, not of the model card.** On a fixed
24 GB card the KV cache and the weights compete for the same VRAM: a 24B at Q4_K_M already
takes ~14–17 GB, leaving single-digit GB for cache and overhead. A model advertising a long
context will happily *accept* a prompt this profile cannot actually hold well — so the number
that governs authoring is the **measured** one, recorded here per profile, never the nominal
spec. Long-context retrieval also degrades toward the middle of a window, and does so hardest
on the smaller models — precisely the ones filling these roles.

**Demand side — engine instruction artifacts (measured, current):**

| Artifact | ~Tokens |
|---|---|
| `CLAUDE.md` (whole file) | **~11,800** |
| `CONTROLS-MAPPING.md` | ~2,850 |
| `GATE_LOG_SCHEMA.md` | ~1,600 |
| `DEFINITION_OF_DONE.md` | ~1,480 |
| `DEPENDENCY_POLICY.md` | ~1,460 |
| `QUALITY_GATE.md` | ~1,330 |
| `agents/manifest.json` | ~1,240 |
| `NEXT_PROMPT_GATES-template.md` | ~1,160 |
| `STORY_TEMPLATE.md` | ~1,150 |
| Largest 800-53 family file (`SA.md`) | **~39,200** |

A gate context assembled per CLAUDE.md §3.2 spends **~20k tokens before seeing any diff**, and
one control-family file **exceeds the `laptop-resident` gate budget by itself**. Hence
CLAUDE.md §5.1 rule 7: the harness extracts the `## <ID>` anchor and injects only that
control's text — **an agent never opens a family file.**

**Supply side — measure and record before declaring a profile usable:**

| Profile / role | Model | Quant | Weights VRAM | KV headroom | **Measured usable ctx** | Assembled-context budget |
|---|---|---|---|---|---|---|
| `laptop-resident` build | Devstral Small 2 | Q4_K_M | ~14–17 GB | *(measure)* | *(measure)* | *(set from measured)* |
| `laptop-resident` gate | Gemma 4 | Q4_K_M | ~16–20 GB | *(measure)* | *(measure)* | *(set from measured)* |
| `egpu-70b` gate | Llama 3.3 70B | Q4_K_M | ~40 GB | *(measure)* | *(measure)* | *(set from measured)* |

> **Do not fill this table from model cards.** Measure on the actual kit with the actual quant
> and KV-cache settings, then record. Leaving a cell blank is honest; guessing it is a §9
> over-claim that would silently set the authoring budgets wrong. The per-profile conformance
> test (CLAUDE.md §5.1 rule 9) is what promotes a row from measured to *usable*.

### Sizing rationale — where the gate budget goes

Why the §5.1 authoring rules are sized the way they are. **Left column measured** (byte counts
÷ 4); **right column estimated** — actual savings depend on how aggressively artifacts are
sliced.

| Gate-context component | Now | After §5.1 | Mechanism |
|---|---|---|---|
| `CLAUDE.md` | 13,035 | ~3,000 | Gate loads guarantees + security criteria + gate-log rules + honesty clause, not all 11 sections (rule 2) |
| Sentinel skill files | ~5,000 *(est., unwritten)* | ~3,000 | Authored to a declared budget (rule 1) |
| `CONTROLS-MAPPING.md` | 2,845 | ~800 | Only rows for checks in scope (rule 4) |
| `GATE_LOG_SCHEMA.md` | 1,595 | ~600 | Row formats only |
| `NEXT_PROMPT_GATES.md` | 1,161 | 1,161 | Already lean |
| `DEPENDENCY_POLICY.md` | 1,460 | ~400 | Severity matrix + licenses injected as data (rule 4) |
| `agents/manifest.json` | 1,240 | ~150 | Acting agent's record only |
| **Fixed overhead** | **~26,300** | **~9,100** | **~3×** |
| Story + diff | ~5,500 | ~5,500 | Unchanged — the actual work |
| **Per control citation** | **up to 39,200** | **~600** | **~65×** — anchor extraction (rule 7) |

**A gate run goes from ~70k tokens to ~15k.** The 3× on fixed overhead is worthwhile; the 65×
on citations is the one that decides feasibility. Five citations under the current design is
~196k tokens — not a slow gate, an impossible one. After rule 7 it is ~3k.

### Model ceilings — advertised vs. VRAM-bound

Two ceilings apply, and **the second binds.** Advertised context lengths come from the model
cards (verify per release — the Gemma 4 / Devstral Small 2 figures in particular must be
confirmed against the actual weights used). The VRAM-bound ceiling is computed:

```
KV cache bytes/token = 2 (K,V) × layers × kv_heads × head_dim × bytes_per_element
usable context       ≈ (VRAM − weights − ~1 GB compute buffers) ÷ KV bytes/token
```

| Role | Weights (Q4) | KV per token | Free VRAM | Usable ctx (fp16 KV) | (Q8 KV) |
|---|---|---|---|---|---|
| Devstral 24B on 24 GB | ~15 GB | ~160 KB *(40 layers, 8 kv heads, dim 128)* | ~7 GB | **~40k** | ~80k |
| Llama 3.3 70B on 48 GB | ~40 GB | ~320 KB *(80 layers, 8 kv heads, dim 128)* | ~6.5 GB | **~20k** | ~40k |

> **The counterintuitive result: the `egpu-70b` gate has *less* context headroom than
> `laptop-resident`.** Its weights consume the added VRAM and its KV cache costs 2× per token
> (80 layers vs. 40). A full 128k window on a 70B would need ~40 GB of KV *alone* — unreachable
> on 48 GB. A 70k-token gate run fits **nowhere** in this lineup; a 15k run fits **everywhere**,
> including the 70B at fp16 KV with margin. Gemma's family has used interleaved local/global
> attention specifically to reduce KV cost — if Gemma 4 retains it, the laptop gate is cheaper
> than the table implies. Confirm before relying.

### Performance expectation (estimates — measure and replace)

Built on the decode figures above (~35–50 tok/s Devstral in-VRAM; ~4–6 tok/s 70B on eGPU).
Prompt ingest is roughly linear in prompt size, so the context reduction lands there first.

| | Before (~70k) | After (~15k) |
|---|---|---|
| Laptop gate — ingest | ~35–70 s | ~7–15 s |
| Laptop gate — verdict | ~35 s | ~25 s |
| **Laptop gate total** | **~1–2 min, if it fit** | **~30–40 s** |
| `egpu-70b` gate total | did not fit | **~4–6 min** (async by design) |

**Multiply by the §3 self-healing loop:** worst case is 3 build+gate rounds. Tolerable at ~40 s
per gate; punishing at the pre-§5.1 numbers, and ~20 min worst-case on the 70B — which is why
that profile is specified async, not interactive.

**The quality effect is likely larger than the speed effect and is not quantified here.**
Long-context retrieval degrades toward the middle of a window, worst on smaller models. A 15k
prompt that is nearly all signal should yield better gate judgments than a 70k prompt that is
~75% boilerplate — but that is a hypothesis for the Track-C measurement (§14), not a claim.

### What additional VRAM does and does not buy

Recorded because the sizing above invites the question directly.

- **It does not buy context.** After §5.1 the gate run is ~15k tokens and already fits
  `laptop-resident` with room to spare. Adding a card to reach the 70B *reduces* usable context
  (~20k vs. ~40k at fp16 KV). **More VRAM is not the fix for a context problem** — the
  authoring rules are, and they are free.
- **It buys judgment.** A 70B reasons better than a ~31B, and the gate is exactly where local-
  model weakness bites hardest (§13). If the Track-C measurement shows the laptop gate missing
  findings the frontier gate catches, more capable gate weights are the remedy.
- **Whether that is needed is currently unmeasured.** Buying hardware before the Track-C
  output-quality comparison (§14) is buying a solution to an unquantified problem. Measure the
  gap on an already-working app first — that is the sequencing §14 already specifies.
- **48 GB is the *minimum* viable 70B gate, not a comfortable one.** 70B Q4 weights are ~40 GB,
  leaving ~6.5 GB for KV (~20k fp16). A 15k assembled context plus growth margin is tight;
  Q8 KV cache or >48 GB is what makes it comfortable. Budget accordingly rather than assuming
  +24 GB lands cleanly.
- **SWaP cost is real for the forward profile.** A second GPU is another box, another power
  draw, another item to provision and hash-verify at base. `laptop-resident` is the DDIL
  target *because* it is one machine (see [[ddil-forward-deployment]]); `egpu-70b` is a
  garrison augmentation and the end-state goal (PRD §14) is that the engine runs fully without
  it.

---

## Selection & swap (design-time, per §5)

`COMPUTE_PROFILE` is a **design-time constant set at clone/deploy time**, not a runtime flag.
Changing hardware = a reconfigure step, not a hot toggle.

**The engine never silently auto-scales the gate on hardware presence.** The gate model is
part of the evidence — *which* model judged a story is recorded in the gate-log. If the gate
silently ran Gemma 4 one day and Llama 3.3 70B the next merely because an eGPU happened to be
attached, two runs of the same story could return **different verdicts with nothing explaining
why**, and the gate's *rigor* would depend on undocumented hardware state — exactly the hidden
variability §9 forbids. So the active profile is an **explicit, recorded operator choice**, not
an ambient side effect of what is plugged in.

A launcher helper (PowerShell / Node / stdlib Python) may therefore
**offer, not impose**:

1. **Enumerate GPUs / VRAM** (`nvidia-smi --query-gpu=memory.total`, or CUDA device count).
   Total VRAM ≥ ~40 GB across devices ⇒ `egpu-70b` is *available*.
2. **Prompt the operator to confirm** the profile (e.g., "external GPU detected — run
   `egpu-70b` [gate = Llama 3.3 70B]?"). The human decides; the engine does not.
3. **Start the local server with placement** — point Ollama / llama.cpp at the profile's
   models, pinning the build model to the internal GPU and the 70B gate to the external card
   (`CUDA_VISIBLE_DEVICES` + layer split); fall back to `laptop-resident` (Gemma 4, hot-swapped)
   when no eGPU is present.
4. **Record the active profile** so the gate-log / evidence shows which model actually judged
   the story.

The gate context itself is hardware-agnostic — it loads whatever model the active profile
names; only the launcher touches GPUs, and only the operator selects the profile. In an
air-gapped kit, all profile models are **provisioned and hash-verified at base** before
deployment — nothing is pulled in the field (see [[ddil-forward-deployment]]).

> **Status:** design only. The launcher, the local server wiring, and the gate agents
> (Crucible / Sentinel) are **Phase-2 / Track-C work — not yet built** (CLAUDE.md §0). This
> section is the intended mechanism, not running code.

---

## Provenance ledger (verify current state before relying — model facts move fast)

| Model | Origin | Base-weight nation | License | Provenance verdict |
|---|---|---|---|---|
| Devstral Small 2 | Mistral | 🇫🇷 France (ally) | Apache-2.0 | ✅ human-confirmed |
| Gemma 4 | Google | 🇺🇸 USA | Apache-2.0 | ✅ human-confirmed |
| Llama 3.3 70B | Meta | 🇺🇸 USA | Llama Community (caveat) | ✅ human-confirmed |
| Granite 4.1 / Gemma 4 E4B (utility) | IBM / Google | 🇺🇸 USA | Apache-2.0 | ✅ human-confirmed |
| nomic-embed-text v1.5 (opt embed) | Nomic AI | 🇺🇸 USA | Apache-2.0 | ✅ human-confirmed |

> Verdicts are **human ratifications** against supply-chain principles (SR-3/SR-4/SR-11; SP
> 800-161 C-SCRM), re-confirmed when a model is added or changed. Not an ATO; not machine-
> verified. Source of record for the decision: **ADR-0003.**
