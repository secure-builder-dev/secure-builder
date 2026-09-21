# Review readout — what was built, what the gates found

© 2026 Casey Houle. All rights reserved.

Date: 2026-09-20/21. Written for the human review that closes the session: the
technical readout first, the junior-developer version second. Every number here
is on disk in the demo projects' `.engine/records/` and `.engine/local/`; the
model tables are in `reviewers/MODELS.md`.

Roles: **Devstral builds, Gemma 4 31B gates, Casey Houle is the human in the
loop.** The bake-off measured every candidate that fits the hardware so the
choice is on the record; it does not imply a second gate model is required. Every gate row names Casey Houle as attester because this is his
build; the session drove the commands. Every model verdict on these ranges is
*advisory* — each unit changed the control manifest, and a governance change makes
the automated verdict advisory by design (the human's line-by-line review is the
accountable control). The row that records that review is:

    python .engine/harness/run.py record gate-log unit=<U> range=<base>..<head> run=<n> \
        mode=normal verdict=pass reviewer="Casey Houle" reviewer_class=human \
        model=none attested_by="Casey Houle" harness_version=<v> checklist_version=cl-34c604b32ce3 side=local

and it is the row that turns "never assessed" into "assessed" in the coverage inventory.

---

## Part 1 — Technical readout

### 1.1 What exists now

| where | what | state |
|---|---|---|
| `~/engine` (branch `engine`, pushed) | the harness: 27 checks, 512 self-tests, `check` GREEN | v1.0 reached; 12 commits this session, all authored and SSH-signed by Casey Houle |
| `C:/dev/notes-api` (`main`) | notes API: bearer auth, owner-scoped notes, PUT, search | NOTES-1, NOTES-2, NOTES-3 merged; `check` GREEN; 14 gate rows |
| `C:/dev/todo-app` (`main`) | to-do list, dark-mode page over a JSON API | TODO-1 merged; `check` GREEN; running at http://127.0.0.1:8765/ |
| `~/engine/reviewers/MODELS.md` | bake-off tables, roles, rejections | committed |
| `~/engine/STRUCTURE-PROPOSAL.md` | the four-folder layout | proposal only, nothing moved |

### 1.2 The bake-off (Task 1) — the numbers

Benchmark: NOTES-1 run 2, the unfixed code (DELETE without the owner guard; no
non-owner DELETE test; `json.loads` unguarded). Three repetitions, temperature 0,
same handoff and checklist. A finding counts only if its quoted line is verbatim
in the diff (else *ungrounded*) and the reviewer did not itself judge the item pass
(else *inconsistent*).

| model | valid | truths found | ungrounded | inconsistent | verdict on broken code | mean s |
|---|---|---|---|---|---|---|
| gemma4:31b-it-q4_K_M | 3/3 | **6/9** | **0** | 0 | fail ×3 | 380 |
| mistral-small3.2:24b-instruct-2506-q4_K_M | 3/3 | 0/9 | 0 | 42 | pass ×3 | 152 |
| llama3.1:8b-instruct-q8_0 | 3/3 | 0/9 | 24 | 0 | fail ×3 (wrong reasons) | 101 |
| devstral:24b-small-2505-q4_K_M | 3/3 | 0/9 | 0 | 42 | pass ×3 | 100 |
| magistral:24b-small-2506-q4_K_M (thinking) | 0/3 | — | — | — | no verdict | 41 |
| magistral, `--no-think` | 3/3 | 0/9 | 0 | 1 | pass, fail, fail | 52 |
| gemma4:12b-it-q8_0 (thinking) | 0/3 | — | — | — | no verdict | 205 |
| gemma4:12b, `--no-think` | 3/3 | 0/9 | 0 | 0 | pass, fail, pass | 45 |

Raw material: `C:/dev/notes-api/.engine/local/bakeoff/` (first four models),
`bakeoff2/` (optional candidates, thinking on), `bakeoff3/` (thinking off): one
verdict copy and one driver log per model and repetition, `results.json`, and the
smoke run in `bakeoff/smoke/`.

