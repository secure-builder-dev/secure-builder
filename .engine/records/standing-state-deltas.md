# Standing-state deltas

© 2026 Casey Houle. All rights reserved.

The continuous monitoring record: each measured delta between gate snapshots
and its disposition (a findings-register row explaining why it is expected, or a ticket).

Schema: standing-state-deltas/1.

| date | commit | measurement | previous | current | disposition | side |
|---|---|---|---|---|---|---|
| 2026-10-10T03:00:05+00:00 | db5142020d8c | control_manifest_result | template-only | resolved | ticket DELTA-control_manifest_result-db5142020d8c | local |
| 2026-10-12T13:31:57+00:00 | 27637443e3b6 | control_manifest_result | resolved | failed | undispositioned: BLOCKING control decay | local |
| 2026-10-12T13:31:57+00:00 | 27637443e3b6 | exported_symbols_without_call_site | 0 | 2 | ticket DELTA-exported_symbols_without_call_site-27637443e3b6 | local |
| 2026-10-12T14:30:59+00:00 | c7d62a18d5a4 | exported_symbols_without_call_site | 2 | 4 | ticket DELTA-exported_symbols_without_call_site-c7d62a18d5a4 | local |
