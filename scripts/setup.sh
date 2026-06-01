#!/usr/bin/env bash
# Research Monster — one-command finisher.
# Run this once on your own machine (it needs a browser for the login step).
#
#   bash scripts/setup.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "🧠 Research Monster setup"
echo "========================="

# 1. Python deps (installs notebooklm-py → the `notebooklm` CLI)
echo
echo "1/3 · Installing Python dependencies…"
python3 -m pip install -r requirements.txt

# 2. NotebookLM login (interactive — opens a browser)
echo
if python3 integrations/notebooklm_bridge.py doctor >/dev/null 2>&1; then
  echo "2/3 · Already authenticated with NotebookLM — skipping login."
else
  echo "2/3 · Logging in to NotebookLM (a browser window will open)…"
  notebooklm login
fi

# 3. Verify the whole install
echo
echo "3/3 · Verifying…"
python3 integrations/notebooklm_bridge.py doctor

echo
echo "Next: open the ./vault folder in Obsidian, start Claude Code in this repo,"
echo "and try:  \"Make an audio overview + mindmap + flashcards + infographic from <url>\""
