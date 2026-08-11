# Corpus Manifest — Source & Currency Ledger

Master list of every source in `corpus/`, its authoritative document ID, revision, and
vendoring status. This is the "is it current?" answer at a glance. Append/update a row when
a source is added, vendored, or refreshed; git history is the tamper/currency record
(Guarantee #6). All entries are **public** standards (§11 OPSEC).

> **Legend — Status:** `SKELETON` = structure only, text not yet vendored ·
> `VENDORED` = verbatim text generated from source and committed · `PARTIAL` = only the
> cited sections vendored (noted per row) · `SOURCE-NEEDED` = vendoring attempted but the
> authoritative source could not be obtained non-interactively; converter is ready and the
> exact needed artifact is named in the file · `STALE` = source revision superseded, refresh due.

> **Vendored on 2026-08-11** (F-corpus). Converters live in `scripts/vendor/` and are
> re-runnable offline once sources are local. See the **Vendoring log** at the bottom.

## NIST

| Path | Document | Revision | Gen source | Status |
|---|---|---|---|---|
| `nist/sp-800-53r5/controls/*.md` | SP 800-53 Rev 5 — Security & Privacy Controls | **5.2.0** (OSCAL 1.2.2) | OSCAL JSON | **VENDORED** |
| `nist/sp-800-53b/baseline-moderate-il4.md` | SP 800-53B — Moderate baseline (IL4), 287 controls | Rev 5 (5.2.0) | OSCAL profile | **VENDORED** |
| `nist/sp-800-53b/baseline-high-il6.md` | SP 800-53B — High baseline (IL6), 370 controls | Rev 5 (5.2.0) | OSCAL profile | **VENDORED** |
| `nist/sp-800-37r2-rmf.md` | SP 800-37 Rev 2 — RMF | Rev 2 | PDF | SKELETON *(deferred — PDF; vendor when a citing project needs it)* |
| `nist/sp-800-171-cui.md` | SP 800-171 — CUI | Rev 2/3 *(confirm)* | OSCAL/PDF | SKELETON *(deferred)* |
| `nist/sp-800-161r1-supply-chain.md` | SP 800-161 Rev 1 — C-SCRM | Rev 1 | PDF | SKELETON *(deferred)* |
| `nist/sp-800-218-ssdf.md` | SP 800-218 — SSDF | v1.1 | PDF | SKELETON *(deferred)* |
| `nist/sp-800-63-digital-identity.md` | SP 800-63 — Digital Identity | Rev 3/4 *(confirm)* | PDF | SKELETON *(deferred)* |
| `nist/fips-199-200.md` | FIPS 199 & 200 — Categorization / Min. Reqs | — | PDF | SKELETON *(deferred)* |
| `nist/mobile/sp-800-124r2-device.md` | SP 800-124 Rev 2 — Mobile Device Security | Rev 2 | PDF | SKELETON *(deferred — Android track)* |
| `nist/mobile/sp-800-163r1-app-vetting.md` | SP 800-163 Rev 1 — Mobile App Vetting | Rev 1 | PDF | SKELETON *(deferred — Android track)* |
| `nist/ai/ai-rmf-100-1.md` | AI 100-1 — AI RMF | 1.0 | PDF | SKELETON *(deferred)* |
| `nist/ai/sp-800-218a-genai-ssdf.md` | SP 800-218A — SSDF for Generative AI | — | PDF | SKELETON *(deferred)* |

## DISA

| Path | Document | Revision | Gen source | Status |
|---|---|---|---|---|
| `disa/stigs/application-security-dev.md` | Application Security & Development STIG — 286 rules | **V6R4** (01 Oct 2025) | XCCDF | **VENDORED** |
| `disa/srg/cloud-computing-srg.md` | DoD Cloud Computing SRG (IL2/4/5/6) | v1r4 *(confirm)* | PDF | **SOURCE-NEEDED** *(PDF, not XCCDF — extract cited sections)* |
| `disa/srg/application-srg.md` | Application SRG | *(confirm)* | XCCDF | **SOURCE-NEEDED** *(direct-download path not located)* |
| `disa/stigs/mobile-application.md` | Mobile Application STIG | *(confirm)* | XCCDF | **SOURCE-NEEDED** *(Android track — direct-download path not located)* |

> The public.cyber.mil download *catalog* is a Salesforce/reCAPTCHA portal (not scriptable),
> but individual archives are direct-downloadable from
> `dl.dod.cyber.mil/wp-content/uploads/stigs/zip/U_<SHORT>_V<v>R<r>_STIG.zip`. The ASD STIG
> was vendored this way (`U_ASD_V6R4_STIG.zip`; V6R5/V7 return 404, so V6R4 is current). The
> Application SRG and Mobile App STIG use a different short code/path not yet located; the CC
> SRG is PDF-only. Converter: `scripts/vendor/xccdf-stig-to-md.mjs` (verbatim-only, verified
> against ASD V6R4).

## OWASP

| Path | Document | Revision | Gen source | Status |
|---|---|---|---|---|
| `owasp/top-10.md` | OWASP Top 10 | 2021 | `OWASP/Top10`@`66ebc4798d2c` | **VENDORED** |
| `owasp/asvs.md` | Application Security Verification Standard | **v5.0** | `OWASP/ASVS`@`cdc8a0f68ac2` | **VENDORED** |
| `owasp/llm-top-10.md` | Top 10 for LLM Applications | **v2.0 (2025)** | `OWASP/www-project-top-10-for-large-language-model-applications`@`99f4395589bd` | **VENDORED** |
| `owasp/masvs.md` | Mobile App Security Verification Standard | **v2** | `OWASP/masvs`@`c0db792d4820` | **VENDORED** |

## DoD AI & Crypto

| Path | Document | Revision | Gen source | Status |
|---|---|---|---|---|
| `dod/ai/ai-ethical-principles.md` | DoD AI Ethical Principles | 2020 | PDF | SKELETON *(deferred)* |
| `dod/ai/responsible-ai-strategy-pathway.md` | Responsible AI Strategy & Impl. Pathway | 2022 | PDF | SKELETON *(deferred)* |
| `dod/ai/dodd-3000-09-autonomy.md` | DoD Directive 3000.09 | 2023 | PDF | SKELETON *(deferred)* |
| `dod/ai/generative-ai-guidance.md` | DoD/CDAO Generative-AI guidance | *(confirm)* | PDF | SKELETON *(deferred)* |
| `dod/cnssp-15-crypto.md` | CNSSP-15 — Crypto (FIPS 140-3) | *(confirm)* | PDF | SKELETON *(deferred)* |

## Deferred vendoring — LATER ITEM (not done yet)

> **Backlog marker (2026-08-11).** The sources below are **not vendored** and are parked for
> a later work item — do not treat their skeletons as authoritative. Vendor them only when an
> active project's tiers/providers actually cite them (scope discipline, ADR-0002). Grouped by
> how they'd be vendored:
>
> - **PDF-only (need human-confirmed verbatim extraction; no clean machine source):**
>   Cloud Computing SRG · SP 800-37r2 · SP 800-161r1 · SP 800-218 · SP 800-63 · FIPS 199/200 ·
>   SP 800-124r2 · SP 800-163r1 · AI RMF 100-1 · SP 800-218A · DoD AI Ethical Principles ·
>   RAI Pathway · DoDD 3000.09 · DoD/CDAO GenAI guidance · CNSSP-15. **Highest near-term value:
>   Cloud Computing SRG** (completes the IL4→IL6 crosswalk overlay).
> - **XCCDF (converter ready — just need the archive path):** Application SRG, Mobile App STIG.
> - **Possibly OSCAL (avoids PDF):** SP 800-171 (rev 3 has an OSCAL representation).

## Derived

| Path | Document | Basis | Status |
|---|---|---|---|
| `crosswalk/il4-vs-il6-delta.md` | IL4→IL6 baseline delta (+83 controls at IL6) | 800-53B High−Moderate (SRG overlay pending CC SRG) | **PARTIAL** *(control delta done; SRG overlay pending)* |

---

**Vendoring order (suggested):** 800-53r5 catalog + 53B baselines (IL4/IL6) first — they
carry the most citations — then the DoD CC SRG overlays, then STIGs, then OWASP/DoD-AI as
the relevant tracks demand. Vendor only what your active tiers/providers need; grow
deliberately (§12.3, §14).

---

## Vendoring log

- **2026-08-11 — NIST SP 800-53 Rev 5 (5.2.0):** vendored all 20 families / 1,196 controls +
  enhancements from the NIST OSCAL catalog (`usnistgov/oscal-content`,
  `NIST_SP-800-53_rev5_catalog.json`, OSCAL 1.2.2, last-modified 2026-05-11) via
  `scripts/vendor/oscal-catalog-to-md.mjs`. Statement + Discussion only; 800-53A assessment
  procedures excluded. `catalog-index.md` regenerated. Spot-checked AC-1, AC-2(1), and the
  withdrawn AC-2(10) against the published control text.
- **2026-08-11 — NIST SP 800-53B baselines:** Moderate (IL4, 287) and High (IL6, 370)
  membership from the OSCAL Moderate/High profiles via `scripts/vendor/oscal-baselines-to-md.mjs`;
  derived `crosswalk/il4-vs-il6-delta.md` (High−Moderate = +83, −0; High ⊇ Moderate as expected).
- **2026-08-11 — OWASP:** Top 10 (2021), ASVS v5.0, Top 10 for LLM Applications v2.0 (2025),
  MASVS v2 — verbatim chapter markdown from the official OWASP repos, pinned to the commit
  SHAs above, via `scripts/vendor/owasp-fetch.mjs`. Spot-checked ASVS §8 (Authorization,
  345 requirement rows total), LLM06 Excessive Agency, Top 10 A01, MASVS-AUTH.
- **2026-08-11 — DISA Application Security & Development STIG (V6R4):** vendored 286 rules
  (STIG-ID, severity, discussion, check, fix) from `U_ASD_STIG_V6R4_Manual-xccdf.xml` via
  `scripts/vendor/xccdf-stig-to-md.mjs`. Direct-downloaded from
  `dl.dod.cyber.mil/.../U_ASD_V6R4_STIG.zip` (the public.cyber.mil catalog is a
  Salesforce/reCAPTCHA portal; direct file links still work). Confirmed V6R4 current
  (V6R5/V7R1 → 404). Spot-checked APSC-DV-000010 against the source. This run also verified
  the XCCDF converter against a real benchmark.
- **2026-08-11 — DISA Application SRG, Mobile App STIG, Cloud Computing SRG:** left
  `SOURCE-NEEDED`. The App SRG and Mobile App STIG use a short code/distribution path not
  located via the direct-download convention; the CC SRG is PDF-only (no XCCDF) — extract
  cited sections. Each file names what to fetch and the ready converter.
- **2026-08-11 — prose standards** (remaining NIST SPs, FIPS, DoD-AI, CNSSP-15): deliberately
  left `SKELETON`. PDF-only, no clean machine-readable source; per scope discipline
  (§12.3 — grow deliberately) vendor these when a citing project's tiers/providers require
  them, capturing only the cited sections (`PARTIAL`) rather than padding (Guarantee #4).
