# © 2026 Casey Houle. All rights reserved.
# ENGINE-OWNED: local edits to this file are discarded on update
"""Control manifest verification (spec 01 §7.3). For every declared control:
the implementation exists where declared, a production call site exists
(recomputed, excluding the definition and tests), any required artifact is
present, and a proving test matches. Three states are distinguished: every
entry resolves; at least one fails; the manifest holds only placeholders."""
from .. import manifest
from ..outcome import Outcome

NAME = "control-manifest"


def run(root, cfg):
    try:
        state, results, structural = manifest.verify(root)
    except manifest.ManifestError as e:
        return Outcome.could_not_run(NAME, str(e))
    if state == "invalid":
        return Outcome.found(NAME, "the manifest is structurally invalid", structural, blocking=True)
    if state == "template-only":
        return Outcome.nothing_yet(NAME, "declared controls",
                                   "the manifest holds only its template placeholder — nothing is declared, so nothing is verified")
    if state == "failed":
        items = [f"{r['id']}: {p}" for r in results for p in r["problems"]]
        return Outcome.found(NAME, f"{len([r for r in results if r['problems']])} of {len(results)} declared controls fail verification",
                             items, blocking=True)
    hybrid = sum(1 for r in results if r["status"] == "hybrid")
    return Outcome.clean(NAME, f"{len(results)} declared control(s) implemented, called from production code, tested"
                               + (f" ({hybrid} hybrid, counterpart named)" if hybrid else ""))
