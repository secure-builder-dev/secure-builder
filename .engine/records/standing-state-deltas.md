# Standing-state deltas

© 2026 Casey Houle. All rights reserved.

The continuous monitoring record: each measured delta between gate snapshots
and its disposition (a findings-register row explaining why it is expected, or a ticket).

Schema: standing-state-deltas/1.

| date | commit | measurement | previous | current | disposition | side |
|---|---|---|---|---|---|---|
| 2026-10-10T03:00:05+00:00 | db5142020d8c | control_manifest_result | template-only | resolved | ticket DELTA-control_manifest_result-db5142020d8c | local |
| 2026-10-20T16:03:16+00:00 | 4a3cc69b9811 | exported_symbols_without_call_site | 5 | 4 | ticket DELTA-exported_symbols_without_call_site-4a3cc69b9811 | local |
| 2026-10-20T18:31:52+00:00 | d817083f1e27 | exported_symbols_without_call_site | 4 | 10 | ticket DELTA-exported_symbols_without_call_site-d817083f1e27 | local |
| 2026-10-20T20:01:59+00:00 | b230197bcfeb | exported_symbols_without_call_site | 10 | 12 | ticket DELTA-exported_symbols_without_call_site-b230197bcfeb | local |
