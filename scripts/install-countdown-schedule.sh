#!/usr/bin/env bash
# install-countdown-schedule.sh — run scripts/run-countdown.sh every day on THIS machine.
#
# macOS: installs a launchd agent (~/Library/LaunchAgents/ai.everygen.gta6-countdown.plist).
# Linux: adds a crontab line. Both fire at 09:15 local time. The runner itself exits
# cleanly after launch day (2026-11-19), so the schedule is harmless afterwards;
# remove it with:  scripts/install-countdown-schedule.sh --uninstall
#
# Do the ONE-TIME Everygen sign-in first (see scripts/run-countdown.sh header), and run
#   scripts/run-countdown.sh --dry-run
# once to confirm the preflight passes.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNNER="$ROOT/scripts/run-countdown.sh"
LABEL="ai.everygen.gta6-countdown"
HOUR=9; MIN=15
MODE="${1:-install}"

if [ "$(uname -s)" = "Darwin" ]; then
  PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
  if [ "$MODE" = "--uninstall" ]; then
    launchctl unload "$PLIST" 2>/dev/null || true; rm -f "$PLIST"; echo "removed $PLIST"; exit 0
  fi
  mkdir -p "$HOME/Library/LaunchAgents"
  cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>$RUNNER</string></array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>$HOUR</integer><key>Minute</key><integer>$MIN</integer></dict>
  <key>StandardOutPath</key><string>$ROOT/vault/40-outputs/gta6/logs/launchd.out.log</string>
  <key>StandardErrorPath</key><string>$ROOT/vault/40-outputs/gta6/logs/launchd.err.log</string>
  <key>EnvironmentVariables</key><dict><key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin</string></dict>
</dict></plist>
PL
  mkdir -p "$ROOT/vault/40-outputs/gta6/logs"
  launchctl unload "$PLIST" 2>/dev/null || true
  launchctl load "$PLIST"
  echo "installed launchd agent $LABEL → daily at $HOUR:$(printf %02d $MIN). Logs: vault/40-outputs/gta6/logs/"
else
  LINE="$MIN $HOUR * * * cd $ROOT && /bin/bash $RUNNER >> $ROOT/vault/40-outputs/gta6/logs/cron.log 2>&1  # $LABEL"
  CURRENT="$(crontab -l 2>/dev/null | grep -v "$LABEL" || true)"
  if [ "$MODE" = "--uninstall" ]; then
    printf '%s\n' "$CURRENT" | crontab -; echo "removed crontab entry $LABEL"; exit 0
  fi
  mkdir -p "$ROOT/vault/40-outputs/gta6/logs"
  printf '%s\n%s\n' "$CURRENT" "$LINE" | sed '/^$/d' | crontab -
  echo "installed crontab entry $LABEL → daily at $HOUR:$(printf %02d $MIN). Logs: vault/40-outputs/gta6/logs/cron.log"
fi
