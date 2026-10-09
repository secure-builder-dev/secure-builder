# Gate log

© 2026 Casey Houle. All rights reserved.

One row per gate run, including every re-run. Append only. A field-mode row
carries mode=field and a field-pass/field-fail verdict; a wrong verdict is superseded by a
later row naming it in `supersedes`, never erased.

Schema: gate-log/1.

| date | unit | range | run | mode | verdict | findings | tickets | reviewer | reviewer_class | model | attested_by | harness_version | checklist_version | side | controls | supersedes | deferred | obligation |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
