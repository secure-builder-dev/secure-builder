# F-PREP-08 — Check registry + competence taxonomy

## Header  *(Charter — PM lane)*
- **Story ID:** F-PREP-08
- **Epic:** EPIC-PREP — Make the gates real
- **Intent element(s):** IE-1 (executable), IE-2 (falsifiable), IE-3 (scripts own decidable checks), IE-4 (portable)
- **Type:** schema change (data file)
- **Security-sensitive?** **Yes** — this file decides which security checks a small model is
  trusted to answer. A misassignment is a control failure.
- **Routing:** Crucible → Sentinel → Keystone (if it needs an ADR)

## Mandatory Reads
- [ ] `CLAUDE.md` §4.2 (quality criteria), §4.3 (security checklist), §3.4 (verification table)
- [ ] `docs/QUALITY_GATE.md`
- [ ] `docs/security/controls/CONTROLS-MAPPING.md`
- [ ] `docs/security/corpus/MANIFEST.md` — what is actually openable
- [ ] `agents/manifest.json`

## User Story
As the harness, I need every gate check as a row of data — one question, one input scope,
one answerer, one control ID, one output schema — so that a gate run is an executable
sequence rather than a prose checklist a model is asked to remember.

## Why this matters
A gate run is currently **prose**. Mechanically it is a table. Making it data is what makes
the fixed 24 GB substrate workable: one narrow question per model call, minimum context per
call, everything decidable pushed to a script, and calls ordered to share a prompt prefix so
the KV cache is reused. Prose cannot be fanned out, cached, or counted.

This file is also where the **competence taxonomy** lives — and that taxonomy is the
load-bearing guardrail of the whole local-model design.

## Acceptance Criteria
- **AC-1 — Registry exists as parseable data** with, per check: check ID, the single
  question, input scope, **answerer**, control ID, output schema, and the failure verdict.
  → `test_registry_parses`
- **AC-2 — Every §4.2 and §4.3 check is present.** No check named in the quality or security
  gate is missing. Coverage is asserted, not eyeballed. → `test_covers_gate_criteria`
- **AC-3 — Answerer is one of exactly three values:** `script`, `model`, `human`. No fourth
  category, no "either". → `test_answerer_enum`
- **AC-4 — Nothing script-decidable is assigned to the model.** Every check a deterministic
  script could answer is assigned `script`. Justification is required for any judgment call
  that stays with the model. → `test_no_scriptable_check_assigned_to_model`
- **AC-5 — Human-only checks are named as such, by design.** Multi-step auth bypass,
  business-rule bypass, and privilege-escalation-by-call-sequence are `human`. These are
  human-only **on purpose**, not because automation is pending (§4.4, §9).
- **AC-6 — The model can decline.** Every `model` check's output schema includes an explicit
  "not my call → escalate" verdict alongside pass/fail. **This is the load-bearing
  guardrail:** the model must be able to say *not my call* rather than emit a confident PASS.
  → `test_model_checks_allow_abstain`
- **AC-7 — Every check traces to a control ID** in `CONTROLS-MAPPING.md`, and each cited
  control's text is **openable** per `corpus/MANIFEST.md`. A check whose source is not
  vendored says so and is never grounded from model memory (Guarantee #4). → `test_control_ids_resolve`
- **AC-8 — Output schemas are constrainable.** Each schema is expressible as a grammar or
  JSON schema at the sampler, so an unparseable verdict is an invalid run rather than
  something to interpret (§5.1 rule 8).
- **AC-9 — Single source of record.** `QUALITY_GATE.md` and `CLAUDE.md` §4 do not duplicate
  the registry's content in a way that can drift; they point at it.

## SHALL NOT constraints
- **SHALL NOT** assign a check to `model` because writing the script is inconvenient. That is
  the exact trade this design exists to refuse (IE-3).
- **SHALL NOT** allow a `model` check whose only outputs are PASS and FAIL (see AC-6).
- **SHALL NOT** cite a control whose text is not openable (Guarantee #4). A plausible-but-
  wrong mapping is worse than none (§9).
- **SHALL NOT** treat a confirmed mapping as re-derivable per story — mappings are
  human-ratified once per check type and cached (Guarantee #4).

## Endpoints touched
N/A.

## Negative authorization tests planned
N/A at the HTTP layer. Equivalent obligation: AC-4 and AC-6 must each be demonstrated by a
failing case, not asserted.

## TDD Red-Phase Evidence
Commit (tests only): `<hash>` → `[F-PREP-08/tests] failing tests for check registry`
```
<failing run output>
```

## Implementation note
_TBD_

---

## Gate Results

### Quality Gate — Crucible
```
QUALITY GATE VERDICT [ ]
```

### Security Gate — Sentinel
```
GATE VERDICT [ ] | SECURITY_TIER [IL4]
open findings: [ ]   blocking findings: [ ]
```

### Manual Security Review
- Verdict: [ ]

### Human Approval
- **APPROVED by:** _pending_
