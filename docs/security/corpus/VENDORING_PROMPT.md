# NEXT PROMPT — Vendor the security governance corpus

> Paste this into a fresh session. It is self-contained (the next session has no memory of
> the last). Its single job: **vendor** the `docs/security/corpus/` skeletons — replace them
> with *verbatim* authoritative text generated from official machine-readable sources, with
> provenance, committed so the corpus works offline.

> ## ⚠️ STATUS: PARTIALLY EXECUTED (2026-08-11, commit `336ebf0` `[F-010/framework]`)
>
> **Already done — do not redo:** NIST 800-53r5 (all 20 families, 1,196 controls) · 800-53B
> Moderate/High baselines + the IL4→IL6 delta · DISA ASD STIG V6R4 (286 rules) · OWASP Top
> 10 / ASVS v5.0 / LLM Top 10 v2.0 / MASVS. Converters are written, committed under
> `scripts/vendor/`, and proven against real sources.
>
> **What is left:** the `SOURCE-NEEDED` rows (Cloud Computing SRG — highest value, completes
> the IL4→IL6 overlay; Application SRG; Mobile Application STIG) and the PDF-only
> `SKELETON` prose standards. **`MANIFEST.md` is the authority on status — read it first
> and only work the rows it says are open.** Vendor deferred sources only when an active
> project's tiers/providers actually cite them (scope discipline, ADR-0002).

---

## Read first (governing law — do not skip)

- `CLAUDE.md` (auto-loaded — engine constitution). Note §8 / §8.1 (OPSEC / clean-room;
  PRD §11), §7.1 (no AI co-author trailer), Guarantee #4 (verbatim, citable — never
  paraphrased).
- `docs/security/corpus/README.md` — what the corpus is and the read-on-demand model.
- `docs/security/corpus/MANIFEST.md` — the source/currency ledger you will update.
- `SECURE_BUILDER_PRD.md` §12.3 (authoritative references), §15.4 (corpus vs. matrix).
- `docs/architecture/ADR-LOG.md` ADR-0002 — the decision that shaped this corpus.

## THE ONE HARD RULE — no fabrication

**Every character of control/standard text must come from the official source file. Do NOT
write, paraphrase, summarize, or "reconstruct from memory" any control text.** If the
authoritative source for a file is not available locally, **STOP for that file, mark it
`SOURCE-NEEDED` in the MANIFEST, and list exactly what you need** — do not fill it. A
plausible-but-wrong control is worse than an empty one (PRD §13). This is the whole point of
Guarantee #4: a reviewer must be able to open the cited source and find the exact text.

## Environment constraints

- **Python is available again** — CPython **3.12.13** via `uv`, shims in
  `C:\Users\cjhou\.local\bin` (a shell started before that install has a stale PATH;
  prepend it or restart the shell). This **supersedes** the earlier "no Python on this
  machine" constraint that shaped the existing converters. The committed converters in
  `scripts/vendor/` are **Node `.mjs`** and work — do not rewrite them for its own sake;
  reach for Python only if a *new* source is genuinely easier that way (and keep it
  **stdlib-only**, since Track C is air-gapped).
- Everything must run **offline** once the source files are local.
- Sources are **public standards** — fetching/transferring them is fine (no OPSEC issue).
  But do not hit the network without the operator's go-ahead; if air-gapped, the operator
  places source files in a local `sources/` scratch dir you agree on (never commit raw
  source archives unless asked).

## What "vendored" means per file

Fill the skeleton with verbatim text, then set its provenance (doc ID, revision, retrieved
date, generation method) in the file header / `_source.md`, and flip its row in
`MANIFEST.md` from `SKELETON` → `VENDORED`. Only mark `VENDORED` when the real text is
present.

## Source map & method (by type)

**A. Control catalogs — clean machine conversion (do these first):**
- **NIST SP 800-53 Rev 5** → OSCAL JSON catalog (`usnistgov/oscal-content`,
  `NIST_SP-800-53_rev5_catalog.json`). Write a PS/Node converter: for each control, emit a
  `## <ID> — <title>` section into the matching family file
  (`nist/sp-800-53r5/controls/<FAMILY>.md`), including statement, guidance, and each
  enhancement, followed by `**Provenance:** NIST SP 800-53r5 · <ID> · <rev>`. All 20
  families, all ~1,189 controls + enhancements. Regenerate `catalog-index.md` (ID → file).
- **SP 800-53B baselines (IL4/IL6)** → OSCAL profiles (moderate / high). Emit the control-ID
  membership lists into `nist/sp-800-53b/baseline-{moderate-il4,high-il6}.md`. Derive
  `crosswalk/il4-vs-il6-delta.md` as the High−Moderate set difference (+ SRG overlay once B
  below is done).

**B. STIGs / SRG — XCCDF conversion:**
- DISA **Cloud Computing SRG**, **Application Security & Development STIG**, **Mobile
  Application STIG** → XCCDF XML (DISA STIG library / cyber.mil). Convert each rule to a
  `## <STIG-ID> — <title>` section (severity, check, fix) with provenance. Extract the CC
  SRG's IL2/4/5/6 overlay deltas into `disa/srg/cloud-computing-srg.md`.

**C. Prose standards — obtain official text, convert, cite:**
- NIST SP 800-37/171/161/218/63, FIPS 199/200, SP 800-124/163, AI RMF (AI 100-1), SP
  800-218A; OWASP Top 10 / ASVS / LLM Top 10 / MASVS (official OWASP repos are often
  markdown already); DoD AI ethical principles, RAI pathway, DoDD 3000.09, GenAI guidance;
  CNSSP-15. These have no OSCAL/XCCDF. Vendor the **authoritative controlling text** from the
  official PDF/HTML/markdown, verbatim, with a full citation + source URL in the header. If
  full verbatim is impractical for a given doc, capture the specific controlling
  sections you need to cite and mark status `PARTIAL` with a note — **never** pad with
  invented text.

## Order

Per `MANIFEST.md`: 800-53r5 catalog + 53B baselines (IL4/IL6) → CC SRG overlays → STIGs →
OWASP / DoD-AI / remaining SPs, scoped to the active tiers/providers. Vendor breadth-first
by citation-weight, not alphabetically.

## Definition of done

- Each targeted file contains verbatim source text (spot-check ≥2 controls per major source
  against the official document and record that you did).
- Every touched file has complete provenance; `MANIFEST.md` rows updated (`VENDORED` /
  `PARTIAL` / `SOURCE-NEEDED`), nothing left silently `SKELETON` that you claim to have done.
- The converter script(s) are saved (e.g. `scripts/vendor/`) so refresh is repeatable.
- No OPSEC leakage (public text only; no real infra values); no AI trailer on any commit
  (§7.1); this is **F-prefix** framework work. **Do not commit unless the operator says so**
  — they control commit timing; when they do, use `[F-XXX/corpus] vendor <source>`.

## If you cannot proceed

If sources aren't local and you're told the box is air-gapped: **write the converter(s)
now** against the known OSCAL/XCCDF schemas so they're ready to run the instant the operator
drops the source files in, update the MANIFEST rows to `SOURCE-NEEDED` with the exact
filenames required, and stop. Do not fabricate to appear complete.
