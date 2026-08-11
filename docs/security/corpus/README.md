# Security Governance Corpus

Verbatim, authoritative source text for the controls and standards the engine cites
(Guarantee #4). This is a **read-on-demand reference, not a database**: an agent opens the
specific file/control it needs (keyed by control ID) — it is **not** loaded wholesale into
context. The corpus is **shared across all projects** and synced in at start; it is not
built per-project.

## What lives here vs. elsewhere

- **`corpus/` (here)** — verbatim external source text, organized by issuing authority.
  Read-only reference.
- **`../controls/`** — the engine's *own* curated baselines and check→control mappings,
  which cite **into** this corpus (`CONTROLS-MAPPING.md`, `IL4-baseline.md`, `IL6-delta.md`).
- **`../providers/`** — how controls are satisfied per provider (aws/azure/android/tactical).

## Citing

Reference a control by authority + ID, e.g. `nist/sp-800-53r5/controls/AC.md#ac-12`
(NIST SP 800-53r5, AC-12). 800-53 is stored **one file per family** (`AC.md`, `AU.md`, …),
each control an anchor. The check→control mapping is human-confirmed once and cached in
`../controls/CONTROLS-MAPPING.md` — retrieval grounds the *citation*; the *mapping judgment*
stays human (Guarantee #4, PRD §4.4/§13).

## Access pattern (not a vector store)

The security gate **reads the specific control file** it is citing — the same on-demand
file read the agents use for `API_CONTRACT.md`. The full catalog is never stuffed into a
prompt. Semantic/vector retrieval is **not** part of this design and is only ever a *later,
optional* discovery aid (finding a control when its ID is unknown) layered on the same
files — never the citation path (recall failure on authoritative text is unacceptable).

## Vendoring status

Vendored in progress — see `MANIFEST.md` for the authoritative per-source status. As of
2026-08-11:

- **VENDORED:** NIST SP 800-53 Rev 5 (all 20 families, 1,196 controls, from OSCAL); SP 800-53B
  Moderate (IL4) & High (IL6) baselines + IL4→IL6 control delta; DISA Application Security &
  Development STIG V6R4 (286 rules, from XCCDF); OWASP Top 10 (2021), ASVS v5.0, Top 10 for
  LLM Applications v2.0, MASVS v2.
- **SOURCE-NEEDED:** DISA Application SRG, Mobile App STIG, Cloud Computing SRG — the XCCDF
  converter is verified (`scripts/vendor/xccdf-stig-to-md.mjs`); these use a distribution
  path not yet located (the DoD Cyber Exchange catalog is a captcha portal) or are PDF-only
  (CC SRG). Each file names the exact download.
- **SKELETON (deferred):** remaining prose NIST SPs, FIPS 199/200, DoD-AI docs, CNSSP-15 —
  PDF-only; vendored per scope discipline when a citing project needs them.

Verbatim text is *vendored* — generated from the authoritative machine-readable source
(**OSCAL** for 800-53, **XCCDF** for STIGs) and committed so it works offline. **Do not treat
a SKELETON or SOURCE-NEEDED file as authoritative.** Converters live in `scripts/vendor/` and
re-run offline once sources are local.

## Currency & provenance

Every source records its doc ID, revision, and generation method (`_source.md` for
multi-file sources, the file header otherwise). **`MANIFEST.md`** is the master ledger.
Refresh = regenerate from the authoritative source and commit; git history is the currency
record.

## Scope discipline

Carry only what governs the tiers/providers you build for (PRD §12.3). **Not** "every
regulation" — bloat degrades retrieval and currency, and stale text is worse than none
(§13). Projects can move IL4→IL6 mid-life, so both baselines are stood up from the start.

## OPSEC

**Public standards only.** No applied provider configs, real infrastructure values,
POA&Ms, or scan results in this corpus (§8/§11). Those stay out of the repo the agent sees.
