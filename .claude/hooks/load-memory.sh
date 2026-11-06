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

# Surface every project MOC so Claude knows where each lane stands
# (Bitcoin-vs-Banks research, GTA6-Content production, and any you add later).
MOCS="$ROOT/vault/MOCs"
if [ -d "$MOCS" ]; then
  for moc in "$MOCS"/*.md; do
    [ -f "$moc" ] || continue
    echo "----- PROJECT MOC: $(basename "$moc") -----"
    cat "$moc"
    echo
  done
fi

# Tell Claude which production engine is wired in, without reading any secrets.
if [ -f "$ROOT/.mcp.json" ] && grep -q '"everygen"' "$ROOT/.mcp.json"; then
  echo "----- PRODUCTION ENGINE -----"
  echo "Everygen MCP registered in .mcp.json (https://everygen.ai/api/mcp)."
  echo "If tools are missing, run /mcp and sign in. Skill: everygen-produce. Runbook: workflows/05-produce.md"
  echo
fi

echo "=== END MEMORY LAYER ==="
