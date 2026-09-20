# Engine rules

© 2026 Casey Houle. All rights reserved.
ENGINE-OWNED: local edits to this file are discarded on update

This file is pulled into every agent session by the project's instruction file.
It states only the non-negotiables, the map of where things live, and the
lifecycle. Everything else is a pointer (spec 03 §5). This file uses no
references of its own: the runtime resolves one level, and a rule two levels
down is silently absent.

## Non-negotiables

1. You never merge to the protected branch, approve your own work, or override a
   gate verdict. Branch protection enforces this; the rule stops the attempt earlier.
2. You never attribute yourself in anything that lands in the repository —
   commit messages, comments, generated documents. The human is accountable.
3. You never read or reproduce environment secrets: deployment value files,
   infrastructure variable files, platform vulnerability artifacts.
4. Review runs in a fresh session from a generated handoff. You never carry the
   construction conversation into a review, and you never write a note for the
   reviewer: the handoff has no free-text field by design.
5. Governance files — this rulebook, the reviewer definitions, anything that
   alters gate behavior — are human-authored. You may only transcribe a decision
   approved elsewhere, citing its source, in a zone the allowlist names.
6. A check that cannot fail is not a check. Every check you add ships with a
   negative fixture and is shown failing before it is accepted.
7. A finding is dispositioned: mechanical becomes a check, judgment becomes a
   checklist line. "Fixed" alone is not a disposition.

## Precedence

Where these rules and the project's own rules in the instruction file conflict,
these rules win. **This statement carries no enforcement.** Both files reach a
session with equal weight; the rules that hold are the ones also enforced
outside the text — by branch protection, the pre-execution hook, and the
mechanical checks. No control whose failure matters rests on this paragraph.

## Where things live

- `.engine/config.json` — the project's shape (track, tier, provider, app type), mode, topology.
- `.engine/control-manifest.json` — the declared security controls. Project-owned.
- `.engine/records/` — gate log, findings register, governance changelog. Append-only, plain text.
- `.engine/scan/` — scan artifacts; the verdict stamp is committed, raw output is not.
- `.engine/agents/` — reviewer definitions. Whole, self-contained, engine-owned.
- `python .engine/harness/run.py check` — the single command. CI runs the same one.

## Lifecycle

PLAN → BUILD → SCAN → HANDOFF → REVIEW → MERGE → CLOSE. The scan completes green
before the handoff; the handoff refuses an unscanned tree; two gates run on the
range in an isolated session; a human merges; closure follows human approval.
Unit-of-work states: planned, building, in review, merged. Item states: open,
claimed, in review, done. State lives in the item and unit files, nowhere else.
