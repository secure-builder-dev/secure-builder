# Field Mode — Behavioral Specification

**Version:** 1.0 · drafted 2026-09-20
**Part of:** Engine Specification Package
**Status:** specification only — implementation-independent
**Copyright:** © 2026 Casey Houle. All rights reserved. Confidential — not for distribution.

---

## 0. Scope

Companion spec 04 defines three operating modes distinguished by **connectivity**. This document
defines a fourth, distinguished by **time and personnel**: one operator, under time pressure, with
no reachback, fixing something that is already deployed and already mattering.

It is not "disconnected mode in a hurry." Disconnected mode changes where the data comes from and
guarantees the same verdicts. Field mode changes **what can be performed at all** — there is no
second human to approve, there may be no time to run the full suite, and the hardware may not be
able to host a capable reviewer. Those are different losses and they need their own accounting.

**Why this is a mode and not a waiver.** The pressure to skip the process at the edge is real and
mostly legitimate — a gate that costs an hour is the wrong tool when something is broken now. The
choice is not between discipline and speed. It is between **degradation that is declared and
tracked** and degradation that happens anyway, silently, and is discovered later by someone reading
a diff and asking who approved it.

**Relationship to the two-instance topology.** Field mode is the far-side case of companion spec 04
§10 with the transfer window removed entirely. Everything there about divergence, back-port status
and record authority applies, and §7 below is its specialization.

---

## 1. The governing principle

**REQ-1.1** Field mode MUST NOT be a weaker gate. It MUST be a **bounded** gate that incurs a
**recorded debt**.

**Rationale, and this is the whole design.** A weaker gate produces a verdict that looks like a
verdict and means less, which is the false-green failure in institutional form. A bounded gate
produces a verdict that states its own boundary — what ran, what did not, and what is therefore
owed — and the thing owed is tracked until it is paid. The first erodes the system. The second is
the system working under conditions it was told about.

**REQ-1.2** Every check deferred in field mode MUST create a **reconciliation obligation** that is
durable, countable, and aged.

**REQ-1.3** A field verdict MUST NOT be presentable as an ordinary gate pass anywhere in the record
set or in an evidence export.

**Rationale.** Identical to the reviewer-class requirement in companion spec 02 §3.1.5, and for the
same reason: a record that does not distinguish between two different things performed under two
different conditions destroys the series for both.

---

## 2. Entry and exit

**REQ-2.1** Field mode MUST be entered by **explicit declaration**, never inferred from a slow
network, a missing device, a failed check, or elapsed time.

**Rationale.** An inferred entry makes field mode the default, because it is faster and because the
conditions that trigger inference are common. Within a month every gate is a field gate and the
discipline is gone with nobody having decided to abandon it.

**REQ-2.2** Entry MUST record: who declared it, when, and **why** — the operational reason, in a
sentence.

**REQ-2.3** Field mode MUST NOT be enterable to escape a **failing** check. It is available where
the full process is **impossible**, never where it is merely inconvenient or unwelcome.

**Rationale.** This is the same distinction companion spec 01 REQ-3.3.2 draws for the scan override,
and the same reason it is drawn there. An escape hatch that can absorb a failure is a mechanism for
passing with known defects, and it will be used that way under pressure by people acting in good
faith.

**REQ-2.4** The implementation MUST distinguish *could not run* from *did not run in time*, and
MUST NOT record the second as the first.

**REQ-2.5** Exit from field mode is **reconciliation** (§7), not a configuration change. Setting the
mode back does not discharge the obligations recorded under it.

---

## 3. What still runs — the floor

**REQ-3.1** The following MUST run in field mode and MUST NOT be deferrable:

| Check | Why it is non-deferrable |
|---|---|
| Credential scan | Seconds to run; a leaked credential at the edge is unrecoverable |
| Injection scan | Seconds to run |
| Control manifest verification | Fast, and it is the check that catches a fix having disarmed a control |
| Reference and citation integrity | Fast, and a record with broken pointers is not a record |
| Record write (§6) | The whole point |

**Rationale for the manifest in particular.** A hurried fix is exactly the change most likely to
remove a control's last call site — a guard commented out to isolate a problem and not restored, an
import dropped during a revert. Verification is fast, it is mechanical, it needs no human, and it
catches the single most dangerous thing a field fix does.

**REQ-3.2** The failure semantics of companion spec 01 §13 apply **unchanged** in field mode. A
check that runs and cannot complete its function MUST NOT exit zero.

**Rationale.** Everything else here bends. This does not, because the entire value of the record
produced in the field depends on its individual lines meaning what they say. A field verdict that
is honest about being partial is useful. A field verdict containing one silently vacuous pass is
worse than no verdict, and the reader has no way to tell them apart.

