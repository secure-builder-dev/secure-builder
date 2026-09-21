# Next session — the harness after the four folders

© 2026 Casey Houle. All rights reserved.

Paste everything below this line into the next chat window.

---

You are continuing the build of the **engine** assurance harness. Read these first, in this
order, and do not restart anything:

1. `~/engine/records/.build-log.md` (append-only session log; the last three entries are the
   bake-off, the build/planted-defect/to-do work, and the four folders)
2. `~/engine/records/STRUCTURE.md` (the layout: rules/, harness/, records/, work/ — in both trees)
3. `~/engine/records/REVIEW-READOUT.md` (what was built, what the gates found, the scorecard)
4. `~/engine/harness/reviewers/MODELS.md` (the bake-off tables, roles, rejections)
5. `C:/dev/notes-api/.engine/records/gate-log.md` and `C:/dev/todo-app/.engine/records/gate-log.md`

## Where things stand (2026-09-21)

- Harness repo `~/engine`, branch `engine`, pushed. `python work/tools/progress.py` says
  **v1.0 REACHED**. 514 hermetic self-tests, 27 registered checks, `python harness/run.py check`
  GREEN. `python -m engine` is gone: the entry point is `harness/run.py` here and
  `.engine/harness/run.py` in a project. Every commit is authored and SSH-signed by Casey Houle
  and nobody else; keep it that way. Governance-set files need `ENGINE_GOVERNANCE_OK=1` on the
  commit; their paths are now `rules/v1.0.md`, `work/tools/progress.py`, `work/hooks/`,
  `rules/specs/`, `rules/prompts/iteration.md`, `rules/GOVERNANCE-SET.md`, `rules/AMENDMENTS.md`.
- Roles: **Devstral builds, Gemma 4 31B gates, Casey Houle is the human in the loop.** There is
  no second gate model and no requirement for one. Ollama 0.34.2; models pinned by tag and
  digest (see MODELS.md); provenance rule: no PRC-origin base weights; only pinned quant tags.
- Demo projects, both on the four-folder layout, both `check` GREEN on main:
  `C:/dev/notes-api` (NOTES-1..3 merged, 14 gate rows, F-1..F-4 in the register) and
  `C:/dev/todo-app` (TODO-1 merged, running at http://127.0.0.1:8765/ with `TODO_TOKENS`
  in the launcher; tokens `tok-casey`, `tok-guest`).
- Every model verdict on those ranges is advisory (each unit changed the manifest). Casey's
  line-by-line review rows are not recorded yet; the command is at the top of REVIEW-READOUT.md.

## Rules that do not bend

Never merge or attest on the human's behalf without saying so in the record; the session drives,
Casey attests. Never reduce the checklist to suit a model (spec 11 REQ-8.3). Records are
append-only: correct by appending a superseding row, never by editing. Write source with the
Write/Edit tools, not bash heredocs (backslashes are stripped). Commit and push after each task;
`check` stays green; receipts are only for spec requirements.

## Open items, in order of value

1. Casey's human-review rows on NOTES-2, NOTES-3 and TODO-1 (turns "never assessed" into
   "assessed" in each coverage inventory).
2. Proposed checklist line (governance change, not made): "B2a. Credential comparison — secrets
   and tokens are compared in constant time; `==` on a secret is a finding." Nobody found the
   planted `==` on NOTES-3.
3. `reviewers/` is unmeasured by the harness's own coverage collector, so two stacked unpushed
   commits touching the drivers turn `check` red (push after each). Either measure it or exempt
   it explicitly with a declared reason.
4. A `gate attest` command that writes the human-review row from the diff the human read.
5. A per-file context budget in the reviewer driver (the to-do page forced a 24k context).
6. Re-run the bake-off (`harness/reviewers/bakeoff.py --rescore` reads saved copies) on every
   checklist revision; the truths lists in MODELS.md are the gate model's regression suite.
