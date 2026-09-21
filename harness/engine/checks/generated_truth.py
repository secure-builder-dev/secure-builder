# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Generated truth vs the plan (spec 02 §9; spec 03 REQ-3.5.3)."""
from .. import truth

NAME = "generated-truth"


def run(root, cfg):
    return truth.check(root, cfg)