**REQ-3.3** Records (companion spec 02) are **not** degradable. If anything, the record matters more
here, because it is the only account of a change that no second person witnessed.

---

## 4. What degrades, precisely

**REQ-4.1** The implementation MUST maintain an explicit table of what field mode changes. Nothing
degrades that is not on the table.

| Capability | Normal | Field mode |
|---|---|---|
| Two-window isolation (spec 03 §2) | Separate reviewing context | **Retained** — it costs nothing but a second session |
| Human merge approval (spec 01 §3.5) | Required | **Not achieved.** Stated in the verdict |
| Separation of duties | Builder ≠ approver | **Not achieved.** Stated in the verdict |
| Control mutation (spec 01 §5.3) | Required before pass | **Deferrable.** Creates an obligation |
| Coverage thresholds on the range | Required | **Deferrable.** Creates an obligation |
| Full security checklist | Every item | **Bounded** by §5. Unrun items are listed, not omitted |
| Scan subsystem | Required green before gate | **Deferrable** where the scanner cannot run on the hardware |
| Standing-state probes | Every gate | **Deferrable** |

**REQ-4.2** The two-window protocol MUST be retained.

**Rationale, and it is the one people expect to see degraded.** Isolation costs a separate session
and nothing else — no extra time, no extra hardware, no second person. It is the cheapest control in
the entire package and it defends against the failure most likely at 0300 with something broken: the
operator who has spent an hour constructing reasons the fix is correct, reviewing the fix. Keep it.

**REQ-4.3** Where separation of duties is not achieved, the verdict MUST say so in those words.

**Rationale.** Companion spec 04 REQ-5.3 already requires this of single-operator environments. It
is restated here because field mode is where it will be true most often and where the temptation to
leave it unsaid is strongest.

---

## 5. The time budget

**REQ-5.1** Field mode MUST accept a **stated time budget**, and the implementation MUST order
checks by value-per-second so the floor (§3) completes first.

**REQ-5.2** A check not run because the budget was exhausted MUST be recorded as **deferred**, by
name, with the reason *budget*.

**REQ-5.3** A deferred check MUST NOT be reported as passed, skipped, or not-applicable.

**Rationale.** These are four different states and the package already insists on distinguishing
three of them (companion spec 01 §1.2). *Deferred* is the fourth and it is the one field mode
creates: the check applies, it could have run, there was no time, and it is owed. Collapsing it into
*skipped* loses the obligation, which is the only thing that makes field mode honest.

**REQ-5.4** The implementation MUST report, at the end of a field run, the elapsed time and the list
of deferrals. A run that completes everything inside its budget MUST say so explicitly, because that
is the good case and it should be visible.

**REQ-5.5** The budget MUST NOT be enforced against the floor in §3. If the floor cannot complete,
the run has failed — it has not run out of time.

---

## 6. The field verdict

**REQ-6.1** A field run MUST produce a verdict of a **distinct class**, recording at minimum:

| Field | Content |
|---|---|
| Mode | `field` |
| Declared by / when / why | From §2.2 |
| Range | Commit identifiers, as always |
| Checks run | By name, with results |
| **Checks deferred** | By name, with reason |
| Separation of duties | Achieved / **not achieved** |
| Reviewer class and **model identity** | See §8 |
| Reconciliation status | Open, until §7 is satisfied |
| Time budget and elapsed | Both |

**REQ-6.2** The verdict MUST state its own boundary in prose, in one sentence a non-specialist can
read, at the top. Rationale: the row will be read by someone deciding whether to trust the change,
possibly at speed, possibly not an engineer.

**REQ-6.3** A field verdict MUST appear in the ordinary gate log (companion spec 02 §3), not in a
separate log.

**Rationale.** A separate log is a log nobody joins to the main series, and the field changes are
precisely the ones an assessor will want to find. One series, with a mode column.

**REQ-6.4** The started-marker requirement (companion spec 02 §3.5) applies unchanged. A field run
that begins and produces no row is the same defect here as anywhere, and more likely, because the
run may be interrupted by the thing that caused it.

---

## 7. Reconciliation — paying the debt

**REQ-7.1** Every field change MUST be re-gated in full when it reaches an environment where the
full process is possible.

**REQ-7.2** Until then it carries an **open reconciliation obligation**, which MUST be reported at
every subsequent gate, in any mode.

**REQ-7.3** The obligation MUST record what was deferred, so reconciliation can be verified as
complete rather than assumed.

**Rationale.** "Re-gate it later" without a list of what was skipped produces a later gate that runs
the normal suite and declares the debt paid, having never specifically confirmed the deferred items.
Naming them makes the discharge checkable.

