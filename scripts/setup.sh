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

# 1. Python deps (installs notebooklm-py[browser] → the `notebooklm` CLI + Playwright)
echo
echo "1/4 · Installing Python dependencies…"
python3 -m pip install -r requirements.txt

# 2. Browser engine for the login step (NotebookLM auth automates a real browser)
echo
echo "2/4 · Installing the Chromium browser engine for login…"
python3 -m playwright install chromium

# 3. NotebookLM login (interactive — opens a browser)
echo
if python3 integrations/notebooklm_bridge.py doctor >/dev/null 2>&1; then
  echo "3/4 · Already authenticated with NotebookLM — skipping login."
else
  echo "3/4 · Logging in to NotebookLM (a browser window will open)…"
  notebooklm login
fi

# 4. Verify the whole install
echo
echo "4/4 · Verifying…"
python3 integrations/notebooklm_bridge.py doctor

echo
echo "Next: open the ./vault folder in Obsidian, start Claude Code in this repo,"
echo "and try:  \"Make an audio overview + mindmap + flashcards + infographic from <url>\""
