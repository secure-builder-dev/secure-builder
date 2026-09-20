# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Reconciliation obligations (spec 11 §7). The count of open obligations is
reported at every gate and in every export (REQ-7.2, 7.5); an obligation older
than the configured threshold is a finding (REQ-7.7). Obligations are discharged
only by a full re-gate that confirms every deferred item — never by this check,
never by clearing the declaration."""
import pathlib

from .. import field
from ..outcome import Outcome

NAME = "reconciliation"


def run(root, cfg):
    if not (pathlib.Path(root) / field.OBLIGATIONS).is_file():
        return Outcome.nothing_yet(NAME, "reconciliation-obligations record", "the record is seeded by init; no field debt can be counted without it")
    try:
        lines, n_open, aged = field.report(root, cfg)
    except (field.FieldError, OSError, ValueError) as e:  # a malformed record is a record that cannot be read, not a clean one
        return Outcome.could_not_run(NAME, f"reconciliation-obligations record unreadable ({type(e).__name__}: {e})")
    decl = field.declaration(root)
    detail = lines[0] + (f"; field mode DECLARED by {decl['declared_by']} ({decl['reason']})" if decl else "")
    if aged:
        return Outcome.found(NAME, detail, lines[1:], blocking=False)
    return Outcome.clean(NAME, detail)
