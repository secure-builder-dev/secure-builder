# Build Strategy — Driving the Implementation with an AI Assistant

**Version:** 1.1 · drafted 2026-09-20, hardened after gap analysis
**Part of:** Engine Specification Package
**Status:** operational document — this one *is* prescriptive about mechanism, unlike specs 01–06
**Copyright:** © 2026 Casey Houle. All rights reserved. Confidential — not for distribution.

---

## 0. What this document is, and the one thing it must get right

Specs 01–06 say what to build. This says how to actually get it built on one machine, by one person
driving an AI assistant, without the build stalling at 60% and without shipping a harness whose
checks cannot fail.

The hard part is not writing the code. An assistant will write 368 requirements' worth of shell and
tests faster than you can review it. The hard parts are three:

1. **Termination.** "Run until v1.0" requires a machine-checkable definition of v1.0. Without one,
   the loop either never stops or stops the first time the assistant feels finished — and it will
   feel finished early, repeatedly, with confidence.
2. **Bootstrapping.** You are building the thing that catches vacuous checks, using a process that
   has no such thing yet. Everything built before the self-test harness exists is unverified by
   construction, and the order in §3 exists to make that window as small as possible.
3. **Erosion under autonomy.** Every softening in spec 00 §5.3 is locally reasonable. An unattended
   loop will take each of them, one per session, each defensible, and you will end up with a green
   harness that checks nothing. The counter is not better prompting. It is **enforcement outside the
   assistant's judgment** — the same principle spec 06 §4.5 states about precedence, applied to your
   own build.

Everything below is in service of those three.

---

## 1. Definition of v1.0 — write this before anything else

**Do not start the loop without this file.** It is the loop's exit condition, and it is the only
defense against a confident premature "complete".

`v1.0.md`, at the repo root, human-authored, never edited by the assistant:

```
v1.0 is reached when ALL of the following are true, each verified by `make progress`:

1. Every MUST requirement in specs 01-06 is either
     - implemented, with a pointer to the implementing file, or
     - explicitly deferred, with a written reason and a v1.1 tag.
   Zero requirements in state `todo` or `doing`.

2. Every implemented check has a mutation receipt on disk proving it has been
   observed failing. No receipt, no credit.

3. `make check` is green from a clean clone, on a machine with no prior state.

4. The self-test suite runs from `make check`, reports pass/fail/skip separately,
   and its skip count is zero or every skip is named in v1.0.md.

5. The requirement-to-implementation table has no row reading "unknown".

6. One full lifecycle has been exercised end to end on a throwaway project:
   build -> gate -> finding -> disposition -> record -> close.

7. The degradation statement (spec 04 §7) exists and is accurate.
```

Three properties matter here. It is **short** — you will read it many times. Every clause is
**machine-checkable** except clause 6, which you check by doing it once. And it contains **no
percentages**, because a percentage is a number the loop can optimize toward without doing the work.

---

## 2. The state model — the ledger is the build

The single most important structural decision: **the assistant's transcript is not the state. A file
is.** Sessions end, context compacts, the machine reboots. Anything that lives only in a
conversation is lost, and the next session will quietly rebuild a different mental model.

### 2.1 The ledger

One tab-separated row per requirement, generated once from the specs, then only ever updated:

```
req      spec  stage  status  impl                          receipt                  note
REQ-1.1  01    3      done    lib/verdict.sh                receipts/01-REQ-1.1.txt
REQ-4.2  01    9      doing   -                             -                        needs image bundle
REQ-8.3  06    -      defer   -                             -                        v1.1: req table tooling
```

**Statuses:** `todo` · `doing` · `done` · `defer` · `na`. Exactly five. `na` requires a note, and
`defer` requires a version tag.

Generate it mechanically — every requirement in the specs is a bolded `**REQ-n.n**`, so the initial
ledger is one `grep` away. Do not let the assistant hand-type it; it will drop rows and you will
never know which.

**Rule: the ledger is append-and-amend only, and every status change is its own commit alongside the
work.** A ledger updated in bulk at the end of a session is a ledger written from memory.

### 2.1a `make progress` is human-authored — the one component the loop may not write

