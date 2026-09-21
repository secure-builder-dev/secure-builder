# Lifecycle exercise

© 2026 Casey Houle. All rights reserved.

v1.0.md clause 6. One full lifecycle exercised end to end on a throwaway
project: build -> gate -> finding -> disposition -> record -> close. Every step
was performed through the placed harness's own command line
(`python .engine/harness/run.py ...`), never through the self-test helpers.

Date: 2026-09-20
Throwaway project: C:/Users/cjhou/AppData/Local/Temp/lifecycle-demo (a fresh
git repository; harness placed with `engine update --project`, initialized
`track=web tier=IL4 provider=aws mode=local topology=single side=local`)
Range gated: b7a593b2d1053d8169bcd2f5a8bfde18ba46df56..42a983abca1a40e73f896cf86ae5c6a526b65c35
(unit U1 on branch unit/U1; run 1 covered b7a593b2d105..ca26a2fd590f, run 2 the range above)
Gate-log rows produced: 3 (U1#1 advisory, U1#2 advisory, U1#1s superseding U1#1)
Finding raised and dispositioned: F-1 — "record-scoped route reachable by
another principal (no cross-principal negative test)", raised by the
negative-tests check on U1 run 2 against GET /items/ID; fixed by owner
scoping (AC-3.2, require_owner) with 401 and 403 negative tests; dispositioned
in the findings register table A (mechanism: the negative-tests check; lives in
engine/gate.py; decided by Casey Houle). Two further gate findings were raised
and dispositioned on the way: manifest-entry (AC-3.1 declared; governance row
GOV-1) and governance (rows GOV-1, GOV-2; the bundled governance commit was
split). One standing-state delta (control_manifest_result template-only ->
resolved) opened a ticket, which was closed with its reason. One ungated
bookkeeping commit was recorded as an accepted risk (R-1), which in turn showed
the probe needed the bookkeeping rule below.

## Steps, in order

1. PLAN: `unit new id=U1`; `item new id=DEMO-1 ... done_when="GET /items/ID
   returns 401 without a token and 403 for another user's item"`; `item claim`;
   branch unit/U1.
2. BUILD: route, auth guard, tests; `unit building`.
3. SCAN: `scan` — refused as impossible (no container runtime, no scanner on the
   path), no stamp written.
4. HANDOFF: `handoff --scan-impossible "..."` — override announced in the
   handoff; started marker written.
5. GATE: `coverage project`; `gate prepare unit=U1 run=1 ...` — quality gate
   passed; security mechanical part raised manifest-entry (blocking) and
   plan-edits. Declared AC-3.1; `mutate` proved it (suite failed under
   mutation); governance row GOV-1 recorded; delta ticket closed. Re-gated:
   clean. `gate no-model unit=U1 run=1 attested_by="Casey Houle"`.
6. FINDING: the route was re-registered on the app object so the generated
   route inventory sees it; `gate prepare ... run=2` raised negative-tests
   (blocking): no 401 test naming the route and no cross-principal test on a
   record-scoped route.
7. DISPOSITION: owner scoping added (AC-3.2), 401/403 tests added, AC-3.2
   declared and mutation-proven, governance row GOV-2 in its own commit;
   re-gated clean; `gate no-model unit=U1 run=2`; `record finding id=F-1 ...`.
8. RECORD: gate-log rows U1#1, U1#2; findings register F-1; governance
   changelog GOV-1, GOV-2; mutation-results AC-3.1, AC-3.2; supersession row
   for U1#1 (its started marker had been deleted by hand); risk row R-1.
9. CLOSE: `item review`, `item done id=DEMO-1`; `unit review`; fast-forward
   merge to main by the human; `unit merged id=U1`; `check` GREEN on main;
   `export package` produced a 24-artifact evidence bundle bound to the commit
   (incomplete: no composition inventory, retention not configured — both
   stated in the manifest).

## What the exercise found in the harness (each fixed with a regression test)

- A placed project has no `selftest/` of its own, so `check` reported an absent
  suite. The single command now runs the placed copy's suite in its own process
  from the placed harness directory, with a nesting guard; the placed package now carries
  the whole package (engine/dist included) so its suite is layout-independent.
- Six shipped tests inspected the build repository's layout (CI workflow,
  hooks/); made layout-independent, and the CI test moved to
  tools/build_test.py.
- The audit excluded `.engine` by absolute path component, not relative.
- `scan` where scanning is impossible stamped the commit red, and the red stamp
  then blocked the override meant for that case. An impossible scan (no
  runtime, no scanner on the path) is now refused before any stamp is written.
- A branch named unit/U1 put a slash in the unit identifier and the started
  marker could not be written. The unit is the branch's last segment.
- A Python project had no way to produce the coverage report the range check
  reads: `coverage project` measures the project's unittest suite with the
  standard-library collector.
- Harness updates committed on the branch put engine-owned files in the range,
  and the project's coverage could never cover them: `.engine/` is excluded.
- PLAN then BUILD on one branch read the unit state transition as a design
  edit: plan edits are now judged per commit against the unit's state in that
  commit.
- The placed harness's own test fixtures satisfied the project's negative-test
  requirement for a route they mention: `.engine/` is excluded from the
  project's tests.
- Records/tickets/unit-state commits after a merge were reported as ungated
  inbound code: bookkeeping commits are named and not reported as code.

## Honesty notes

- Both gate runs were recorded with `gate no-model` (mechanical checks and the
  record; checklist not applied; verdict advisory), because no reviewer session
  was launched on this workstation. A reviewer run is `review unit=U1 run=2`
  with `ENGINE_ASSISTANT_CMD` set, in a fresh session. The coverage inventory
  therefore reports the six source files as never assessed, which is true.
- The exercise was driven by the build session on the author's behalf; the
  attestations name Casey Houle, whose signature is on every commit of this
  repository. Re-performing it by hand is one afternoon and is recommended
  before v1.0 is announced to anyone else.
