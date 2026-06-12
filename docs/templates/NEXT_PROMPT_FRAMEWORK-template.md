# NEXT_PROMPT_FRAMEWORK-template.md — Framework-stream handoff template (F-prefix)

> **Stream:** `_bmad-output/NEXT_PROMPT_FRAMEWORK.md` — written after each **F-prefix
> (framework)** commit. **Source of record:** `SECURE_BUILDER_PRD.md` §4.3.
> **Operationalized by:** `CLAUDE.md` §3.3.
>
> **F-prefix = building the engine itself** (this constitution, the gate docs, the agent
> skills, the enforcement hooks) — as opposed to S-prefix, which builds an *app* with the
> engine. Secure Builder's own development uses this stream. (In this engine repo the live
> handoff is currently kept at the repo root as `NEXT_PROMPT.md` for convenience; the
> structure is identical.)
>
> A fresh session has **no memory** of the current one — keep this **fully
> self-contained.** Clean-room rule applies: build from `SECURE_BUILDER_PRD.md` and the
> owner's descriptions only; never paste work artifacts (`CLAUDE.md` §8.1).

---

```markdown
# NEXT PROMPT — Secure Builder (session handoff)

> Paste this to the agent at the start of the next session. Self-contained: the next
> session has no memory of the last one. (Memory files under the project memory dir also
> carry this context.)

## Where we are
<The clean-room rebuild status: which week of SECURE_BUILDER_BUILD_PLAN.md, what's been
built, what the engine is for. Restate the hard rule (clean-room / OPSEC) and the end
state (Track B own-orchestration + Track C local models, both out of the 4-week window).>

## What we did last session
<Bullet list: the engine artifacts drafted/changed, their commit hashes (F-XXX), and what
each encodes. End with: committed as F-XXX, no AI co-author trailer.>

## Decisions locked (don't relitigate)
<Bullet list of engine-design decisions made that a fresh session should not reopen.>

## What's next (pick up here)
<The next build-plan item(s), with the PRD section(s) to encode and any honesty nuance to
preserve (e.g., mark today-binding vs Phase-2; human-attested vs verified).>

## Key files
- CLAUDE.md — engine constitution (governing law + auto-loaded).
- SECURE_BUILDER_PRD.md — the spec / build contract — LOCKED.
- SECURE_BUILDER_BUILD_PLAN.md — 4-week build plan.
<plus the specific docs in play this session.>
```

---

## Notes
- Every framework commit is **F-prefix** and carries **no AI co-author / attribution
  trailer** (`CLAUDE.md` §7.1) — restate this in the handoff so a fresh session doesn't
  reintroduce a trailer.
- Always name the **PRD section** the next piece encodes, so the next session works from
  the spec rather than re-deriving it.
- Preserve the **honesty framing** explicitly in the "what's next" note — the now-vs-Phase-2
  and attested-vs-verified distinctions are easy to lose across a cold handoff.