`make progress` decides v1.0. It is the single check whose failure mode is *declaring the build
finished when it is not*, and it is therefore the one component to which this package's own rules
must be applied hardest — not the one to hand to the assistant along with everything else.

**Rules, and they are not negotiable for the same reason `v1.0.md` is not:**

- **You write it.** It is human-authored and human-owned, like `v1.0.md`. It is in the build's
  governance set (§5.1).
- **It gets negative fixtures before the loop starts.** At minimum: a ledger with a `done` row whose
  impl pointer does not exist must fail; a `done` row with no receipt must fail; a receipt whose
  broken-section output shows a *pass* must fail; an empty ledger must fail rather than reporting
  complete.
- **The empty case is the important one.** A `make progress` that iterates over the ledger and finds
  nothing must fail, not report success. "Nothing to check, therefore done" is the vacuous pass
  (§7.2 of spec 05) sitting on the exit condition itself.
- **It recomputes from the tree.** See §6. It never trusts a ledger row's own claim.

An assistant that writes both the work and the measure of the work has no independent check on
either. Everything else in this document assumes `make progress` is trustworthy; that assumption has
to be earned somewhere, and this is the only place it can be.

### 2.2 Mutation receipts

This is the artifact that makes the whole scheme resistant to the assistant's optimism.

For every check, a file `receipts/<spec>-<req>.txt` containing, in order:

```
REQ:        REQ-4.2.4
CHECK:      checks/scan-freshness.sh
MUTATION:   set the recorded data date to 200 days ago
--- output with the property broken (must show failure) ---
[scan] FAIL detection data is 200 days old, threshold 7
exit 1
--- output with the property restored (must show success) ---
[scan] PASS detection data 2 days old
exit 0
```

`make progress` refuses to count a requirement as `done` unless its receipt exists, is non-empty,
contains both sections, and the broken section contains a failure marker. That last clause is the
one that catches the interesting case: a receipt where the "broken" run passed anyway.

**The mutation must be a property-level edit.** Deleting the file under test, renaming a command, or
removing a dependency all produce a check that fails and therefore a receipt that looks valid — and
prove nothing, because a check that notices its own subject has vanished is not a check that notices
the subject is *wrong*. The receipt records the mutation as a diff against the implementation, and
a mutation that removes or renames rather than alters is not a mutation. Spot-checks (§2.2, below)
are where this gets caught; the constraint is stated so the assistant is not guessing at it.

**Why a file and not a claim in chat.** A claim in chat is unverifiable six weeks later and is lost
at compaction. A receipt is a durable artifact you can spot-check at random — and *tell the
assistant you will*. Pick three receipts a week and re-run the mutation yourself. If one doesn't
reproduce, that's a finding against the process, not against the check.

### 2.3 The journal

Append-only, one short block per session: what was attempted, what landed, what is blocked and why.
Three to six lines. This is for *you*, so that a Monday morning six weeks in doesn't start with
reading a diff to find out where you were.

Do not let it grow into a narrative. The ledger is the state; the journal is a breadcrumb trail.

---

## 3. Build order and what is parallelizable

Spec 00 §4 gives the 14 stages. What it doesn't say is which can run at once, which matters a great
deal for wall-clock time.

| Stages | Shape | Notes |
|---|---|---|
| 1 → 2 → 3 → 4 | **Strictly serial.** No parallelism. | Every later stage depends on the conventions these set. Doing these fast is a false economy — this is where you read every line. |
| 5 | **Fan out.** One agent per check. | Checks are independent by construction. This is the stage where parallel sessions pay. |
| 6 → 7 → 8 | Serial. | 8 consumes 6 and 7. |
| 9 | **Fan out.** One agent per scanner. | Most environment-dependent stage; expect the most rework. |
| 10, 11, 12 | Independent of each other. Can run in parallel after 8. | |
| 13 → 14 | Serial, last. | 14 assembles what 6–12 produce. |

**The bootstrap window is stages 1–3.** Everything built there is unverified, because the thing that
verifies is stage 4. Keep that window small, review it by hand, and then — this is the part people
skip — **go back and retrofit stage 4's discipline onto stages 1–3** as the first act after stage 4
lands. Write the mutation receipts for those early components before moving to stage 5. If you don't
do it then, you never will, and the foundation of the harness will be its least-proven part.

