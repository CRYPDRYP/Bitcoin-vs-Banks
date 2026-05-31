#!/usr/bin/env bash
# SessionStart hook: prints the Obsidian "memory layer" so Claude Code begins
# every session already knowing the user's profile, interests, and style.
#
# Output on stdout is injected into the session as context.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MEM="$ROOT/vault/_memory"

echo "=== RESEARCH MONSTER: MEMORY LAYER ==="
echo "(loaded automatically at session start from vault/_memory/)"
echo

if [ -d "$MEM" ]; then
  for f in profile.md interests.md style-guide.md; do
    if [ -f "$MEM/$f" ]; then
      echo "----- $f -----"
      cat "$MEM/$f"
      echo
    fi
  done
else
  echo "(no memory layer found yet — run the 'learn' skill after your first session)"
fi

# Surface the active project's top-level MOC so Claude knows where things stand.
ACTIVE_MOC="$ROOT/vault/MOCs/Bitcoin-vs-Banks.md"
if [ -f "$ACTIVE_MOC" ]; then
  echo "----- ACTIVE PROJECT MOC: Bitcoin-vs-Banks.md -----"
  cat "$ACTIVE_MOC"
  echo
fi

echo "=== END MEMORY LAYER ==="