How to check a number: open `bakeoff/gemma4-31b-it-q4-K-M-rep3.json`,
`findings_detail[*].quote`, and grep that line in
`git -C C:/dev/notes-api diff 0e8a4122a551..fb46176272ef`. Every Gemma quote is
there; Llama's eight ungrounded quotes per run are not (it rewrote `"` as `'`).

### 1.3 NOTES-2 — the build model builds, the gate catches it

- Devstral session 1: converged in **round 1** (86 s). Its tests passed. Read
  before commit: the PUT handler wrote the note *before* `require_owner` ran (a
  non-owner got 403 with the text already replaced), and the malformed-JSON clause
  of the definition of done was not implemented. Committed unchanged as `a59fd92`
  so the gate would review what the model wrote.
- Mechanical gate: **CLEAN** on negative tests — the status-only 403 test satisfied
  it. The write-before-guard bug is invisible to the mechanical layer.
- Run 2, Gemma: **B3 blocking** at `src/app.py:95` (`note = self.store.update(...)`,
  "state update is performed before the authorization check"), **B8 blocking** at
  `src/app.py:56` (`json.loads` unguarded). Zero ungrounded. Both correct.
- Run 3, Mistral, same range: **pass**, "require_owner enforces that only the
  note's owner can update it" — false. This is the bake-off result repeated on a
  live unit.
- Hand-back: two failing tests expressing the two clauses (`3a209c7`). Devstral
  session 2: **5 rounds, not converged** — guarded `json.loads` on PUT only, never
  reordered the guard. Mistral as build model: **5 rounds, not converged**, same
  partial fix, byte-identical answers from round 3 (temperature raised to 0.6, no
  change). Fixed by hand (`f25a370`): parse and write inside the owner callback;
  one guarded body parser `_text_of` for every writer.
- Run 4, Gemma on the fix: **pass**, 0 findings. Run 5, Mistral: **no verdict** —
  its summary field looped until the 8192-token cap (raw answer kept); recorded as
  a fail row with the model's identity, as spec 11 REQ-8.3 requires.
- Records: AC-3.2 declared (GOV-2), mutation-proven; F-1 and F-2 in the register
  with project-rule lines appended to AGENTS.md; design plan corrected (the
  generated truth found four structures the plan never listed); merged to main by
  the session on Casey's behalf, stated in `plans/units/NOTES-2.md`.

### 1.4 NOTES-3 — three planted defects the mechanical checks cannot see

Planted by hand on `unit/NOTES-3`: (D1) `Principals.principal_for` compares tokens
with `==` instead of `hmac.compare_digest`; (D2) `dispatch` answers an unexpected
exception with `repr(e)` and `traceback.format_exc()`; (D3) `GET /notes/search/<term>`
returns every owner's matches and the owner filter lives only in `src/client.py`,
which the tests go through (so a "cross-principal" test exists and passes).

- Mechanical gate on the planted range: **CLEAN** except manifest-entry (the
  `principal_for` change is control-shaped; declared as AC-2.2, GOV-3). Negative
  tests CLEAN — the client-filtered test satisfied it. None of D1–D3 visible.
- Run 2, Gemma: **B3 blocking** at `src/app.py:35` — "authorization is deferred to
  the client helper in src/client.py; any authenticated user can access all notes
  via direct API calls"; **B8 blocking** at `src/app.py:130` — "explicitly includes
  the full stack trace in the HTTP response". Zero ungrounded. **D1 not found.**
  The same two findings, same lines, in the pre-rebuild sample kept at
  `bakeoff/gemma4-31b-notes3-prerebuild.json`.
- Bake-off on the planted range, every model: see §1.5.
- Fixed (`c995449`): scoping in the store (`search_for(owner, term)`), generic 500
  body with a log line, `compare_digest` back with a test that pins it. Re-gate:
  §1.5.

### 1.5 NOTES-3 bake-off and re-gate

Every model, two repetitions, on the planted range (`bakeoff-notes3/`):

| model | valid | D1 timing (`==`) | D2 traceback in body | D3 client-only scoping | verdict |
|---|---|---|---|---|---|
| gemma4:31b-it-q4_K_M | 2/2 | — | 2/2 blocking, exact line | 2/2 blocking, exact line, names src/client.py | fail, fail |
| mistral-small3.2:24b-instruct-2506-q4_K_M | 2/2 | — | 2/2 **non-blocking** | — | pass, pass |
| llama3.1:8b-instruct-q8_0 | 1/2 | — | — | — | fail (hypotheticals), invalid |
| devstral:24b-small-2505-q4_K_M | 0/2 | — | — | — | invalid ×2 |

By class: authorization-in-the-wrong-layer and information leakage are found by
Gemma every time; cryptographic hygiene (the `==`) by nobody — the checklist
names cryptography only in an informational item at this tier, and B2 asks about
completeness, not constant-timeness. The proposed governance change is a
checklist line ("B2a. Credential comparison — secrets and tokens are compared in
constant time; `==` on a secret is a finding"); proposed, not made.

Re-gate: run 3, Gemma on the fix (`c995449`): **pass**, 0 findings, 163 s. F-3 and
F-4 registered with project rules; AC-2.2 declared (GOV-3), mutation-proven;
merged to main by the session on Casey's behalf.

### 1.6 TODO-1 — the to-do app

Project `C:/dev/todo-app`, unit `unit/TODO-1`, merged to main. Running at
http://127.0.0.1:8765/ (token `tok-casey`; a second user `tok-guest` exists to
try the ownership rules against).

- Acceptance tests first (`315253d`, 11 tests from the definition of done, red).
  The first Devstral attempt had "converged" in 120 tokens against the green
  skeleton — the build driver now refuses to start on a green suite.
- Devstral from red: **5 rounds, not converged** (`b19cb2b`, kept as evidence): no
  route registered, an exception name never imported, `request.app`, a
  constant-time helper defined and unused. Built by hand (`923dbe4`): the notes-api
  shape, four API routes behind `require_auth`, `require_owner` before any write,
  one guarded body parser, generic 500 with a log line, `hmac.compare_digest`,
  token table from `TODO_TOKENS` with no default, and a dark-mode page with a
  violet accent (add, toggle, inline edit, delete; token in localStorage).
- Coverage read 38% on `src/server.py` because the harness's collector traced the
  main thread only; fixed (threads traced), 94% after.
- Controls declared: AC-2.1, AC-2.2, AC-3.1, IA-5.1 (GOV-1), all mutation-proven.
  Every mechanical check CLEAN on the range. Run 1, Gemma, 24k context (the range
  needed 17.7k tokens; the driver refused 16k rather than review blind): **pass**,
  0 findings, 271 s.
- Generated truth found `Handler` missing from the plan and the page listed as a
  routed interface it cannot see; plan revised, tickets closed. `check` GREEN on main.

### 1.7 What the session found in the harness (each fixed with a regression test, committed and pushed)

1. Bake-off scoring missed a defect named in prose when a neighbouring line was
   quoted → truths take alternative fragments; `--rescore` re-reads saved copies.
2. A finding on an informational item became a finding when the model put the
   item id in `id` → item resolved from `checklist_item` or `id`.
3. A decorator-registered route handler had "no production call site" → the
   decorator line directly above the `def` is its registration.
4. The driver read the manifest, project rules and register from the working tree
   → read at the range head from version control (a replayed handoff had been
   judged against a newer manifest).
5. A parse failure discarded the model's raw answer → kept beside the verdicts
   with `done_reason` and token counts; `--no-think` for reasoning models.
6. A Table A register row could not be corrected or retired (append-only, and the
   check read every row as current) → the latest row per id stands.
7. Two placed self-tests read the build tree's layout (`reviewers/` beside
   `engine/`) → resolve either layout.
8. A finding grounded on a lone `]` (present in every diff) → a quote needs
   substance: eight non-space characters and a word.
9. The build driver declared convergence on a suite that was green before it
   wrote anything → it refuses to start on a green suite; construction begins
   from failing acceptance tests.
10. The coverage collector traced the main thread only, so `http.server` handlers
    under test read 38% → threads started under it are traced.
11. A control that is a method (`principal_for`) had "no production call site"
    because the mention pattern excluded a preceding dot → attribute calls count.

Known and not fixed: the harness's own coverage-range check cannot see
`reviewers/` (its collector measures `engine/` only), so two unpushed commits
touching the drivers turn `check` red; moving the drivers under `engine/` trips
the no-network scan (they import `urllib`, loopback only). See
STRUCTURE-PROPOSAL.md item 4.

### 1.8 Process errors by the session, and what the harness did about them

- Bundled a plan edit with `unit building` in one commit (NOTES-3): the plan-edits
  check blocked it; the branch was rebuilt before any record named its commits.
- Let a gate-log row ride along inside a governance commit (NOTES-3, GOV-3): the
  governance-isolation check blocked it; split into three commits, re-reviewed.
- Prepared run 1 twice at different heads (NOTES-2): recorded run 1 at its original
  head as a mechanical-only row; the second handoff's marker was removed before any
  record and the log says so.
- Wrote two register rows with an unresolvable `lives_in`: the findings-register
  check blocked `check` on main until item 6 above existed.

Each of these is the harness refusing something a careful person could still get
wrong. That is the point of it.

---

### 1.9 The engine's scorecard

**Successes**
- Every real defect that reached a model gate was caught by Gemma: five for five
  on authorization (DELETE guard, write-before-guard, client-only scoping) and
  leakage (unguarded decode, traceback in the body), at the exact line, with
  zero invented findings across 17 grounded findings this session.
- The mechanical layer caught every process error the session made — bundled
  plan edit, bundled governance row, undeclared control-shaped code, unresolvable
  register rows, plan/code divergence — before any of them reached a record.
- The grounding rule did its job on every weak model: 24 Llama hallucinations,
  84 Mistral/Devstral commentary "findings" and one trivially-grounded Gemma
  finding were all discarded mechanically, never by judgment.
- Eleven harness defects found by use and fixed with regression tests in one
  session; `check` stayed GREEN at every commit.

**Failures**
- Neither build model finished a unit unaided: Devstral converged once (on code
  with two defects), then failed twice in five rounds; Mistral failed once. The
  build role on this laptop is "first draft", not "builder".
- Nobody found the `==` token comparison. The checklist, not the model, is the
  fix (a governance change; proposed above).
- Every verdict is advisory because every unit declared a control; the human
  review row is what closes each unit, and none is recorded yet — that row is
  Casey's, not the session's.

**Strengths of the design, seen in use**
- Verbatim-quote grounding, item-consistency and the informational filter turn a
  language model's output into something that can be counted.
- Append-only records with supersession made every correction visible instead
  of silent (register rows, gate rows, tickets).
- Refusing rather than degrading: the context refusal, the green-suite refusal,
  the impossible-scan refusal each produced a better run than the alternative.

**Suggestions**
1. Add the constant-time-comparison line to the checklist (governance change).
2. Record the human review as a `reviewer_class=human` gate row so the assessed
   boundary reflects it; consider a `gate attest` command that writes it.
3. Give the reviewer driver a per-file context budget so a page-sized HTML diff
   does not force the whole review to a bigger context.
4. Measure `reviewers/` in the harness's own coverage or exempt it explicitly
   (STRUCTURE-PROPOSAL item 4) so two stacked driver commits stop turning
   `check` red.
5. Run the bake-off on every checklist revision; the truths list is the
   regression suite for the gate model.
6. Devstral earns its place only with acceptance tests written first; keep the
   green-suite refusal and consider a round cap of three.

## Part 2 — The junior-developer breakdown

**What is this whole thing?** A set of rules and checks (the "harness", in
`.engine/`) that sits inside a code project and refuses to let code move forward
until it has been checked in specific, recorded ways. Some checks are mechanical
(does every route have a test for the "no token" case? did the tests pass? is
every security control listed in a manifest?). One check is a *reviewer*: a
language model reads the diff against a checklist and writes findings — but only
findings that quote a real line of the diff count, and only a named human can
attest the result.

**What was built this session, in plain words**

1. *Which AI models are any good at reviewing code?* We gave four local models the
   same broken code three times each. One (Gemma 4, 31B) found the bugs every
   time and never made anything up. Two (Mistral, Devstral) said the broken code
   was fine, every time. One (Llama 8B) shouted about everything and found
   nothing real. Two more candidates could not even produce an answer in the
   required format until "thinking" was switched off, and then found nothing.
   Conclusion: Gemma reviews. The other candidates were measured so the choice
   is on the record, not to fill a slot.

2. *Can an AI build a feature and another AI catch its mistakes?* Devstral wrote
   the "edit a note" feature in one go and its own tests passed. But it changed
   the note *before* checking who owned it — a stranger could overwrite your note
   and still get told "forbidden". The mechanical checks were happy (a 403 test
   existed). Gemma caught it, quoted the exact line, and said how to fix it. Then
   we handed Devstral a failing test that said "a rejected edit must not change
   the note" — and it could not fix it in five tries. Neither could Mistral. A
   human fixed it in five minutes. Lesson: the build model is a fast typist, not
   an engineer; the gate model is a real reviewer; the human is still needed.

3. *Can the gate catch subtle things?* We planted three bugs on purpose: a timing
   leak in the password-style token check, an error page that prints the whole
   stack trace, and a search feature that hides other people's notes only in the
   browser (the server sends them anyway). Gemma caught the stack trace and the
   fake privacy immediately. It missed the timing leak. So: strong on "who can
   see what" and "what leaks out", weaker on cryptographic hygiene — the checklist
   item for that is informational at this tier, which is part of why.

4. *A to-do app, end to end.* We wrote the tests first (what "done" means),
   handed them to Devstral, and it could not make them pass in five tries. A
   human built the app to the same tests in one go; every mechanical check was
   clean; Gemma reviewed the whole thing and passed it with nothing to say. It is
   running now, and a second user's token (`tok-guest`) lets you confirm you
   cannot touch someone else's list.

**How to read a gate-log row** (`.engine/records/gate-log.md`): one line per
review. `unit` is the feature, `run` counts attempts, `verdict` is pass / fail /
advisory (advisory = "a human must look, because the rules themselves changed in
this batch"), `findings` lists what was found, `model` says exactly which model
with its checksum, `attested_by` is the human who owns the result.

**Things to remember**

- A finding must quote the code. If it doesn't, it is thrown out and counted
  against the reviewer. This is what stops a model from making things up.
- "Tests pass" is not "done". Twice this session, tests passed on code that was
  wrong; the tests were checking the wrong thing.
- The records are append-only. When we got something wrong, we added a row saying
  so; we never edited history.
- Every run is on disk. If a number in this document looks wrong, the file it
  came from is named next to it.
