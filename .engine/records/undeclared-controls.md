# Undeclared controls

Control-shaped code with no manifest entry (spec 01 §7.5). Each row is dispositioned:
`declared` (a manifest entry now exists) or `not-a-control` with a written reason. The probe does not
block; it makes incompleteness visible.

| file | symbol | families | disposition | reason |
|---|---|---|---|---|
| harness/engine/distribute.py | sha | cryptography | not-a-control | content hash for placed-file divergence detection; not a security control (path moved by the four-folder layout; disposition carried from engine/distribute.py) |
| harness/engine/export.py | redaction_problems | redaction | not-a-control | the self-check on EXP-REDACT's output; the control is redact, declared (carried from engine/export.py) |
| harness/engine/scan/bundles.py | sha256 | cryptography | not-a-control | bundle integrity digest; not a security control (carried from engine/scan/bundles.py) |
| harness/engine/topology.py | render_authority | authentication | not-a-control | renders the record-authority table; the word authority is about records, not authentication (carried from engine/topology.py) |
| engine/distribute.py | sha |  | declared or gone | content hash for placed-file divergence detection; not a security control |
| engine/export.py | redaction_problems |  | declared or gone | the self-check on EXP-REDACT's output; the control is redact, declared |
| engine/scan/bundles.py | sha256 |  | declared or gone | bundle integrity digest; not a security control |
| engine/topology.py | render_authority |  | declared or gone | renders the record-authority table (which side owns which record); the word 'authority' is about records, not authentication |
| engine/export.py | redact |  | declared or gone |  |
