# DISA Mobile Application STIG

> **STATUS: SOURCE-NEEDED** — not vendored. The authoritative XCCDF archive is on the DoD
> Cyber Exchange (`public.cyber.mil/stigs/downloads/`), whose download table is JavaScript-
> rendered; the exact versioned `.zip` could not be located non-interactively during
> vendoring. Not filled from memory (Guarantee #4).
>
> **To vendor (operator):**
> 1. Download the current **Mobile Application STIG** zip from the DoD Cyber Exchange (the
>    ASD STIG direct-download convention `dl.dod.cyber.mil/.../stigs/zip/U_<SHORT>_V<v>R<r>_STIG.zip`
>    did not resolve for the Mobile App short code — confirm the exact archive). Unzip, find
>    the `*_Manual-xccdf.xml`.
> 2. Run:
>    ```
>    node scripts/vendor/xccdf-stig-to-md.mjs <path>/..._Manual-xccdf.xml \
>      docs/security/corpus/disa/stigs/mobile-application.md \
>      "DISA Mobile Application STIG" "DISA Mobile Application STIG" 2026-08-11
>    ```
> 3. Spot-check ≥2 rules; flip the row to `VENDORED` in `../../MANIFEST.md`.
>
> Only needed when the Android track is active (`APP_TRACK=android`). Converter:
> `scripts/vendor/xccdf-stig-to-md.mjs` — verbatim-only, and **verified** against a real
> benchmark (ASD STIG V6R4, 286 rules). What is missing here is the *source archive*, not
> a working converter.
> **Provenance/currency:** see `../../MANIFEST.md`.
