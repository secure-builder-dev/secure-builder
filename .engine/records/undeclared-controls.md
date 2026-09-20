# Undeclared controls

Control-shaped code with no manifest entry (spec 01 §7.5). Each row is dispositioned:
`declared` (a manifest entry now exists) or `not-a-control` with a written reason. The probe does not
block; it makes incompleteness visible.

| file | symbol | families | disposition | reason |
|---|---|---|---|---|
| engine/distribute.py | sha | cryptography | not-a-control | content hash for placed-file divergence detection; not a security control |
| engine/scan/bundles.py | sha256 | cryptography | not-a-control | bundle integrity digest; not a security control |
