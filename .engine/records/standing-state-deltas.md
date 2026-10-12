# Standing-state deltas

© 2026 Casey Houle. All rights reserved.

The continuous monitoring record: each measured delta between gate snapshots
and its disposition (a findings-register row explaining why it is expected, or a ticket).

Schema: standing-state-deltas/1.

| date | commit | measurement | previous | current | disposition | side |
|---|---|---|---|---|---|---|
| 2026-10-10T03:00:05+00:00 | db5142020d8c | control_manifest_result | template-only | resolved | ticket DELTA-control_manifest_result-db5142020d8c | local |