**A note on stage 5.** It is tempting to fan out eight checks at once. Do three. The first three
will surface conventions you didn't know you needed — how failures print, how paths resolve, how
fixtures are laid out — and fixing those across eight in-flight branches costs more than the
parallelism saved.

---

## 4. The agent roster

Four roles. The separation is not ceremony; three of the four exist because of a specific failure
mode in the other.

### 4.1 Builder

Implements requirements. Sees: the requirement text, the relevant spec sections, the existing code.
Writes code, tests, receipts. Commits.

Give it the *rationale*, not just the requirement. A builder that knows the failure a requirement was
written against makes better calls on the twenty details the requirement doesn't cover. This is why
the specs carry rationales at all.

### 4.2 Adversary

**The highest-value agent in the roster, and the one most likely to be cut.**

Runs in a **separate session** that has never seen the builder's reasoning. Sees exactly three
things: the requirement text, the diff, and the receipt. Its job is not to review style. Its job is
a single question:

> *Construct an input, environment, or sequence under which this check passes while the property it
> asserts is false.*

If it can, that's a finding and the requirement goes back to `doing`.

This is spec 03 §2 applied to your own build. The builder cannot do this job — not because it isn't
capable, but because it spent the last hour constructing the reasons the check is correct, and those
reasons are now in its context. Isolation is the mechanism. A "now review your own work" turn in the
same session is not isolation and does not substitute.

**Run the adversary on every check.** Not on a sample. The whole point is that you cannot tell in
advance which check is the vacuous one.

### 4.3 Spec interpreter

Answers "what does REQ-x.y actually require here" **without seeing the implementation**. Sees the
specs only.

This exists because of a specific and very common failure: you ask the builder whether its code
satisfies a requirement, and it answers by reading the requirement in the light of the code it just
wrote. The requirement bends. Asking an agent that has never seen the code gets you the requirement's
plain meaning, which is what you wanted.

Use it whenever you're about to accept a requirement as satisfied and you feel even slight doubt.

### 4.4 Ledger keeper

Mechanical. Updates rows, verifies receipt well-formedness, runs `make progress`, reports drift
between the ledger and the tree. Small model, cheap, high frequency.

Keep this separate from the builder for one reason: **the agent that does the work should not be the
agent that records whether the work is done.** That is the same self-approval principle your own
permanent-checks register already states — an agent may not accept its own finding.

---

## 5. The loop

Two layers. The inner layer keeps a single session working; the outer layer survives crashes,
context exhaustion, and the machine rebooting.

### 5.1 Inner loop — the stop hook

A `Stop` hook can block a session from ending. That is the mechanism that makes "doesn't stop until
v1.0" real rather than aspirational:

```
on Stop:
    run `make progress --quiet`
    if exit 0  ->  allow stop, v1.0 reached
    else       ->  block, and inject:
                   "Ledger shows N todo, M doing. Continue with the
                    lowest-numbered actionable requirement."
```

Two guards on it, both necessary:

- **A stall detector.** If the ledger hasn't changed in three consecutive stop-blocks, allow the
  stop and write a `BLOCKED` entry to the journal. A loop that cannot progress must surface that,
  not spin. Spinning burns tokens and produces increasingly creative non-work.
- **A governance tripwire.** If the next actionable requirement is in the governance set, allow the
  stop and queue the item for human review. **This is not optional.** An assistant editing the rules
  that constrain it is the one loop in the package with no check on it, by construction.

  **The build's governance set, from day one.** Spec 01 §11 defines the governance set for a
  *finished* harness — instruction files, reviewer definitions, anything altering gate behavior. On
  day three of the build none of those exist, so a tripwire pointed at them matches nothing and
  never fires. Name the build's own set explicitly instead, before the first iteration:

  ```
  v1.0.md              the exit condition
  make progress        the thing that evaluates it
  the hooks            pre-commit, Stop
  prompts/iteration.md the loop's instructions
  specs 00-08          the requirements themselves
  ```

  These are human-owned for the duration of the build. As the harness grows its own governance
  artifacts, they are added to the list. A tripwire matching a list that is empty on the day it
  matters is the same defect as a check that passes when it finds nothing.

