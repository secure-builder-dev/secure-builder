#!/bin/sh
# install-hooks.sh — install the local-attested git hooks (no framework required).
#
# Copies scripts/hooks/* into .git/hooks and makes them executable. Use this on targets
# where the pre-commit framework is unavailable (e.g. air-gapped). Where the framework
# IS available, `pre-commit install` + .pre-commit-config.yaml is the alternative — both
# call the SAME scripts/gates/*.py, so behavior is identical either way.

set -e
ROOT="$(git rev-parse --show-toplevel)"
HOOKS_SRC="$ROOT/scripts/hooks"
HOOKS_DST="$ROOT/.git/hooks"

for hook in pre-commit commit-msg; do
  cp "$HOOKS_SRC/$hook" "$HOOKS_DST/$hook"
  chmod +x "$HOOKS_DST/$hook"
  echo "installed: .git/hooks/$hook"
done
echo "done. Hooks run in local-attested mode (CLAUDE.md §6). Bypass with --no-verify is"
echo "visible in the gate log + git history by design — not a silent skip."
