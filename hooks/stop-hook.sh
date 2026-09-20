#!/bin/sh
# © 2026 Casey Houle. All rights reserved.
# Inner-loop Stop hook (spec 07 §5.1). Exit 0 allows the session to stop.
# Exit 2 blocks it and the message on stderr is injected as the next instruction.
# NOT installed by this repository — see hooks/README.md.
cd "$(git rev-parse --show-toplevel)" || exit 0
python tools/progress.py --quiet >/dev/null 2>&1 && exit 0

# stall detector: three consecutive stop-blocks with no change in the done count
python tools/progress.py --count-done >> .journal/stop-done-counts
if [ "$(wc -l < .journal/stop-done-counts | tr -d ' ')" -ge 3 ] && \
   [ "$(tail -3 .journal/stop-done-counts | sort -u | wc -l | tr -d ' ')" = "1" ]; then
    echo "BLOCKED: done count unchanged across three stop attempts" >> .build-log.md
    exit 0
fi

todo=$(awk -F'\t' 'NR>1 && $4=="todo"' ledger.tsv | wc -l | tr -d ' ')
doing=$(awk -F'\t' 'NR>1 && $4=="doing"' ledger.tsv | wc -l | tr -d ' ')
echo "Ledger shows $todo todo, $doing doing. Continue with the lowest-ordered actionable requirement." >&2
exit 2
