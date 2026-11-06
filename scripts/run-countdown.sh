#!/usr/bin/env bash
# run-countdown.sh — run today's GTA 6 countdown brief through Everygen, hands-off.
#
# Drives Claude Code headlessly (`claude -p`) with the everygen-produce skill. Requires a
# ONE-TIME interactive setup on this machine:
#   claude            # in this repo: approve the `everygen` project MCP server
#   /mcp              # pick everygen → sign in (OAuth in your browser)
# After that this script needs no input. Everygen credits are spent on each run.
#
# Usage:
#   scripts/run-countdown.sh                 # today's brief
#   scripts/run-countdown.sh --date 2026-11-10
#   scripts/run-countdown.sh --dry-run       # show the brief + prompt, call nothing
#   CREDIT_CAP=60 scripts/run-countdown.sh   # refuse to spend more than 60 credits (default 60)
#   MAX_TURNS=40 scripts/run-countdown.sh    # cap agent turns (default 40)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DATE="$(date +%Y-%m-%d)"
DRY_RUN=0
while [ $# -gt 0 ]; do
  case "$1" in
    --date) DATE="$2"; shift 2 ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
CREDIT_CAP="${CREDIT_CAP:-60}"
MAX_TURNS="${MAX_TURNS:-40}"
LAUNCH="2026-11-19"

# --- 1. make sure the brief for DATE exists (idempotent) --------------------------------
python3 integrations/countdown_briefs.py --from "$DATE" --to "$DATE" >/dev/null || true
STAMP="${DATE//-/}"
BRIEF="$(ls vault/40-outputs/gta6/${STAMP}-d*-countdown-brief.md 2>/dev/null | head -1 || true)"
if [ -z "$BRIEF" ]; then
  if [[ "$DATE" > "$LAUNCH" ]]; then
    echo "Launch has passed ($LAUNCH); no countdown brief for $DATE. Nothing to do."; exit 0
  fi
  echo "No brief found for $DATE in vault/40-outputs/gta6/." >&2; exit 1
fi
BRIEF_STEM="$(basename "$BRIEF" .md)"
LOGDIR="vault/40-outputs/gta6/logs"; mkdir -p "$LOGDIR"
LOG="$LOGDIR/${STAMP}-run.log"

# --- 2. preflight: claude present, everygen server approved & signed in -----------------
if ! command -v claude >/dev/null 2>&1; then
  echo "claude (Claude Code CLI) is not on PATH. Install it, then run the one-time setup in the header." >&2; exit 1
fi
MCP_STATUS="$(claude mcp get everygen 2>&1 || true)"
if echo "$MCP_STATUS" | grep -qiE "pending approval|needs authentication|not found|No MCP server"; then
  echo "Everygen MCP is not ready in this repo:" >&2
  echo "$MCP_STATUS" | sed 's/^/  /' >&2
  echo "One-time fix: run 'claude' here, approve the everygen server, then '/mcp' → everygen → sign in." >&2
  exit 1
fi

# --- 3. the headless instruction -------------------------------------------------------
read -r -d '' PROMPT <<PROMPT_EOF || true
Use the everygen-produce skill. Run the brief at ${BRIEF} end to end WITHOUT pausing for approval, under these rules:
1. First call the Everygen read tool to get the credit balance. If the balance is below the brief's credit_budget, or the run would exceed ${CREDIT_CAP} credits in total, write a short note under "## Results" in the brief explaining that, and stop without generating anything.
2. Follow the shot list exactly as written: the model, resolution and length per row, and the exact visual prompt text. For days that say "reuse approved final from [[20261106-d13-countdown-brief]]", do not render a new scene; find the final video card in vault/40-outputs/gta6/ whose brief is the D-13 brief and status is final or approved, and reuse its URL.
3. Then generate the voiceover from the narration lines (spoken text only, not the parenthetical source notes), then captions if a captions tool exists.
4. After every generation, run: python3 integrations/everygen_cards.py --project gta6 --kind <video|image|voiceover|captions> --title "<short title>" --model "<model>" --credits <credits spent> --aspect 9:16 --duration <seconds> --resolution <res> --url "<asset url>" --prompt "<exact prompt>" --brief "[[${BRIEF_STEM}]]" --moc "[[GTA6-Content]]" --status <draft|final>
   Mark the first render of the D-13 scene as "final" once it is the best you can do in one pass; everything else is "draft".
5. Append the card wikilinks under "## Results" in the brief, set its frontmatter status to "drafting", and fill "## What worked / what to change" with one or two factual lines (credits actually spent, anything that failed).
6. Never upload or reference any Rockstar / GTA footage, art, logos, likenesses or music. Never use the words GTA or Rockstar inside an image or video prompt.
7. Finish with a four-line summary: what was generated, credits spent, card paths, and anything that needs a human look.
PROMPT_EOF

CMD=(claude -p "$PROMPT"
  --permission-mode acceptEdits
  --allowedTools "mcp__everygen__*" "Bash(python3 integrations/everygen_cards.py*)" "Bash(python integrations/everygen_cards.py*)" "Read" "Edit" "Write" "Glob" "Grep"
  --max-turns "$MAX_TURNS"
  --output-format text)

if [ "$DRY_RUN" -eq 1 ]; then
  echo "== DRY RUN =="; echo "Brief: $BRIEF"; echo "Credit cap: $CREDIT_CAP  Max turns: $MAX_TURNS"; echo
  echo "Claude Code would be invoked as:"; printf '  %q ' "${CMD[@]}"; echo; echo
  echo "Prompt:"; echo "$PROMPT" | sed 's/^/  /'
  exit 0
fi

echo "[$(date -Is)] running $BRIEF (cap $CREDIT_CAP credits)" | tee -a "$LOG"
"${CMD[@]}" 2>&1 | tee -a "$LOG"
echo "[$(date -Is)] done" | tee -a "$LOG"
