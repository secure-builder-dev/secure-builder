# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""The honest-degradation statement (spec 04 §7).

On demand, states which guarantees are reduced in the current mode, in three
categories: unaffected; reduced, quantified; not achieved. Generated from the
component registry and the record set, never hand-maintained. Included in
every evidence export.

Each subsystem registers what it guarantees and under what conditions, at the
moment it is written, so the statement never has to be reconstructed later.
"""
import datetime
import pathlib

from . import config as cfgmod

# (component, condition -> (category, text)). Conditions are evaluated against
# the loaded configuration and the record state. Components register here as
# they are built; a component missing from this table is a build defect that
# the self-test for this module catches.
UNAFFECTED = "unaffected"
REDUCED = "reduced, quantified"
NOT_ACHIEVED = "not achieved"


def _catalogue_age(root):
    p = pathlib.Path(root) / ".engine" / "currency-verified"
    if not p.is_file():
        return None
    try:
        d = datetime.date.fromisoformat(p.read_text(encoding="utf-8").strip()[:10])
    except ValueError:
        return None
    return (datetime.date.today() - d).days


def _detection_age(root):
    p = pathlib.Path(root) / ".engine" / "detection-data-date"
    if not p.is_file():
        return None
    try:
        d = datetime.date.fromisoformat(p.read_text(encoding="utf-8").strip()[:10])
    except ValueError:
        return None
    return (datetime.date.today() - d).days


def entries(cfg, root):
    """Return a list of (category, component, statement)."""
    mode = cfg.mode
    out = [
        (UNAFFECTED, "mechanical checks", "computed from the tree and vendored data only; identical in every mode"),
        (UNAFFECTED, "control wiring verification", "computed from the tree; identical in every mode"),
        (UNAFFECTED, "mutation testing", "runs the project's own suite; identical in every mode"),
        (UNAFFECTED, "citation resolution", "resolved against vendored catalogues; identical in every mode"),
        (UNAFFECTED, "record-keeping", "plain text under version control; identical in every mode"),
    ]
    age = _catalogue_age(root)
    if mode == "connected":
        out.append((UNAFFECTED, "catalogue currency", "currency checker may fetch published sources on demand"))
    else:
        out.append((REDUCED, "catalogue currency",
                    "currency not checked in this mode; last verified "
                    + (f"{age} day(s) ago" if age is not None else "never (no verification recorded)")))
    dage = _detection_age(root)
    if mode == "disconnected":
        out.append((REDUCED, "scanner detection data",
                    "refreshed only by transferred bundle; data is "
                    + (f"{dage} day(s) old" if dage is not None else "of unknown age (no bundle ingested)")))
    else:
        out.append((UNAFFECTED, "scanner detection data", "refreshed by the tools' own update mechanism"))
    if mode == "connected":
        out.append((UNAFFECTED, "protected-branch merge control", "enforced by hosting platform branch protection"))
        out.append((UNAFFECTED, "change requires review", "enforced by platform pull request"))
    else:
        out.append((NOT_ACHIEVED, "protected-branch merge control",
                    "no hosting platform; a client-side hook reduces accidents and is not a control"))
        out.append((NOT_ACHIEVED, "change requires review",
                    "no platform pull request; requires a server-side hook or documented procedure"))
    if cfg.operators < 2:
        out.append((NOT_ACHIEVED, "separation of duties",
                    "single-operator environment: one person cannot independently review their own work"))
    else:
        out.append((UNAFFECTED, "separation of duties", f"{cfg.operators} operators declared"))
    if cfg.topology != "single":
        out.append((REDUCED, "record authority",
                    f"two-instance topology; this is the {cfg.topology}; records carry side='{cfg.side}'"))
    return out


def statement(root):
    """The statement as text. Raises ConfigError if the project is not initialized."""
    cfg = cfgmod.load(root)
    rows = entries(cfg, root)
    lines = [f"# Degradation statement", f"{cfg.mode_line()}",
             f"generated: {datetime.datetime.now().astimezone().isoformat(timespec='seconds')}",
             f"shape: {cfg.shape}", ""]
    for cat in (UNAFFECTED, REDUCED, NOT_ACHIEVED):
        lines.append(f"## {cat}")
        items = [r for r in rows if r[0] == cat]
        if not items:
            lines.append("(none)")
        for _, comp, text in items:
            lines.append(f"- {comp}: {text}")
        lines.append("")
    return "\n".join(lines)
