# Vendored data

© 2026 Casey Houle. All rights reserved.
ENGINE-OWNED: local edits to this file are discarded on update

Every data set the harness carries, its source, and the terms under which it is
redistributed — or that the operator must supply it (spec 06 REQ-8.5; spec 04
REQ-3.9). Provenance for each vendored copy is written beside it at placement.

| Data set | Source | Redistribution | Coverage |
|---|---|---|---|
| `nist-sp-800-53-r5.json` | NIST SP 800-53 Revision 5 (a work of the United States Government; public domain in the United States) | Redistributable. This seed is a transcription by the author of the identifiers, statuses, titles and successors the harness itself cites; it is not the full catalogue | Partial. Ingest the official OSCAL catalogue for full coverage: `engine catalogue ingest NIST_SP-800-53_rev5_catalog.json` |
| `publications.json` | NIST and FIPS publication index, transcribed by the author | Redistributable (titles and revision numbers) | The publications the harness's checklist cites |
| `owasp-top10.json` | OWASP Top 10:2021 category identifiers and titles | Redistributable under CC BY-SA 4.0; attribution: OWASP Foundation | The current edition's ordered list |
| OWASP MASVS | Not vendored | Cited by the mobile-track block; supply a catalogue with `engine catalogue ingest` to have those identifiers resolve. Until then they are reported as *platform not in the index*, not failed | — |
| Scanner detection data | Produced by the scanner tools at run time, or delivered as a dated bundle | Not redistributed by the harness | See `engine scan bundle-data` |
| Model weights (field mode) | Not vendored | Operator-supplied, version-pinned, transferred with provenance like any other data set | — |

Catalogues carry no control text. They answer one question — does this identifier
resolve to a real, current control — deterministically.
