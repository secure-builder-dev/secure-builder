# DISA Application SRG

> **STATUS: SOURCE-NEEDED** — not vendored. The Application Security Requirements Guide
> (SRG) XCCDF is on the DoD Cyber Exchange (`public.cyber.mil/stigs/downloads/`), whose
> download table is JavaScript-rendered; the exact versioned `.zip` could not be located
> non-interactively during vendoring. Not filled from memory (Guarantee #4).
>
> **To vendor (operator):** download the current **Application Security Requirements Guide**
> zip (SRGs are not under the `.../stigs/zip/` path that served the ASD STIG — find the exact
> archive from the DoD Cyber Exchange), unzip, then run the XCCDF converter (same invocation
> shape as `../stigs/application-security-dev.md`), targeting this file with title/prov-id
> "DISA Application SRG". Spot-check ≥2 rules; flip the row to `VENDORED` in `../../MANIFEST.md`.
>
> Note: the SRG is the requirements *guide* the App Sec & Dev STIG implements; for most
> citation needs the STIG (`../stigs/application-security-dev.md`) is the operative source.
> Converter: `scripts/vendor/xccdf-stig-to-md.mjs`. **Provenance/currency:** `../../MANIFEST.md`.
