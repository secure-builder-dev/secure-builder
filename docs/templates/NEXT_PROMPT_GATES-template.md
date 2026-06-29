# NEXT_PROMPT_GATES-template.md — Intra-story build→gate handoff (gate context entry)

> **Stream:** `_bmad-output/NEXT_PROMPT_GATES.md` — written by the **build context (CW1)**
> at the end of implementation, to hand a single story's diff to the **gate context
> (CW2)**. **Source of record:** `SECURE_BUILDER_PRD.md` §4 (CW2), §4.2, §4.3.
> **Operationalized by:** `CLAUDE.md` §3 (CW2), §3.2, §3.3.
>
> **This is not the inter-story handoff.** `NEXT_PROMPT.md` / `NEXT_PROMPT_FRAMEWORK.md`
> carry a *completed* story to the *next* story's session. This file carries *one story
> mid-lifecycle* from its build context to its gate context, and is overwritten each
> story.
>
> **The whole point is the bias firewall (§4).** The gate context starts **cold** and
> sees only what is below — the story, the acceptance criteria, and the diff to scan. Do
> **not** paste the builder's reasoning, justifications, or self-assessment into this
> handoff; that is exactly the contamination the two-context split exists to prevent. A
> fresh set of eyes scans the artifact, not the author's argument for it.
>
> Clean-room / OPSEC applies: generic placeholders only; never write real infrastructure
> values or app secrets into a handoff (`CLAUDE.md` §8).

---

```markdown
# GATE CONTEXT — <app name> / <story id> (build→gate handoff)

> You are the **gate context (CW2)** for this story. You did not build this code and you
> have no access to the builder's reasoning — by design. Scan the artifact below on its
> own terms. Run Murat (quality), then Sentinel (security). Kick FAILs back with concrete
> findings. Do not approve anything — approval is a human act (Guarantee #1).

## 0. Sentinel skill-load — DO THIS FIRST, before judging any code (§3.2)
Open and read each skill file below, and echo a one-line attestation of each (what you
loaded) before any verdict. A gate run that skips this is **invalid** and re-runs. Do not
improvise or recall these from memory — read them.
- [ ] Quality-gate checks (Murat cluster) — `<path>`
- [ ] Security-gate checklist (Sentinel) — `<path>`
- [ ] Control lookup against `docs/security/controls/CONTROLS-MAPPING.md` — `<path>`
- [ ] Dependency policy — `docs/architecture/DEPENDENCY_POLICY.md`
- [ ] **Adversarial testing** — `<path>`

## 1. Init variables
APP_TRACK=<> · SECURITY_TIER=<> · PROVIDER=<> · APP_TYPE=<> · GATE_ENFORCEMENT=<>

## 2. Story under gate
- Story id / title: <>
- Story file: <path>
- Acceptance criteria (verbatim, for ATDD mapping): <list, or pointer to the story file>
- Security-sensitive surface? (auth / RBAC / new endpoints / data-boundary) <yes/no — which>

## 3. The diff to scan (the ONLY thing you judge)
- Commit range: `<test-only sha>..<impl sha>` (+ any remediation shas)
- Touched files: <list>
- How to view: `git diff <range>` / `git show <sha>`
- Endpoints/resources introduced or changed (for negative-test + IDOR review): <list>

## 4. What to produce
- **Murat:** `QUALITY GATE VERDICT [PASS/FAIL]` per §4.2 format (TDD two-commit present in
  `git log`; per-layer coverage on the diff; negative tests 401/403/IDOR/400/conflict;
  ATDD [x/x ACs]; CI stage; flaky check). FAIL → findings back to the builder, re-scan.
- **Sentinel:** `GATE VERDICT [PASS/FAIL] | SECURITY_TIER [IL4/IL6]` per §4.3; every check
  traces to a control ID in `CONTROLS-MAPPING.md`. FAIL → findings back to the builder,
  re-scan. Write verdict + finding rows **live** to `_bmad-output/gate-log.md` (you own
  it, §7.2).
- **Self-healing loop is capped at 3 rounds.** If gates still FAIL after the third round,
  **stop and escalate to the human** — do not auto-remediate indefinitely (§3).

## 5. Hard stops (do NOT cross without a human)
- After gates PASS: the **manual security review (§4.4)** is a human gate — present the
  concrete endpoints/resources and the §4.4 questions; do not self-clear.
- **Human approval (§3 step 7)** is the only thing that unlocks promotion. On "approved":
  append the gate-log DONE row (Sentinel), then Bob writes the next story's `NEXT_PROMPT.md`.
```

---

## Notes
- Keep §3 (the diff) precise and §0 (skill-load) non-negotiable — those two are what make
  this an *independent* gate rather than a rubber stamp.
- Never include the builder's rationale. If a reviewer needs to know "why," they read the
  story's acceptance criteria and the code — not the builder's defense of it.
- This handoff is **intra-story**; it does not replace the inter-story `NEXT_PROMPT*`
  streams, which are written only after this story has cleared all gates and the human
  approved.
