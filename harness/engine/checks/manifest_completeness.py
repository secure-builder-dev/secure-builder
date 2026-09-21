# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Manifest completeness probe as a mechanical check (spec 01 §7.5). Never
blocks: it converts an unbounded unknown into a finite, dispositioned list."""
from .. import probes

NAME = "manifest-completeness"


def run(root, cfg):
    return probes.completeness_probe(root, cfg)
