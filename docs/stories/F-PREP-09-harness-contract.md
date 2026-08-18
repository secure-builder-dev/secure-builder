# F-PREP-09 — Harness contract specification

## Header  *(Charter — PM lane)*
- **Story ID:** F-PREP-09
- **Epic:** EPIC-PREP — Make the gates real
- **Intent element(s):** IE-1 (executable), IE-4 (portable), IE-5 (runs where it ships)
- **Type:** new ADR
- **Security-sensitive?** **Yes** — the harness decides what controlling text reaches the
  security gate. A retrieval bug is a silent control failure. Sentinel reviews.
- **Routing:** Keystone → Sentinel

## Mandatory Reads
- [ ] `CLAUDE.md` §5.1 rules 7–9 (the harness behaviors that do not exist yet), §0
- [ ] `SECURE_BUILDER_PRD.md` §10 (orchestration requirements), §10.1 (Track-B tiers), §10.2
- [ ] `docs/architecture/ADR-LOG.md` ADR-0002 (corpus ≠ RAG), ADR-0005
- [ ] `docs/architecture/MODEL-PROFILES.md`

## User Story
As the engine, I need the harness's responsibilities specified, so that the rules already
written against it — deterministic context assembly, control-anchor extraction, constrained
verdict decoding — have a component that owes them.

## The gap
`CLAUDE.md` §5.1 rules 7–9 describe behavior that **does not exist**, and §0 marks it so.
Nothing specifies the component that would provide it. Three concrete obligations are
currently owed to nobody:

1. **Deterministic context assembly** — select and inject the slices a role needs, with no
   reliance on a runtime that auto-loads a constitution, failing loudly when the assembled
   context exceeds the measured budget rather than silently truncating.
2. **Control-anchor extraction** — slice the `## <ID>` anchor and inject **only** that
   control's text. An agent never opens a control-family file. *(The largest 800-53 family
   file is ~39.2k tokens — opening one to ground a single citation exceeds the laptop gate
   model's practical context outright.)*
3. **Constrained verdict decoding** — enforce the §4.2/§4.3 verdict formats at the sampler,
   so an unparseable verdict is an **invalid run** that re-runs, not a judgment to interpret.

## Acceptance Criteria
- **AC-1 — Responsibilities are enumerated** as a contract: inputs, outputs, failure modes,
  and what the harness explicitly does **not** own.
- **AC-2 — All three obligations above are covered**, each with a stated failure behavior.
- **AC-3 — Fail-loud is specified, not implied.** Over-budget assembly and unparseable
  verdicts both produce an explicit invalid-run signal. Silent truncation is named as the
  prohibited behavior it is.
- **AC-4 — ADR-0002 is preserved.** The corpus stays a read-on-demand git folder keyed by
  control ID, **not** a vector store. This story makes retrieval deterministic *code*; it
  does not introduce RAG.
- **AC-5 — Per-model adapter boundary is drawn.** Chat templates and tool-call encodings live
  in a thin adapter, never in a skill file (§5.1 rule 6). The contract says what the adapter
  owns.
- **AC-6 — Mapped to PRD §10.1 tiers.** Each responsibility is placed in the Track-B tier
  that will own it, so the eventual port is a known target. Adopt-vs-build is stated per item
  (Tier 1 is adopt, not hand-build).
- **AC-7 — Prefix-caching order is specified.** Fan-out calls are ordered static-prefix-first
  so the KV cache is reused across many small calls. *(This is the unwritten "rule 10"; if it
  belongs in `CLAUDE.md` §5.1, that edit needs the operator's express permission.)*
- **AC-8 — The Devstral chat-template question is answered.** Whether Devstral Small 2's
  template relocates the system prompt to the last user turn is **verified**, because if it
  does, prefix caching silently buys nothing and AC-7 is void. Answer recorded with its source.
- **AC-9 — Conformance test defined.** §5.1 rule 9's per-profile conformance test is
  specified concretely enough to run once a profile exists.

## SHALL NOT constraints
- **SHALL NOT** introduce a vector store or embedding model (ADR-0002). Any embedding model
  would additionally face the §8.2 provenance gate.
- **SHALL NOT** let the harness silently truncate an over-budget context. Silent truncation
  produces a confident verdict from a model that never saw the rule.
- **SHALL NOT** build the harness in this story. This is the contract; implementation is
  Track B / Phase 2.
- **SHALL NOT** report a passing conformance test as evidence the local gate is as strong.
  Rule 9 proves the instructions *arrived*, nothing about the rigor of the judgment (§5.1).

## Endpoints touched
N/A.

## Negative authorization tests planned
N/A — non-code story.

## TDD Red-Phase Evidence
`N/A — non-code story.`

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
