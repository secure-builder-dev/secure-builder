# The build's governance set

© 2026 Casey Houle. All rights reserved.

Spec 07 §5.1. These files are human-owned for the duration of the build. The
loop may not edit them. A commit touching any of them requires an explicit
human approval (`ENGINE_GOVERNANCE_OK=1` at commit time) and is logged.

    rules/v1.0.md                  the exit condition
    work/tools/progress.py         the thing that evaluates it
    work/tools/progress_test.py    its negative fixtures
    work/hooks/                    pre-commit and stop hooks
    rules/prompts/iteration.md     the loop's instructions
    rules/specs/                   the requirements themselves
    rules/GOVERNANCE-SET.md        this list
    rules/AMENDMENTS.md            decisions about the specs

As the harness grows its own governance artifacts (spec 01 §11 — instruction
files, reviewer definitions, anything altering gate behavior), they are added
here.
