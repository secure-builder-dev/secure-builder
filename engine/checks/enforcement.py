# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Every non-negotiable in the rulebook names an enforcement point outside the
text, and each named point exists (spec 03 REQ-1.2.3)."""
from .. import enforcement

NAME = enforcement.NAME


def run(root, cfg):
    return enforcement.run(root, cfg)
