# ADR Log — Secure Builder Engine

> Running record of architectural decisions for the **engine itself** (F-prefix work):
> what was decided, what was rejected, and why. **Append-only** (Guarantee #6); corrections
> are new entries, never edits or deletions — git history is the tamper record. Applications
> built with the engine keep their own ADR logs; this one governs the engine.
>
> **Backfill note.** Earlier engine decisions (e.g., the F-008 two-context build/gate split)
> predate this log and are recorded in git history and in `SECURE_BUILDER_PRD.md` /
> `CLAUDE.md`. Add formal ADR entries here as those decisions are next revisited.

---

## ADR-0001 — Project Contextualization as a prerequisite Phase-0 workflow

- **Status:** Accepted (F-010)
- **Date:** 2026-08-11
- **Deciders:** C.J. Houle (operator / approver)
- **Relates to:** PRD §15, §4.5, §3.2, §3; CLAUDE.md §2.3, §3.5, §2, §3.2
- **Controls touched:** SA-8 (security engineering principles in design), PL-2/PL-8
  (system architecture & intent capture)

### Context

The §4 story lifecycle silently assumes the project's governing context already exists —
the intent an epic is built toward, the `SHALL NOT` rules the gates check against, the
target contracts a story is written to. In a real brownfield onboarding (a LAN → secure-
enclave migration of a beta build), producing that context took roughly a week by hand:
author the document matrix (current state + desired delta + end-state intent), harden
*every* document via gap analysis, generate the epics and stories, pressure-test the
stories back against the matrix to confirm they fulfill build intent, and stand up an
epic-completion cohesion check — all before any code was written. Without automating this
onboarding, the engine cannot be handed to a peer as a standalone tool; the original
context author must stay in the loop.

### Decision

Add a prerequisite **Project Contextualization Workflow (Phase 0)** that guides a user
through producing a build-ready project. It delivers three artifacts: a hardened **document
matrix**, an **intent-traceable backlog**, and per-project **cohesion-gate criteria**.
Specifics:

1. **New agent — Atlas (Contextualization Lead),** the Phase-0 orchestrator (Bob's analogue
   for inception). Owns only `docs/context/**`; **triggers** the lane owners
   (John / Winston / Sentinel) to write governing docs into their own artifacts, preserving
   Guarantee #5.
2. **Document matrix = fixed core + needed-only additions.** The core is always produced; a
   needs-analysis may then recommend *additional* governing docs — **cap 3, target ≤ 2,
   default zero** — and **only** where the recommendation names the specific build failure
   or intent-gap that occurs without the document. If that failure cannot be stated, it is
   not recommended. The cap is a ceiling, never a quota. No fluff.
3. **Two new Phase-0 gates,** both Tori-driven: **Gap-Analysis** (matrix coherence +
   completeness) and **Intent-Traceability** (bidirectional story ↔ intent).
4. **Standing Epic-boundary Cohesion Gate (§4.5).** Fires at every epic completion, on
   every project; the *criteria* are generated per-project during Phase 0 — universal
   mechanism, project-specific content, mirroring the security gate's init-variable
   pattern. Binary `COHERENT` / `DRIFT`; `DRIFT` blocks epic close.
5. **The matrix is loaded, not RAG'd.** It is authoritative per-project intent, loaded into
   agent context via §4.2 mandatory reads. It stays separate from the compliance corpus
   (NIST 800-53 / STIG / SRG), which is external controlling text retrieved to ground
   citations. RAG appears in Phase 0 only as a construction tool over a large brownfield
   source tree.
6. **Reverse-engineering is demoted to current-state pre-fill** (stage 0), OPSEC-filtered
   (§11) and provenance-tagged — an input that reduces authoring load, not the product.

### Alternatives rejected

- **Reverse-engineered codebase ontology as the product.** The initial framing treated a
  codebase ontology (entities/glossary/topology) as the deliverable. **Rejected:** the
  product is the *forward-intent* document matrix + backlog + cohesion gate; extraction is
  only current-state pre-fill.
- **Cohesion gate as opt-in per project.** **Rejected** — intent-integrity is not optional;
  opt-in would let epics close with no drift check. Standing gate with per-project criteria
  instead.
- **Store the matrix in the RAG.** **Rejected** — semantic-retrieval recall failure on an
  intent element (a silently un-retrieved `SHALL NOT`) is a failure a security build cannot
  tolerate; the matrix is loaded deterministically.
- **No new agent (distribute across existing lanes).** **Rejected** — the matrix-as-a-whole,
  the traceability map, and the cohesion criteria have no existing owner; distributing them
  leaves the deliverable homeless and would overload the security gatekeeper with a baseline
  it later judges.

### Consequences

- Phase 0 is Phase-2 automation: build Atlas + the two Phase-0 gates atop existing framework
  skills (project documentation, PRD / architecture / epics creation, gap / implementation-
  readiness checks), orchestrated into one guided flow.
- The §4 story lifecycle gains a standing epic-boundary gate (§4.5).
- Honesty constraints (§9 / PRD §13) apply unchanged: the matrix and backlog are drafts for
  human ratification; the Phase-0 gates are structured self-checks, not proof; ratified ≠
  verified.
- New owned-artifact tree `docs/context/**` (Atlas) is added to the manifest and the §4.2 /
  §3.2 mandatory-read lists.

---

## ADR-0002 — Governance corpus as a read-on-demand git folder, not a vector RAG

- **Status:** Accepted (F-010)
- **Date:** 2026-08-11
- **Deciders:** C.J. Houle (operator / approver)
- **Relates to:** PRD §2 (Guarantee #4), §12.3, §12.4, §14 (Track C), §15.4; CLAUDE.md §2.3;
  `docs/security/corpus/`
- **Controls touched:** CA-2, SA-11 (evidence), plus the full catalog it grounds

### Context

Guarantee #4 requires every security check to cite verbatim controlling text a reviewer can
open. The PRD (Track C) originally framed this as "RAG over a governance-document corpus."
"RAG" implied a vector store to build — embedding infra, an offline embedding model, and
non-deterministic recall — none of which the citation job actually needs, and all of which
are worst-suited to an air-gapped, single-operator target with weaker local models. The
retrieval job is a **keyed lookup by control ID**, and the check→control mapping is
human-confirmed once and cached (`CONTROLS-MAPPING.md`).

### Decision

Implement the corpus as a **version-controlled folder of verbatim source text**
(`docs/security/corpus/`), read on demand and keyed by control ID — not a vector store.

1. **Three-layer split under `docs/security/`:** `corpus/` (verbatim external source, read-
   only) vs. `controls/` (the engine's own baselines + mappings that cite *into* corpus) vs.
   `providers/` (implementation).
2. **Organized by issuing authority:** `nist/`, `disa/`, `owasp/`, `dod/`, plus `crosswalk/`.
   800-53 is stored **one file per family** (`AC.md` … 20 families), each control an anchor.
3. **IL4 vs IL6** represented as baselines/overlays (`sp-800-53b/baseline-moderate-il4.md`,
   `baseline-high-il6.md`, CC SRG overlays, `crosswalk/il4-vs-il6-delta.md`), not duplicated
   control text. **Both baselines stood up from the start** — projects routinely begin IL4
   and migrate to IL6.
4. **Vendored, not fetched:** verbatim text is generated from authoritative machine-readable
   sources (OSCAL for 800-53, XCCDF for STIGs) and committed, so it works offline.
5. **Provenance + currency:** `_source.md` per multi-file source (else a file header) plus a
   master `MANIFEST.md` ledger; git history is the currency record.
6. **Read-on-demand, never prompt-loaded wholesale:** the gate opens the specific control
   file it cites. Semantic/vector search is at most a *later, optional discovery aid* over
   the same files — never the citation path (recall failure on authoritative text is
   unacceptable).

### Alternatives rejected

- **Vector RAG as the foundation.** Rejected — non-deterministic recall on authoritative
  text, offline-infra burden, not needed for keyed lookup; reserve semantic search for
  optional discovery only.
- **"Every regulation I can find."** Rejected — bloat degrades retrieval and currency, and
  stale text is worse than none (§13). Scope to the active tiers/providers; grow deliberately.
- **A formal `RAG_SPEC.md`.** Rejected as over-engineering — a corpus `README.md` +
  `MANIFEST.md` covers scope, sourcing, and currency.

### Consequences

- Full skeleton tree stood up under `docs/security/corpus/` (`STATUS: SKELETON`); **vendoring
  the verbatim text is a follow-on task** (needs OSCAL/XCCDF tooling — unavailable on the
  current clean-room laptop).
- Corpus added to the §8.4 / §10 governance indexes and the §14 / §15.4 wording (RAG framing
  retired in favor of "read-on-demand reference corpus").
- Corpus is **public standards only**; applied provider configs and real values stay out
  (§8/§11).
