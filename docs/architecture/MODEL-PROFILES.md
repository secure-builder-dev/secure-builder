# Model Profiles — Local Substrate Binding (Track C)

> **Winston (Architect) lane.** Operational config for the Track-C local substrate: which
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

A launcher helper (PowerShell / Node — **no Python on the clean-room laptop**) may therefore
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
> (Murat / Sentinel) are **Phase-2 / Track-C work — not yet built** (CLAUDE.md §0). This
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
