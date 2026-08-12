# scripts/ — Enforcement mechanics (the machine-checkable guarantees)

> **Source of record:** `SECURE_BUILDER_PRD.md` §2 (Guarantees #3, #5, #7), §3.2, §9.
> **Operationalized by:** `CLAUDE.md` §0, §2.2, §4.1, §6, §8. **Track:** F-prefix
> (engine self-development).

These scripts implement the **`local-attested`** half of the gate chain
(`GATE_ENFORCEMENT=local-attested`, PRD §9): a pre-commit/commit-msg backstop plus
gate-time checks. They are **defense-in-depth, not an unbypassable wall** — `--no-verify`
exists, and that is acceptable in this mode *because* the append-only gate log and git
history make any skip visible and attributable, and the downstream platform team re-runs
its own checks (Guarantee #2, PRD §13). Where a real Git remote + CI exists, the
`ci-enforced` server-side merge wall is the stronger enforcement; wire it there too.

**Design choices:** stdlib-only Python (no `pip install`, air-gap friendly) for the check
logic; a thin `sh` dispatcher for the hooks; a JSON manifest as data. Works with or
without the `pre-commit` framework — both paths call the same `gates/*.py`.

## What's enforced today vs. Phase 2 (honest split)

| Check | Script | Dimension it covers | Not covered (still human/Phase-2) |
|---|---|---|---|
| Secret / forbidden-file scan | `gates/secret_scan.py` | Guarantee #7 backstop — pattern match on staged content | Structural separation (the *primary* control); novel secret formats |
| Commit-message prefix | `gates/check_tdd.py --staged-msg` | naming convention for S/F commits | — |
| TDD two-commit ordering | `gates/check_tdd.py --story S-XXX` | Guarantee #3 — tests commit precedes impl commit | that red tests truly failed; trivially-neutered tests |
| Lane boundary | `gates/check_lanes.py --agent X` | Guarantee #5 — file-ownership (diff vs globs) | semantic over-reach inside an allowed file |

The automated gate **agents** (Crucible, Sentinel) that orchestrate these are Phase-2 builds
(PRD §3.1). Today the operator runs these scripts and the checklists by hand; the scripts
make the mechanical parts repeatable, not the judgment.

## Layout

```
agents/manifest.json        # §3 agent table as data: lanes, owned_globs, mandatory_reads
scripts/
  gates/
    secret_scan.py          # pre-commit: forbidden files + probable secrets
    check_tdd.py            # commit-msg prefix; gate-time two-commit ordering
    check_lanes.py          # gate-time: touched files vs an agent's owned globs
  hooks/
    pre-commit              # sh dispatcher → secret_scan (+ app lint/typecheck/test if present)
    commit-msg              # sh dispatcher → check_tdd --staged-msg
  vendor/                   # corpus vendoring converters (Node .mjs — see below)
    oscal-catalog-to-md.mjs   # NIST OSCAL catalog JSON  → 800-53r5 family files + index
    oscal-baselines-to-md.mjs # NIST OSCAL profiles      → 53B IL4/IL6 baselines + delta
    xccdf-stig-to-md.mjs      # DISA XCCDF benchmark XML → STIG/SRG rule files
    owasp-fetch.mjs           # official OWASP repos     → Top 10 / ASVS / LLM / MASVS
  install-hooks.sh          # copy hooks into .git/hooks (framework-free path)
.pre-commit-config.yaml     # framework path: repo:local hooks calling the same scripts
```

## `vendor/` — corpus generation (a different job from the gates)

The `gates/` scripts enforce guarantees at commit/gate time. The `vendor/` scripts do
something else: they generate `docs/security/corpus/` — the **verbatim** authoritative
source text Sentinel's citations resolve into (Guarantee #4, ADR-0002). They are **Node
`.mjs`** — written that way in F-010 when this box had no working Python (it does now:
CPython 3.12.13 via `uv`, shims in `~/.local/bin`). They stay Node because they work and
are proven against real sources; new converters may be either, but keep them
**dependency-free** — Track C is air-gapped. They run offline once the source file is
local, so a corpus refresh is repeatable rather than a one-time manual conversion.

**The rule they encode: no fabrication.** Every character of control text comes from the
official source file. A source that cannot be obtained is marked `SOURCE-NEEDED` in
`corpus/MANIFEST.md` — never filled from memory. Currency and per-source status live in
that manifest; the full procedure is `corpus/VENDORING_PROMPT.md`.

```sh
# each script prints its own usage when called with no arguments
node scripts/vendor/oscal-catalog-to-md.mjs   <catalog.json> <out-controls-dir> [retrieved]
node scripts/vendor/oscal-baselines-to-md.mjs <catalog> <moderate> <high> <out-53b-dir> <crosswalk-dir> [retrieved]
node scripts/vendor/xccdf-stig-to-md.mjs      <benchmark.xml> <out.md> "<Doc Title>" "<Prov doc id>" [retrieved]
node scripts/vendor/owasp-fetch.mjs           <corpus-owasp-dir> [retrieved]   # network path
```

## Install (pick one)

**Framework-free (air-gap safe):**
```sh
sh scripts/install-hooks.sh
```

**With the pre-commit framework:**
```sh
pre-commit install
pre-commit install --hook-type commit-msg
```

## Gate-time checks (run by the operator / future Sentinel, not on every commit)

```sh
# TDD two-commit ordering for a story:
python scripts/gates/check_tdd.py --story S-001 --range main..HEAD

# Lane boundary for the agent that did the work:
python scripts/gates/check_lanes.py --agent Forge --range main..HEAD

# List known agents and their lanes:
python scripts/gates/check_lanes.py --list-agents
```

All scripts exit `0` on pass, `1` on a finding, `2` on a usage error — usable directly in
CI for the `ci-enforced` path.
