# Local models: the bake-off and the roles

© 2026 Casey Houle. All rights reserved.
<!-- ENGINE-OWNED: local edits to this file are discarded on update -->

Which open-weight models are up to which job on the 24 GB laptop, decided by
measurement, not by reputation. Everything here was produced by
`reviewers/bakeoff.py` driving `reviewers/local_model.py` against a range with
known defects, and by `reviewers/build_model.py` on a claimed work item. The raw
material is on disk in the demo project (C:/dev/notes-api/.engine/local/bakeoff/:
one verdict copy and one driver log per model and repetition, `results.json`,
`bakeoff-stdout.txt`) and in that project's gate log.

Constraints that shaped the candidate list: 24 GB VRAM, one model resident at a
time; the provenance rule from the Track C deck (no PRC-origin base weights); only
pinned quantization tags, never `:latest`; Ollama 0.34.2 on the loopback interface.

## The benchmark

Range NOTES-1 run 2 of the notes-api demo (`0e8a4122a551..fb46176272ef`): the
unfixed unit with defects known to be in it. The same prepared handoff, checklist
(cl-34c604b32ce3), and control manifest for every run; temperature 0; 16 384
tokens of context; the prompt is ~9 600 tokens (17 000 chars). Three repetitions
per model. Nothing was submitted to the gate log.

Planted truths (`--truth file|fragment[;fragment]|label`; a truth counts as found
when a grounded finding names the file and its quoted line or its description
contains one of the fragments):

1. `src/app.py` — DELETE /notes/<id> lacks the owner guard (`self.store.delete;delete_note;DELETE /notes`)
2. `src/app.py` — malformed JSON body is an unhandled exception (`json.loads;malformed;invalid JSON;JSONDecodeError`)
3. `tests/test_notes.py` — no non-owner DELETE test (`delete`)

A finding is *grounded* only if its quoted line exists verbatim in the diff at the
range; otherwise it is discarded as ungrounded and counted. A finding on a checklist
item the same reviewer judged pass or not-applicable is *inconsistent* and also
discarded. Every model needed the one allowed repair pass for the completeness
answers (Q3/Q4 must be lists) and every model produced an acceptable set after it,
so every verdict below is *valid* in the harness's sense — validity is the floor,
not the score.

## Results (2026-09-20)

| model | vendor | valid | truths found | ungrounded | inconsistent | verdict on broken code | mean s | tok/s |
|---|---|---|---|---|---|---|---|---|
| gemma4:31b-it-q4_K_M (digest 6316f0629137) | Google | 3/3 | **6/9** (3, 1, 2 per rep) | **0** | 0 | fail, fail, fail | 380 | 20–23 |
| mistral-small3.2:24b-instruct-2506-q4_K_M (5a408ab55df5) | Mistral | 3/3 | 0/9 | 0 | 42 | pass, pass, pass | 152 | 31–34 |
| llama3.1:8b-instruct-q8_0 (b158ded76fa0) | Meta | 3/3 | 0/9 | 24 | 0 | fail, fail, fail | 101 | 57–61 |
| devstral:24b-small-2505-q4_K_M (9bd74193e939) | Mistral | 3/3 | 0/9 | 0 | 42 | pass, pass, pass | 100 | 30–34 |
| magistral:24b-small-2506-q4_K_M (27bcbbf6d324), model default (thinks) | Mistral | 0/3 | — | — | — | no verdict ×3 | 41 | — |
| magistral:24b-small-2506-q4_K_M, `--no-think` | Mistral | 3/3 | 0/9 | 0 | 1 | pass, fail, fail | 52 | 25–34 |
| gemma4:12b-it-q8_0 (41c402fdddc2), model default (thinks) | Google | 0/3 | — | — | — | no verdict ×3 | 205 | — |
| gemma4:12b-it-q8_0, `--no-think` | Google | 3/3 | 0/9 | 0 | 0 | pass, fail, pass | 45 | 38–41 |

The optional candidates were pulled because the first table left the second gate
slot empty (see Roles). Their first runs are in `bakeoff2/`, the thinking-off
runs in `bakeoff3/`. The `bakeoff2/` runs were made after unit NOTES-2 had
declared AC-3.2, and the driver at that time read the manifest from the working
tree, so those models were shown a control the NOTES-1 diff does not contain;
that driver defect is fixed (governed inputs are now read at the range head)
and the invalid results stand on their own ground — neither model produced a
parseable verdict for a reason unrelated to the manifest:

