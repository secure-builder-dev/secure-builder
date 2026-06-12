# NEXT_PROMPT-template.md — Story-stream handoff template (S-prefix)

> **Stream:** `_bmad-output/NEXT_PROMPT.md` — written by Bob after each **S-prefix
> (story)** commit. **Source of record:** `SECURE_BUILDER_PRD.md` §4.3.
> **Operationalized by:** `CLAUDE.md` §3.3.
>
> A fresh session has **no memory** of the current one. This handoff must be **fully
> self-contained** — someone (or some session) starting cold can pick up from it alone.
> Copy this skeleton, fill every section, and overwrite the live `NEXT_PROMPT.md`. Use
> generic placeholders only; never write real infrastructure values or app secrets into a
> handoff (`CLAUDE.md` §8).

---

```markdown
# NEXT PROMPT — <app name> (session handoff)

> Paste this to the agent at the start of the next session. Self-contained: the next
> session has no memory of the last one.

## Where we are
<1 short paragraph: what app, which track/tier/provider, what phase of the §4 lifecycle
we're in, and the current sprint goal.>

- Init variables: APP_TRACK=<> · SECURITY_TIER=<> · PROVIDER=<> · APP_TYPE=<> ·
  GATE_ENFORCEMENT=<>

## What we did last session
<Bullet list. The story(ies) completed, their gate verdicts, the commit hashes, and any
finding opened/closed. End with: committed as S-XXX, gate log updated.>

## Decisions locked (don't relitigate)
<Bullet list of decisions made that a fresh session should not reopen.>

## Open findings carried forward
<Any ACCEPTED / non-blocking findings with their Issue IDs (GL-YYYY-MM-DD-###) and the
follow-up owner. "None" if clean.>

## What's next (pick up here)
<The next story to dispatch and its routing (first agent → then, per §3.1). The mandatory
reads for that agent. Any setup the next session needs before starting.>

## Key files
<The story file, the contracts/specs the next agent must read, and the governance docs in
play.>
```

---

## Notes
- The **gate verdicts and commit hashes** are the load-bearing content — a fresh session
  reconstructs trust in prior work from them, not from prose.
- If a story is mid-lifecycle (e.g., failed a gate and is being remediated), say **exactly
  which step** it's on and what FAIL/findings remain.
- Keep it to what the next session needs to act — this is an operational handoff, not a
  status report.