### 5.2 Outer loop — the driver

A shell script, run in a terminal you can leave open:

```sh
#!/bin/sh
# drive.sh — outer loop. Survives crashes and context exhaustion.
set -u
i=0
while [ "$i" -lt 200 ]; do
    i=$((i + 1))
    make progress --quiet && { echo "v1.0 reached at iteration $i"; break; }

    claude -p "$(cat prompts/iteration.md)" --permission-mode acceptEdits
    rc=$?

    git rev-parse HEAD >> .journal/heads
    [ "$rc" -eq 0 ] || echo "iteration $i exited $rc" >> .journal/errors

    # stall guard: keyed on DONE COUNT, not on HEAD. See note below.
    make progress --count-done >> .journal/done-counts
    tail -3 .journal/done-counts | sort -u | wc -l | grep -q '^ *1$' && {
        echo "STALLED after iteration $i — see .journal/errors"; break; }

    # budget guard
    make progress --spend-check || {
        echo "BUDGET reached at iteration $i"; break; }
done
```

**Why the stall guard keys on the done count and not on the commit.** The obvious version compares
recent `HEAD`s and stops when they stop changing. It does not work, and the reason is specific: the
loop's *first* act each iteration is to set a requirement to `doing` and commit that. So every
iteration produces a new `HEAD` whether or not any work happened, and the detector is defeated by
the loop's own bookkeeping. The count of `done` requirements only moves when something is actually
finished, which is the property being measured. This is a small bug with a large blast radius — an
undetected stall spins until the iteration cap, producing increasingly creative non-work.

**On the budget guard.** An unattended loop on a personal account needs a spend ceiling you set,
checked every iteration, that stops cleanly and writes the reason. The iteration cap is not a spend
control: 368 requirements at roughly one per iteration means the cap of 200 is *below* the work, not
above it, so the cap will be hit legitimately and raised, and then it constrains nothing.

**The honest size of this.** Somewhere around 350–400 iterations for a full v1.0, most of them
short. Knowing the rough number up front changes how you schedule it, and not knowing it is how a
build gets abandoned at 60% because it was expected to take a weekend.

Points that matter more than they look:

- **Every iteration starts a fresh session.** No accumulated context, no drift, no compaction
  surprises. The ledger carries state across iterations; that is its entire job.
- **The driver is dumb on purpose.** All intelligence is in `prompts/iteration.md` and the ledger.
  A driver with logic in it becomes a second source of truth.
- **The iteration cap and the stall guard are both required.** Unbounded is a token fire with no
  smoke alarm.
- **Run it attended for the first ten iterations.** Watch what it does. You are calibrating the
  iteration prompt, and you will change it three or four times. After that it can run unattended.

### 5.3 The iteration prompt

The single most leveraged file in the build. Keep it under a page:

```
Read ledger.tsv. Pick the lowest-numbered requirement with status `todo`
whose stage prerequisites are all `done`. Set it to `doing` and commit that.

Read the requirement and its rationale from the spec. If the requirement is
ambiguous, do not guess: write the question to .journal/questions and pick
the next requirement instead.

Implement it. Write the test first, watch it fail, then make it pass.

Mutate: break the property, capture the failing output, restore, capture the
passing output. Write receipts/<spec>-<req>.txt.
If the mutation does NOT produce a failure, the test is wrong. Fix the test,
not the code, and do not mark done.

Run `make check`. If red, fix before continuing. Never commit past a red check.

Update the ledger to `done` with the impl pointer and receipt path. Commit.

Append three lines to the journal. Stop.
```

**Two mechanical points the prompt depends on.**

*Ordering.* Requirement identifiers are **not unique across specs** — spec 01 and spec 03 both have
a `REQ-1.1.1`. The ledger keys on (spec, req) so rows are unambiguous, but "the lowest-numbered
requirement" is not, and an autonomous loop will resolve that ambiguity differently on different
days. Define the order once: **spec number, then requirement number within the spec, compared
numerically by component.** Write it in the prompt, not in your head.

*A requirement that is wrong.* Ambiguity goes to `.journal/questions`. A requirement that is
**incorrect** is a different case, and across 368 of them there will be several. Without a path, the
loop will either implement something it knows is wrong or quietly reinterpret it, and no record will
exist either way — which is, ironically, a governance failure inside a package with a governance
protocol.

