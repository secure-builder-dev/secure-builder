# Standing-state deltas

© 2026 Casey Houle. All rights reserved.

The continuous monitoring record: each measured delta between gate snapshots
and its disposition (a findings-register row explaining why it is expected, or a ticket).

Schema: standing-state-deltas/1.

| date | commit | measurement | previous | current | disposition | side |
|---|---|---|---|---|---|---|
| 2026-10-10T03:00:05+00:00 | db5142020d8c | control_manifest_result | template-only | resolved | ticket DELTA-control_manifest_result-db5142020d8c | local |
| 2026-10-18T07:55:26+00:00 | 46c8999f384e | exported_symbols_without_call_site | 4 | 3 | ticket DELTA-exported_symbols_without_call_site-46c8999f384e | local |
| 2026-10-19T15:28:12+00:00 | a511c67a5bfa | exported_symbols_without_call_site | 3 | 5 | ticket DELTA-exported_symbols_without_call_site-a511c67a5bfa | local |
