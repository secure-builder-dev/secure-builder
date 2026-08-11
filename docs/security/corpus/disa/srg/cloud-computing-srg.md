# DISA DoD Cloud Computing SRG — IL Overlays

> **STATUS: SOURCE-NEEDED** — not vendored. Unlike the STIGs, the **DoD Cloud Computing SRG
> is published as a PDF**, not XCCDF/OSCAL — there is no clean machine-readable source to
> convert, and its IL2/IL4/IL5/IL6 overlay text must be extracted from the official PDF
> verbatim. Extracting controlling prose from a PDF without a reviewer confirming each
> excerpt risks paraphrase/error, so it is deferred rather than filled from memory
> (Guarantee #4; PRD §13 — a plausible-but-wrong control is worse than an empty one).
>
> **To vendor (operator):**
> 1. Download the current **DoD Cloud Computing SRG** PDF from
>    `public.cyber.mil/dccs/` (or the Cyber Exchange SRG library).
> 2. Extract, **verbatim**, the sections actually cited: the impact-level definitions
>    (IL2/4/5/6) and the IL4→IL6 overlay deltas (jurisdiction/off-premises, connectivity,
>    personnel, CSP/mission-owner responsibility split). Add a full citation (doc ID, version
>    e.g. v1r4, page/section) in the header.
> 3. Mark `PARTIAL` if only the cited sections are captured; `VENDORED` only if complete.
> 4. Then re-derive the SRG overlay portion of `../../crosswalk/il4-vs-il6-delta.md`
>    (currently the 800-53B control delta only).
>
> **Provenance/currency:** see `../../MANIFEST.md`.