So: an **amendment log** in the build repo. One row per amendment: the requirement, why it is wrong,
what replaces it, who decided, and the date. The ledger row points at it. This is spec 01 §11.8's
governance changelog applied to the specs themselves, it costs nothing, and it is what makes a v1.1
of this package possible instead of a rewrite. One more line in the prompt:

```
If a requirement is WRONG rather than ambiguous, do not implement it and do not
reinterpret it. Write the case to .journal/amendments-proposed and move on.
Amendments are decided by the human, never by the loop.
```

**Verify the two loop layers do not fight, on day one.** The inner Stop hook blocks a session from
ending; the outer driver starts a fresh session per iteration. A blocking Stop hook inside a
**non-interactive** invocation is the one mechanism in this document I would not assume behaves as
described — it may loop within that single session rather than returning to the driver, possibly
without bound. Test it deliberately during the attended iterations: let one iteration complete and
confirm the process actually exits and the *driver* starts the next. If it does not, drop the Stop
hook and let the driver carry the loop alone. The driver is the layer that survives crashes; the
Stop hook is a convenience.

Three deliberate choices in there. **One requirement per iteration** — the fresh session makes batching
tempting and batching is how receipts get skipped. **Ambiguity goes to a question file, not to a
guess** — this is the single highest-value line in the prompt, and reading `.journal/questions` each
morning is your main steering input. **"Fix the test, not the code"** on a failed mutation, because
the instinct is exactly backwards there.

---

## 6. Enforcement outside the assistant's judgment

Prompt instructions are honored until they're inconvenient. These are not.

| Guard | Mechanism | Catches |
|---|---|---|
| No commit with `doing` rows lacking a receipt | Pre-commit hook | Silent skipping of the mutation step |
| No commit while `make check` is red | Pre-commit hook | The observed "continued past a failed verification" defect |
| Receipt well-formedness | `make progress` | Empty, truncated, or single-section receipts |
| Broken-section-must-fail | `make progress` | A mutation that didn't actually break anything |
| Governance files unwritable by the loop | File permissions, plus a hook | The assistant editing its own constraints |
| Ledger vs. tree drift | Ledger keeper, every iteration | Rows marked done whose impl pointer doesn't exist |

That last row deserves emphasis. **`make progress` must recompute from the tree, never trust the
ledger's own claims.** A `done` row whose `impl` path doesn't exist, or whose receipt is missing, is
a drift finding and gets reset to `todo` automatically. Self-reported progress is exactly the class
of defect this entire package exists to eliminate; it would be absurd to build it on self-reported
progress.

---

## 7. Efficiency

Unglamorous and worth real money over a build this size.

**Feed sections, not documents.** Give each iteration only the spec sections the requirement cites.
A script that extracts `§n` from a spec file pays for itself in a day. Pasting all six specs into
every iteration is the default failure and it is expensive and it makes the output *worse*, because
the relevant requirement is diluted.

**Tier the models.** Ledger keeping, receipt validation, and mechanical file edits go to the small
fast model. Builder and adversary work goes to the strong one. Roughly: tier the work by whether a
subtle wrong answer would be caught by something downstream.

**End every iteration at a commit.** Never let a session compact mid-requirement. A compacted session
resumes with a summary of its own reasoning, which is the least reliable input available.

**Batch the adversary.** Run it over the last five requirements at once rather than one at a time.
It needs the diff and the receipts, both small, and the fixed cost of framing the adversarial task
dominates.

**Don't re-derive the ledger.** Read it, don't regenerate it. Regeneration silently drops your
`defer` and `na` notes, and nothing will tell you.

**Let `make check` be the feedback loop, not the assistant's reading of the code.** Running the check
is cheap and definitive; asking the assistant whether the code is correct is expensive and it is a
guess dressed as an answer.

---

## 8. Failure modes of the loop itself

