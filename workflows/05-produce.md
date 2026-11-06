# Workflow 5 — Produce (Everygen)

**Goal:** turn what the vault knows into posted-ready short-form media (shorts, ads,
thumbnails, voiceovers, captions) without leaving Claude Code, and file every generation
back into the vault.

**Skill:** `everygen-produce` · **Config:** `.mcp.json` · **Code:** `integrations/everygen_cards.py`

## One-time setup (on your own machine, needs a browser)
1. Open this repo in Claude Code. It will ask you to approve the project MCP server
   `everygen` from `.mcp.json`. Approve it.
2. Run `/mcp`, choose `everygen`, and sign in to your Everygen account in the browser.
   It is OAuth 2.1 with PKCE; no API key. Grant the scopes you want
   (`generation:read`, `image:generate`, `video:generate`, `voiceover:generate`, …).
3. Have credits on the account (Starter 200 / Pro 500 / Creator 1,000 a month; no free plan).

If you prefer the CLI: `claude mcp add --transport http everygen https://everygen.ai/api/mcp`
adds it to your user config instead of the project file.

## Do it
Say: "Make the D-13 countdown short from the GTA 6 plan" or
"Turn the fees synthesis into a 30-second explainer short".
Claude will:
1. Create a brief from `vault/_templates/video-brief.md` in `vault/40-outputs/<project>/`.
2. Check your credit balance before spending.
3. Generate a still, then a cheap draft clip, and ask before upgrading to Seedance 2.5 /
   Kling / Gemini Omni at 1080p.
4. Add voiceover and captions.
5. Card every generation:
   ```bash
   python integrations/everygen_cards.py --project gta6 --kind video \
     --title "…" --model "Seedance 2.5" --credits 16 --aspect 9:16 --duration 4 \
     --url "<asset url>" --prompt "<exact prompt>" --source "[[note]]" --status draft
   ```
6. Link the cards from the brief and the project MOC.

## Daily countdown (GTA 6)
```bash
python integrations/countdown_briefs.py          # adds any missing briefs, today → launch day
```
Then say "Run today's countdown brief." Only D-13 and launch day render a new scene; the
other days reuse the approved final and change the counter, narration and captions.

## What happens
- Everygen renders on its credits; Claude only orchestrates.
- Results live as cards in `vault/40-outputs/<project>/` with frontmatter
  (`engine: everygen`, `model`, `credits`, `url`, `sources`, `status`), so `synthesize` and
  `learn` can read what was made and what it cost.

## Guardrails
- Rights: only upload media you own. For GTA 6, follow
  `vault/20-notes/20261106-gta6-fan-content-rules.md` (no Rockstar assets into generators).
- Cloud sessions: the login needs a browser and the sandbox may block `everygen.ai`.
  Produce from a local Claude Code session.
- Only `everygen.ai` / `www.viewmax.io` are official. Ignore look-alike domains.
