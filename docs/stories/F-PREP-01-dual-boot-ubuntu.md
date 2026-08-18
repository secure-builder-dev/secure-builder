# F-PREP-01 — Dual-boot Ubuntu LTS: build where the engine ships

## Header  *(Charter — PM lane)*
- **Story ID:** F-PREP-01
- **Epic:** EPIC-PREP — Make the gates real
- **Intent element(s):** IE-5 (the engine runs where it ships), IE-2 (falsifiable)
- **Type:** devsecops (environment)
- **Security-sensitive?** No — no application auth surface. *(Touches Secure Boot and disk
  layout, so it is operationally risky; that is a different axis from security-sensitive.)*
- **Routing:** Bastion → Crucible (verification only; no code gate)

## Mandatory Reads  *(per CLAUDE.md §3.2 — operator attests these were supplied)*
- [ ] `docs/architecture/MODEL-PROFILES.md` — the VRAM/context budgets this move affects
- [ ] `docs/architecture/ADR-LOG.md` ADR-0003 — model provenance and `COMPUTE_PROFILE`
- [ ] `CLAUDE.md` §5, §8 — init variables, OPSEC rules

## User Story
As the operator, I want the engine's development environment to be the same OS family it
is forward-deployed on, so that a gate verdict produced on my laptop is evidence about the
target and not about Windows.

## Why this is first
F-016 found three defects that exist **only** because development happens on Windows: a
`fnmatch` case-sensitivity split that gives the same commit different lane verdicts per OS,
a cp1252 crash that truncated every finding, and a Microsoft Store python shim that would
have blocked every commit. That is a defect *class*, not three accidents. Every story after
this one produces evidence; evidence produced on the wrong platform has to be re-earned.

## Acceptance Criteria  *(each AC maps by name to a verification step)*
- **AC-1 — Dual-boot exists.** Ubuntu LTS boots from its own partition (~1 TB), Windows
  still boots (~900 GB), and the bootloader offers both. *Verify:* boot each in turn.
- **AC-2 — Windows survives intact.** The Windows install boots to desktop and its data is
  present after the shrink. *Verify:* boot Windows, confirm the repo at `C:\dev\secure-builder`.
- **AC-3 — GPU is real.** `nvidia-smi` reports the RTX 5090 Laptop GPU with **24 GB** and a
  driver that supports Blackwell (the **open** module variant). *Verify:* `nvidia-smi` output.
- **AC-4 — Secure Boot resolved explicitly.** Either the MOK key is enrolled and the NVIDIA
  module loads, or Secure Boot is off **as a recorded decision**. Silent breakage is a FAIL.
  *Verify:* `mokutil --sb-state` plus `lsmod | grep nvidia`.
- **AC-5 — Gate scripts agree across platforms.** Every `scripts/gates/*.py` check produces
  an **identical verdict and exit code** on Linux and Windows for the same commit range.
  *Verify:* run the F-PREP-02 suite on both, diff the output. This is the AC that closes the
  `fnmatch` defect class.
- **AC-6 — Hooks work on Linux.** `sh scripts/install-hooks.sh` installs, and a commit with
  a malformed message is rejected. *Verify:* live attempt, as F-016 did on Windows.
- **AC-7 — VRAM headroom measured, not assumed.** Idle VRAM consumption is measured on
  Linux and the delta vs. Windows is recorded in `MODEL-PROFILES.md`'s supply-side table.
  *Verify:* the table row is filled with a measured number.
- **AC-8 — Fan/thermal control has an answer.** Sustained GPU load does not thermally
  throttle unmanaged. Either `Linuwu-Sense` (or equivalent) is installed, or the limitation
  is recorded. *Verify:* a sustained-load run with temperatures recorded.

## SHALL NOT constraints
- **SHALL NOT** proceed without a verified backup of anything on the Windows volume that is
  not already in git. Repartitioning is destructive.
- **SHALL NOT** treat a passing `nvidia-smi` as evidence the inference stack works — that is
  AC-5's job for gates and a later story's for models.
- **SHALL NOT** record AC-7 from a spec sheet or a model card. Measured on this hardware or
  it does not go in the table (`MODEL-PROFILES.md` rule).

## Endpoints touched
N/A — non-application story.

## Negative authorization tests planned
N/A — non-code story.

## Known risks to plan around  *(Bastion)*
- Windows will likely refuse to shrink `C:` anywhere near its free-space figure; unmovable
  files (pagefile, hibernation, shadow copies) cap it. Disable hibernation and the pagefile,
  shrink, re-enable — or resize from a GParted live USB.
- Blackwell requires the **open** NVIDIA kernel-module variant; the classic proprietary
  branch does not cover RTX 50-series.
- The PH18-73 has a **MUX switch** in BIOS — decide hybrid vs. discrete *before* install.
- `PredatorSense` has no Linux equivalent (see AC-8).
- The python paths in `.claude/settings.local.json` are Windows-specific and need Linux
  equivalents after the move.

## TDD Red-Phase Evidence
`N/A — non-code story.`

## Implementation note  *(Bastion)*
_TBD_

---

## Gate Results  *(written by the gates — append, do not overwrite)*

### Quality Gate — Crucible
```
QUALITY GATE VERDICT [ ]
```

### Security Gate — Sentinel
```
GATE VERDICT [ ] | SECURITY_TIER [IL4]
open findings: [ ]   blocking findings: [ ]
```

### Manual Security Review — human + AI assistant
- Verdict: [ ]

### Human Approval  *(hard stop — Guarantee #1)*
- **APPROVED by:** _pending_