- Magistral (model default) answered in markdown fences with the gate
  definition's verdict-block shape instead of the driver's schema — verdict
  "pass", zero findings, 1 237 tokens — so the schema constraint did not bind.
  With thinking off it answers in the schema; its two "fail" verdicts rest on one
  finding each, the same one both times: `dispatch` "does not explicitly enumerate
  exceptions to the authentication requirement" — grounded, not a defect, not a
  planted truth.
- Gemma 4 12B (model default) thought for 23 885 characters, hit the 8 192-token
  generation cap with `done_reason=length` and 9 019 tokens generated against a
  16 384 context already holding a 9 727-token prompt: the answer was cut inside a
  string. With thinking off it is the fastest valid reviewer here (45 s) and finds
  nothing; its one "fail" is a hypothetical B2 against `dispatch`.

Per repetition, Gemma 4 31B:

- rep 1: B3 blocking on `delete_note` (quote `return require_auth(request, self.principals, handler)`, src/app.py:58) — "lacks the ownership authorization check (require_owner)"; B4 blocking, tests/test_notes.py — "negative tests for authorization are missing for the DELETE endpoint". Truths 1 and 3.
- rep 2: the B3 finding only, same line, same diagnosis. Truth 1.
- rep 3: B3 as above; B4 blocking quoting the owner's own delete test — "no test case verifying that a non-owner is rejected (403)"; B8 blocking on `return fn(request)` in `dispatch` (src/app.py:89) — "does not catch generic exceptions (e.g., JSONDecodeError)". Truths 1, 2 and 3.

What the other three did, every repetition:

- Mistral Small 3.2 and Devstral (same base family) judged all eleven base items
  pass and emitted one "finding" per checklist item that is really a paragraph of
  commentary ("The require_owner function ensures ... This is acceptable") — fourteen
  per run, all on items they had judged pass, all discarded as inconsistent. Their
  verdict on code with an authenticated-user-deletes-anyone's-note hole was **pass**.
  In gate run 3 of NOTES-1 Mistral also passed the fixed code; a reviewer that
  passes both states of the code is measuring nothing.
- Llama 3.1 8B raised a finding on every checklist item, most of them quoting
  `import json`, five of them *blocking* (B1, B5, B10, B11 among them — items the
  change does not touch), plus eight ungrounded findings whose quotes had been
  rewritten with single quotes. Zero of the planted defects. Verdict fail for the
  wrong reasons. This is the 8B floor the smoke run had already shown.

## Roles

| role | model | why |
|---|---|---|
| security gate, primary | gemma4:31b-it-q4_K_M | the only candidate that found any planted defect; found the authorization hole 3/3 with the exact line, zero hallucinations in nine findings; its fail verdicts were for the right reasons |
| security gate, second (bias firewall) | **none qualifies on this hardware** | must be a different vendor from the primary and must find at least one planted defect; every non-Google candidate that fits 24 GB and the provenance rule (Mistral Small 3.2, Magistral, Llama 3.1 8B) found 0/9. Until a qualifying second model exists, the second signature on a unit is the human's line-by-line review, and the gate log says so (NOTES-2 run 3 is Mistral passing what Gemma failed) |
| build (CW1), never the gate | devstral:24b-small-2505-q4_K_M | writes parseable, schema-shaped files under src/ and tests/; its review-role result is irrelevant to this role — the gate is a different model in a different process |

## Rejected, with reasons

- **mistral-small3.2:24b-instruct-2506-q4_K_M as a gate model** — 0/9 planted
  defects over three repetitions, verdict pass on code with an authorization hole;
  42 commentary "findings" on items it judged pass. Kept as an allied-nation
  candidate for the build role only.
- **llama3.1:8b-instruct-q8_0 as a gate model** — 0/9; 24 ungrounded findings;
  blocking findings on untouched checklist items. Recorded fail in NOTES-1 run 1
  as well (could not complete the completeness questions then).
- **devstral:24b-small-2505-q4_K_M as a gate model** — same behaviour as Mistral
  Small 3.2 (0/9, 42 inconsistent, pass on broken code); it is a build model.
