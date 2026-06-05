# Secure Builder PRD — Manual Fill-In Worklist

Work top to bottom. Each item tells you the PRD section, what to decide or write,
and why it matters. Check items off as you go. Items marked **[DECISION]** need a
judgment call, not just text — those are the ones to think hardest about.
Items marked **[QUICK]** are fast factual fills.

When you've worked through these, send me the draft and we'll pressure-test §2.

---

## Do these first (they unblock the rest)

- [ ] **[QUICK] Cover block** — your name, today's date. (Header)

- [ ] **[DECISION] §6.1 + §13 — Operating mode.** Are you single-operator or team?
  This single answer changes how honest §6 and §13 read. If single-operator: write
  it plainly and note what compensates (e.g., "platform team review is the real
  separation of duties; this engine is pre-flight only"). This is the most
  important decision in the whole document — everything about the human gate's
  credibility flows from it.

- [ ] **[DECISION] §2 — Core Guarantees.** Read all 7. For each, ask: "is this a
  promise I'm actually willing to make about *everything* the engine outputs, and
  can I point at the machinery that enforces it?" Cut any you can't back. Add any
  real promise that's missing. Reword in your own voice. This list is your IP —
  don't ship my wording unexamined.

---

## Honesty / risk items (don't skip — these protect you)

- [ ] **[DECISION] §4.2 + §4.4 + §13 — Mandatory-read verification.** Decide how (or
  whether) you can verify an agent *read* a file vs. it merely being in context. If
  you can't verify it: change the language from "verified" to "human-attested" and
  leave the §13 risk in. Don't let the doc claim a check it can't enforce.

- [ ] **[FILL] §6.4 — What "approved" actually evidences.** One or two sentences
  stating plainly what your human approval means in your context, so a platform
  team or assessor can't over-read it. (e.g., "one developer's structured
  self-check per §6.2, not senior security sign-off.")

- [ ] **[REVIEW] §13 — Risks.** Read all six. Confirm each is stated in a way you'd
  be comfortable showing a platform team. Add any risk specific to your environment.

---

## Factual confirmations against your existing docs

- [ ] **[QUICK] §3 — Agent manifest.** Confirm names/lanes/owned-artifacts match
  your current build. Fill the Tech Writer's owned artifacts (the screenshots left
  it blank). Add any agent not listed (you referenced `bmad-testarch-*` as "Murat's
  7 test-architecture skills" — decide if that's one agent or a skill cluster and
  represent it correctly).

- [ ] **[QUICK] §3 table — Frank & Sentinel artifacts.** I compressed these slightly.
  Cross-check against your source and expand if I dropped anything.

- [ ] **[DECISION] §4 / §6 — "human" vs "Casey".** I genericized "Casey" to "human"
  since Casey = end user. Confirm you want it generic (better for an ownable tool)
  or want to keep a named role. Be consistent throughout if you change it.

- [ ] **[QUICK] §9 — Init variables.** Confirm values, defaults, and the decision-tree
  logic match your clone-time setup exactly.

- [ ] **[QUICK] §5.2 — Coverage thresholds.** Confirm the four numbers (80/80/70/80)
  are current.

- [ ] **[QUICK] §5.6 — Dependency severity matrix + license policy.** Confirm
  timelines and the approved/prohibited license lists are current. Note: this maps
  directly to your "drop the CVE/POA&M process" value prop, so get it exactly right.

---

## Environment-specific / sensitivity calls

- [ ] **[DECISION] §12.4 — Inheritance source name.** Your source names a specific
  platform ATO. Decide: keep the real name (internal version) or genericize to
  "platform ATO" (ownable/standalone version). Consider maintaining two builds — an
  internal one and a sanitized public one — and note which this file is.

- [ ] **[DECISION] §12.2 — ADR-023 / ADR-026 references.** These point at ADRs that
  live in your project, not the engine. Decide whether the standalone PRD should
  reference them or state the ceiling logic self-containedly.

- [ ] **[DECISION] Perimeter-network specifics.** You mentioned a network you can't
  talk about. Scrub anything in §12 that's more specific than the public DoD
  standards warrant. When in doubt, generalize. **If you're ever unsure whether a
  detail is releasable, leave it out of any version of this file you'd put on
  personal hardware or share — that's the safe default.**

- [ ] **[DECISION] §8.2 — GitHub Copilot incident narrative (2026-04-29).** Your ADR
  log references a real incident as an example. Decide: (a) preserve the *lesson*
  abstracted into §11's rationale, (b) keep it as a project-history example, or
  (c) omit from the engine PRD entirely. If the §11 sensitive-value rules exist
  *because* of that incident, capturing the abstracted lesson is worth it.

---

## Completeness fills

- [ ] **[FILL] §7 — Agent-builder templates.** Confirm all 9 templates and their
  purposes match your `assets/` folder. Add any I missed.

- [ ] **[FILL] §10 — Orchestration "what I'd have to rebuild" list.** This is the
  most valuable thing you can add for your own future. Every time you notice the
  current framework doing something for you, write it here. Build this list
  continuously over the next few sprints, not in one sitting.

- [ ] **[FILL] Appendix A — Glossary.** Spell out every acronym. Tedious but it's
  what lets a new teammate or an assessor read the doc cold. Do this last.

---

## Stretch / later (not blocking a v1 draft)

- [ ] **[LATER] §8.4 — Document reference.** Confirm every file path exists or is
  planned. Flag any that are aspirational vs. real.

- [ ] **[LATER] §5.4 — Control mappings.** The example control IDs I pulled from your
  screenshots should be spot-checked against the actual 800-53 Rev 5 text as you
  build the real `CONTROLS-MAPPING.md`. Don't trust any mapping (mine or the
  engine's) without confirming against the controlling text — that's Guarantee #4
  applied to your own document.

---

## Suggested order for tomorrow

1. Cover block + operating mode (§6.1/§13) — 15 min, unblocks the tone of everything.
2. Core Guarantees (§2) — the real thinking work, do it while fresh.
3. The three honesty items (mandatory-read, approval-evidences, risks).
4. Factual confirmations — fast, mechanical, good for when energy dips.
5. Sensitivity calls — do these deliberately, not tired.
6. Completeness fills + glossary — last, low-stakes.

Don't try to finish in one session. Items 1–3 are a complete, valuable first sitting.
