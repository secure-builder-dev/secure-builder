# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The mechanical check registry. One command runs every check (spec 01 REQ-3.1.1).

Each check is a module exposing `run(root, cfg) -> Outcome`. Registration is
explicit — a check not listed here does not run, and the self-test asserts the
list matches the modules on disk so a check cannot be written and never wired.
"""
import importlib

REGISTRY = [
    "config",
    "no_network",
    "divergence",
    "negative_fixtures",
    "credential_scan",
    "injection_scan",
    "reference_integrity",
    "doc_consistency",
    "attack_surface",
    "license_policy",
    "harness_self_scan",
    "lint",
    "coverage_range",
]


def load(name):
    if name == "config":
        from .. import config
        return config.check
    mod = importlib.import_module(f"engine.checks.{name}")
    return mod.run


def run_all(root, cfg):
    outcomes = []
    for name in REGISTRY:
        fn = load(name)
        outcomes.append(fn(root) if name == "config" else fn(root, cfg))
    return outcomes
