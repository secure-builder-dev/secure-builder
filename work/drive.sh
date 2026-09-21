#!/bin/sh
# © 2026 Casey Houle. All rights reserved.
# drive.sh — outer loop (spec 07 §5.2). Survives crashes and context exhaustion.
# Stall guard keys on the DONE COUNT, never on HEAD. Budget guard reads budget.txt.
set -u
cd "$(dirname "$0")" || exit 1
i=0
while [ "$i" -lt 500 ]; do
    i=$((i + 1))
    python work/tools/progress.py --quiet && { echo "v1.0 reached at iteration $i"; break; }

    # ENGINE_ASSISTANT_CMD is the operator's assistant CLI invocation, e.g.
    # '<cli> -p --permission-mode acceptEdits'. It is set in the environment,
    # never in this repository. The iteration prompt is appended as the last argument.
    ${ENGINE_ASSISTANT_CMD:?set ENGINE_ASSISTANT_CMD to the assistant CLI invocation} "$(cat prompts/iteration.md)"
    rc=$?

    git rev-parse HEAD >> .journal/heads
    [ "$rc" -eq 0 ] || echo "iteration $i exited $rc" >> .journal/errors

    python work/tools/progress.py --count-done >> .journal/done-counts
    if [ "$(wc -l < .journal/done-counts | tr -d ' ')" -ge 3 ] && \
       [ "$(tail -3 .journal/done-counts | sort -u | wc -l | tr -d ' ')" = "1" ]; then
        echo "STALLED after iteration $i — see .journal/errors"; break
    fi

    python work/tools/progress.py --spend-check || { echo "BUDGET reached at iteration $i"; break; }
done