**REQ-7.4** Reconciliation MUST produce its own gate-log row, referencing the field row it
discharges. Both rows remain.

**REQ-7.5** The count of open obligations MUST be reported at every gate and in every evidence
export.

**REQ-7.6** A configurable ceiling on open obligations MUST exist. Exceeding it MUST require an
explicit, recorded acceptance to enter field mode again.

**Rationale, and the tension is deliberate.** A hard block would be operationally wrong — the
situation that justifies field mode does not care how much debt is outstanding, and a tool that
refuses to help during an incident is a tool that gets bypassed permanently. But unbounded debt is
how a temporary posture becomes the permanent one. A ceiling that can be exceeded by a named person
who records why preserves both: the work is never blocked, and nobody drifts past the line without
noticing. This is the same shape as the carried-findings rule in companion spec 01 §4.10 — the
escalation is a forcing function, not a wall.

**REQ-7.7** Open obligations MUST age, and the age MUST be visible. An obligation older than a
configured threshold is a finding.

---

## 8. Hardware and model degradation

**REQ-8.1** The harness MUST operate with **no model at all**, running the mechanical checks and
producing a record.

**Rationale.** This is the floor of the floor. Field hardware may have no accelerator, no capacity
to spare, or a power budget that forbids inference. A harness that becomes useless without a model
is a harness that is useless exactly when the situation is worst. Mechanical checks plus an honest
record is a genuinely useful product on its own, and it must be a supported configuration rather
than a degraded accident.

**REQ-8.2** Where a model performs the review, the verdict MUST record **which model** — identifier
and parameter scale.

**Rationale, and this is the requirement most likely to be thought pedantic.** A small model and a
large model applying the same checklist do not produce equivalent review, and the difference is
invisible in the output: both produce fluent, plausible, structured findings. Without the model
recorded, a reader cannot tell a review performed by a capable reviewer from one performed by
something running on a laptop's integrated graphics, and the record implies they are the same. This
is companion spec 02 §10.5 — *say what the reviewer is* — applied one level deeper. Saying "an
automated reviewer" is no longer sufficient once the automated reviewers differ by an order of
magnitude in capability.

**REQ-8.3** The checklist MUST NOT be reduced to suit a smaller model.

**Rationale.** A smaller model given a shorter checklist produces a clean verdict against a
diminished standard, and nothing in the output says the standard moved. Keep the checklist fixed and
let the recorded model identity carry the information about how much weight the verdict bears.

**REQ-8.4** Where the model cannot complete the checklist within the budget, the unreached items are
**deferred** (§5.2), not dropped.

**REQ-8.5** Model weights are vendored data and MUST be version-pinned and transferred with
provenance, exactly as catalogues and detection data are (companion spec 04 §3.5, §4.2.2).

---

## 9. Non-requirements

- **No automatic entry into field mode.** REQ-2.1.
- **No field mode to escape a failing check.** REQ-2.3.
- **No reduced checklist.** REQ-8.3.
- **No separate log.** REQ-6.3.
- **No silent deferral.** REQ-5.2. A deferral that is not recorded did not happen — the work simply
  was not done.
- **No discharge of an obligation by the passage of time**, by a mode change, or by a later gate
  that did not specifically confirm the deferred items. REQ-7.3.
- **No degradation of the failure semantics or the record set.** REQ-3.2, REQ-3.3.

---

## 10. Build order

Field mode is mostly assembly. Almost every component exists for other reasons.

| Stage | Build | Note |
|---|---|---|
| 1 | The deferred state, distinct from passed / skipped / not-applicable | One state, and it is the whole idea |
| 2 | Mode declaration with reason, and the anti-inference rule (§2) | Cheap, and it is the erosion defense |
| 3 | The floor: ordering checks by value-per-second (§3, §5.1) | Needs the mechanical checks to exist |
| 4 | The field verdict class and its gate-log row (§6) | Needs the record set |
| 5 | Reconciliation obligations, with count and aging (§7) | The debt ledger; this is what makes it honest |
| 6 | Model identity in the verdict (§8.2) | Trivial, and it is the difference between a record and an implication |
| 7 | No-model operation (§8.1) | Should fall out of stages 1–4 if they were built without assuming a model |
| 8 | The obligation ceiling (§7.6) | Last; needs real usage to set a sensible number |

**A note on stage 1.** The temptation is to reuse *skipped*. It is one word and it is already there.
But *skipped* carries no obligation, and the obligation is the only thing separating a bounded gate
from a weaker one. If only one requirement from this document survives, it is that deferred is its
own state and it is owed.