- **Llama 3.3 70B** — does not fit 24 GB.
- **gpt-oss-120b** — GB10-class memory.
- **Qwen, DeepSeek, GLM, Kimi, MiniMax and every other PRC-origin base** — the
  provenance rule.
- **magistral:24b-small-2506-q4_K_M** — no verdict with its default thinking
  (fenced markdown, wrong shape); 0/9 with thinking off.
- **gemma4:12b-it-q8_0** — no verdict with its default thinking (generation cap
  and context overrun); 0/9 with thinking off. Same vendor as the primary in any
  case, so it could never be the firewall.
- **Gemma 4 26B MoE (a4b)** — 4B active parameters; not measured, and same
  vendor as the primary.
- **any `:latest` tag** — not pinned; identity would change under the gate log.

## Reading the numbers honestly

- "Truths found" is scored by fragment match on grounded findings; a model that
  described the hole in prose while quoting a neighbouring line of the same route
  counts, a model that quoted the right line while describing something else does
  not. The rescoring (`bakeoff.py --rescore`) reads the saved copies and re-runs
  nothing.
- The gate accepts a verdict only after the driver's grounding and consistency
  filters; the raw model output is in the `.log` file beside each verdict copy.
- Three repetitions at temperature 0 are not independent samples for the
  deterministic models (Mistral, Devstral and Llama repeated themselves almost to
  the token); they are for Gemma, whose three answers differed. Nine findings, nine
  grounded, is the number that carries weight.
- Two benchmark ranges now: NOTES-1 run 2 above, and NOTES-3 run 2 below.

## Second benchmark: NOTES-3 run 2 — three subtler defects, by class

Planted by hand on the demo's `unit/NOTES-3` (range `efde0bc667ad..24f02db60100`),
each invisible to the mechanical checks: **D1 cryptographic hygiene** —
`Principals.principal_for` compares tokens with `==` instead of
`hmac.compare_digest`; **D2 information leak** — `dispatch` answers an unexpected
exception with `repr(e)` and `traceback.format_exc()`; **D3 authorization in the
wrong layer** — `GET /notes/search/<term>` returns every owner's matches and the
owner filter lives only in `src/client.py`, which the tests go through (so the
negative-tests check saw a cross-principal test and was satisfied). Two
repetitions each, results in `bakeoff-notes3/`.

| model | valid | D1 timing | D2 leak | D3 client-only scoping | ungrounded | inconsistent | verdict | mean s |
|---|---|---|---|---|---|---|---|---|
| gemma4:31b-it-q4_K_M | 2/2 | — | **2/2 blocking**, exact line | **2/2 blocking**, exact line, names src/client.py | 0 | 0 | fail, fail | 342 |
| mistral-small3.2:24b-instruct-2506-q4_K_M | 2/2 | — | 2/2 but **non-blocking** | — | 0 | 0 | pass, pass | 81 |
| llama3.1:8b-instruct-q8_0 | 1/2 | — | — | — | 0 | 25 | fail (four "may not" hypotheticals against `def` lines), invalid | 55 |
| devstral:24b-small-2505-q4_K_M | 0/2 | — | — | — | 0 | 5 | invalid ×2 (completeness not repairable) | 75 |

What the classes say:

- **Authorization and leakage** are where Gemma is reliable: four for four across
  the two units on "who can see what" (DELETE guard, write-before-guard,
  client-only scoping) and two for two on "what leaks" (unguarded decode, traceback
  in the body), every one at the exact line, none invented.
- **Cryptographic hygiene** nobody found. The `==` comparison sits next to a
  removed `hmac` import in the diff; the checklist item that names cryptography
  (ELEVATED1) is informational at this tier, and B2 asks about completeness of
  authentication, not its constant-timeness. A checklist line is the fix, not a
  bigger model — and it is a governance change, so it is proposed, not made, here:
  "B2a. Credential comparison — secrets and tokens are compared in constant time
  (`hmac.compare_digest` or equivalent); `==` on a secret is a finding."
- **Mistral's one catch** was rated non-blocking, so its verdict stayed pass; a
  reviewer that sees the traceback leak and does not block on it is not a gate.
- Gemma's rep 1 carried a third finding (a manifest gap) whose quote was a lone `]`
  — present in every diff, so it grounded trivially. The driver now requires a
  quote with substance (eight non-space characters and a word); that finding would
  be discarded as ungrounded today.