| Symptom | Cause | Response |
|---|---|---|
| Ledger advances, `make check` never gets harder | Checks are being written vacuously | Stop. Run the adversary over everything done so far. This is the expensive failure — catch it at iteration 20, not 120. |
| Same requirement cycles `doing` → `todo` | Genuine ambiguity the prompt can't resolve | It belongs in `.journal/questions`. Answer it yourself and add the answer to the spec as a clarification. |
| Receipts exist but are thin | Mutation is being performed as a gesture | Spot-check three. Tighten the receipt schema if they don't reproduce. |
| Iterations get slower and longer | Context bloat from a growing journal or ledger | The journal is three lines per session. Enforce it. |
| Everything green, clause 6 of v1.0 fails | The parts work, the lifecycle doesn't | Expected. Clause 6 is there precisely because unit-level green does not imply the system runs. |
| Assistant reports v1.0 complete | It feels finished | `make progress` decides. It is not a matter of opinion and you do not need to argue about it. |
| Loop spins, ledger `done` count flat | Stall detector keyed on the wrong signal | Key it on the done count, never on commit HEAD (§5.2) |
| Receipts valid, checks still weak | Mutations removed the subject rather than altering it | §2.2. Tighten the receipt schema and re-audit |

---

## 9. Human checkpoints

Unattended is the goal for the build stages. These four are not negotiable, and each is a place
where the loop hands back rather than proceeding:

1. **Before the loop starts** — `v1.0.md` and the generated ledger. Read every row once. This is an
   hour and it sets the terminating condition for the entire build.
2. **After stage 4** — the self-test harness. You are about to trust it for 300 requirements. Read
   it line by line, and verify the retrofit onto stages 1–3 actually happened.
3. **Every governance item** — spec 01 §11. Queued by the tripwire, reviewed line by line, never
   batch-approved.
4. **Weekly: three random receipts** — re-run the mutations yourself. Fifteen minutes. It is the
   only sampling that catches systematic receipt gaming, and its deterrent value exceeds its
   detection value. Check specifically that each mutation *altered behavior* rather than removing
   the subject (§2.2).
5. **Every proposed amendment** — a requirement the loop believes is wrong. You decide, and the
   decision lands in the amendment log.

Everything else can run while you sleep.

---

## 10. Order of operations, day one

0. **Document 10 first.** Local git identity, commit signing, `LICENSE`, `PROVENANCE.md`. Twenty
   minutes, before the first commit, and none of it can be done retroactively.
1. Create the repo. Copy in specs 00–08. They are the input, not the product — nothing generated
   overwrites them.
2. Write `v1.0.md` by hand (§1).
3. Generate `ledger.tsv` from the specs mechanically. Read it. Mark obvious `defer` and `na` rows now
   — deciding scope later, mid-loop, is how scope grows.
4. Write `make progress` **first**, before any harness code. It is the exit condition; without it
   the loop has no meaning. It should be the first thing that works.
5. Write `make progress`'s negative fixtures and watch each one fail (§2.1a). This is the step that
   makes everything downstream mean anything.
6. Write the pre-commit hook and the stop hook (§5.1, §6). Name the build's governance set.
7. Write `prompts/iteration.md` (§5.3), including the ordering rule, the amendment path, and the
   copyright header on every authored file (doc 10 §1.3).
8. Set the budget ceiling.
9. Run ten iterations attended. Confirm the two loop layers do not fight (§5.3). Fix the prompt.
   Fix it again.
10. Start `drive.sh`. Check `.journal/questions` and `.journal/amendments-proposed` each morning.

**Step 4 is the one to resist reordering.** Building `make progress` before there is anything to
measure feels backwards and is the single highest-leverage hour in the build: it is the file that
decides what "done" means, and writing it early forces you to answer that question while it is still
cheap to answer.

---

## 11. What "complete" will actually feel like

The loop will report v1.0 before the harness is good. That is not a defect in the process — it is
the difference between *specified* and *mature*. Clauses 1–7 of §1 are satisfiable by a harness that
has never been pointed at a real project.

So: v1.0 is the point at which the harness is ready to be **used**, not the point at which it is
finished. Its first real project will produce a findings list, and those findings get sorted the way
every other finding does — mechanical becomes a check, judgment becomes a checklist line. That sorting
is the actual maturation process, and it does not run on a loop. It runs on use.

Plan for v1.0 to be reached, and then for the first project to be the real review.
