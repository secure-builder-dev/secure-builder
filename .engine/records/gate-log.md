# Gate log

© 2026 Casey Houle. All rights reserved.

One row per gate run, including every re-run. Append only. A field-mode row
carries mode=field and a field-pass/field-fail verdict; a wrong verdict is superseded by a
later row naming it in `supersedes`, never erased.

Schema: gate-log/1.

| date | unit | range | run | mode | verdict | findings | tickets | reviewer | reviewer_class | model | attested_by | harness_version | checklist_version | side | controls | supersedes | deferred | obligation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-19T03:53:36+00:00 | TO-1 | 9563866543d7..45743b95d0bf | 2 | normal | advisory | 0 | - | security-gate | automated | gemma4:31b-it-q4_K_M (gemma4; 31.3B; Q4_K_M; ollama digest 6316f0629137) | Casey Houle (submitted by the build session on Casey Houle's behalf; not a line-by-line human review) | 0.1.0-dev+0ab5d0855a75 | cl-34c604b32ce3 | local | - | - | - | - |
| 2026-10-19T09:47:31+00:00 | TO-2 | 9563866543d7..3df85b88f5e2 | 1 | normal | advisory | 0 | - | security-gate | automated | gemma4:31b-it-q4_K_M (gemma4; 31.3B; Q4_K_M; ollama digest 6316f0629137) | Casey Houle (submitted by the build session on Casey Houle's behalf; not a line-by-line human review) | 0.1.0-dev+0ab5d0855a75 | cl-34c604b32ce3 | local | - | - | - | - |
