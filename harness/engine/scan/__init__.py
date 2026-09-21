# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The scan subsystem (spec 01 §4; spec 02 §6; spec 04 §4).

Five concerns, each by a separate tool, run as pinned container images (or
host binaries where explicitly selected); two independent vulnerability
scanners whose findings are correlated; detection data whose age is
determined before a clean verdict is allowed; images rebuilt from the current
tree and bound to the reviewed commit by digest; two separate verdicts; a
composition inventory per image; findings routed to an actionable document
(whose existence is the gate's blocking condition) and a carried-findings
record shaped as a plan of action.
"""
