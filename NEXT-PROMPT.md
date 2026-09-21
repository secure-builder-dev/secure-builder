# Next session — continue testing the harness with local models

© 2026 Casey Houle. All rights reserved.

Paste everything below this line into the next chat window.

---

You are continuing the build of the **engine** assurance harness. Read these first, in this order,
and do not restart anything:

1. `~/engine/.build-log.md` (append-only session log; the last four entries are today's work)
2. `~/engine/LIFECYCLE-EXERCISE.md`
3. `~/engine/reviewers/local_model.py`, `build_model.py`, `bakeoff.py` (docstrings)
4. `C:/dev/notes-api/.engine/records/gate-log.md` (the demo project's gate log)

## Where things stand (2026-09-20)

- Harness repo `~/engine`, branch `engine`, pushed to `secure-builder.git`. `python tools/progress.py`
  says **v1.0 REACHED** (474 requirements done, 6 deferred to v1.1, 9 n/a). 501 hermetic
  self-tests, 27 registered checks, `python -m engine check` GREEN. Every commit is authored and
  SSH-signed by Casey Houle and nobody else; keep it that way (no co-author trailers, no assistant
  names anywhere in the tree — the pre-commit hook enforces it).
- Ollama 0.34.2 is installed (`$LOCALAPPDATA/Programs/Ollama/ollama.exe`; start with `ollama serve`
  if `curl localhost:11434/api/version` fails). Four models are pulled, pinned by tag and digest:
  - `gemma4:31b-it-q4_K_M` (Google, 19 GB) — gate model
  - `mistral-small3.2:24b-instruct-2506-q4_K_M` (Mistral, 15 GB) — gate model, allied nation
  - `llama3.1:8b-instruct-q8_0` (Meta, 8.5 GB) — gate candidate
  - `devstral:24b-small-2505-q4_K_M` (Mistral, 14 GB) — build model
  Provenance rule (Track C deck): no PRC-origin base weights. Llama 3.3 70B was rejected because
  it does not fit 24 GB VRAM. One model resident at a time; they hot-swap.
- Demo project `C:/dev/notes-api` (a stdlib notes API: bearer auth, owner-scoped notes). Unit
  NOTES-1 is merged. Its gate log: run 1 Llama 8B could not complete the checklist (recorded fail,
  REVIEW-INCOMPLETE); run 2 Gemma 4 found the DELETE-without-owner hole and the missing test (two
  grounded blocking findings); runs 3–4 Mistral and Gemma pass the fix. Branch `unit/NOTES-2` is
  planned (item N-2: PUT /notes/<id> owner-only + malformed JSON → 400) and NOT yet built: Devstral's
  first attempt produced an unfixable syntax error five times, the driver now rejects files that do
  not parse, and its retry hung >25 min in one generation, so both drivers now cap `num_predict`
  at 8192. `src/` and `tests/` on that branch are clean (restored from git).
- The reviewer driver runs as a fresh process with only the handoff path; loopback endpoint only;
  findings must quote the diff verbatim (else discarded as ungrounded); informational items and
  items the reviewer itself judged pass cannot be findings; one repair pass for completeness
  answers; refuses to run when the prompt would not fit the context; diff excludes `.engine/`
  except the governed files. Prompt is ~10 k tokens: ~220 words of instructions, the rest is the
  code under review, the per-run checklist and the reviewer definition (whole, per spec 03 REQ-1.3).

## Task 1 — bake off the gate models (which ones are up to the task)

The benchmark range is NOTES-1 run 2 (the unfixed code with two known defects). Its handoff and
prepared state already exist. Run every gate candidate three times against it:

```
cd C:/dev/notes-api
set PYTHONIOENCODING=utf-8
python .engine/reviewers/bakeoff.py --handoff .engine/local/handoff-NOTES-1-2.md --repeat 3 ^
  --model gemma4:31b-it-q4_K_M --model mistral-small3.2:24b-instruct-2506-q4_K_M ^
  --model llama3.1:8b-instruct-q8_0 --model devstral:24b-small-2505-q4_K_M ^
  --truth "src/app.py|self.store.delete|delete route lacks the owner guard" ^
  --truth "src/app.py|json.loads|malformed JSON body is an unhandled exception"
```

(bash: replace `^` with `\`.) Expect ~2–4 min per Gemma run, ~1–2 min for the others; ~40 min
total. It prints a table and writes `.engine/local/bakeoff/results.json` plus one log and verdict
per run. Score on: valid verdict (the harness accepts it), truths found, ungrounded findings
(hallucinations), inconsistent findings, time. A model that cannot produce a valid verdict, or that
finds neither planted defect, is not a gate model whatever its fluency. A smoke run with Llama
already exists: valid, 0/2 truths found, 8 ungrounded — that is the 8B floor.

Optional candidates if the first table is close: `gemma4:26b-a4b-it-q4_K_M` (MoE, faster),
`magistral:24b-small-2506-q4_K_M` (Mistral reasoning), `gemma4:12b-it-q8_0`. Pull with
`ollama pull <tag>`; only pinned quant tags, never `:latest`.

Record the outcome: append a paragraph to `~/engine/.build-log.md`, and add the table to
`~/engine/reviewers/MODELS.md` (create it) with the rejected alternatives and why. Commit as Casey.

## Task 2 — let the build model build NOTES-2, then gate it with the two best reviewers

```
cd C:/dev/notes-api && git checkout unit/NOTES-2
python .engine/reviewers/build_model.py --model devstral:24b-small-2505-q4_K_M --item N-2 --rounds 5
```

If it converges (tests pass): read the diff, commit as Casey, then `coverage project`, declare any
new control-shaped code in `.engine/control-manifest.json` in its own commit with a governance
row (`record changelog ...`), `mutate`, `handoff --scan-impossible "..."`, `gate prepare`, then
`review` with `ENGINE_REVIEWER_CMD="python .engine/reviewers/local_model.py --model <best>"`,
`gate submit ... attested_by="Casey Houle"`, and again with the second-best model on the next run.
If Devstral does not converge in 5 rounds, try `mistral-small3.2` as the build model, and record
which build model converged, in how many rounds. Every attempt is data: log it.

## Task 3 — stress the gate with harder planted defects

Create unit NOTES-3 on a branch and plant, by hand, three subtler defects the mechanical checks
cannot see, e.g.: a timing-unsafe token comparison (`==` instead of `hmac.compare_digest`), an
error response that echoes the internal exception text, a list route that filters by owner in the
client-side helper but not in the store. Gate with each model; extend the bake-off `--truth`
lines; report which models find which class of defect. Then fix, re-gate, close the unit.

## Rules that do not bend

- Never merge or attest on the human's behalf without saying so in the record; every gate row
  names Casey Houle as attester because this is his build — say in the log that the session drove it.
- Never reduce the checklist to suit a model (spec 11 REQ-8.3). A model that cannot complete it
  gets a fail row with its identity, as run 1 did.
- Use the Write/Edit tools for source with backslashes; bash heredocs strip them (see memory).
- Commit and push after each task; check stays green; receipts are only for spec requirements.
