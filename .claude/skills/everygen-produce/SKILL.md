---
name: everygen-produce
description: Turn vault research into short-form video, images, voiceovers and captions with the Everygen MCP (Seedance, Kling, Gemini Omni, MiniMax, Grok Imagine, Nano Banana, GPT Image), then file every generation back into the vault as an output card. Use when the user says "make a short/video/clip/ad/thumbnail", "animate this", "generate a voiceover", "produce content from these notes", or names Everygen, Seedance, Kling, or a GTA 6 short.
---

# everygen-produce

The **Produce** step of the Research Monster. Research goes in (vault notes, NotebookLM
outputs, a brief), finished short-form media comes out, and the vault keeps a record of
every generation so the next session knows what was made, what it cost, and what worked.

Everygen (formerly Viewmax, by Viewmax LLC) is a credit-based AI studio that fronts the
major video/image models behind one remote MCP server. Official site: `everygen.ai` only.
Reference captured in `vault/10-sources/20261106-everygen-ai.md`.

## Prerequisites (once)

1. The server is registered for this repo in `.mcp.json` (`everygen` → `https://everygen.ai/api/mcp`,
   Streamable HTTP). On first use Claude Code asks to approve the project server.
2. Sign in: run `/mcp` in Claude Code, pick `everygen`, and complete the OAuth login in the
   browser. It is OAuth 2.1 with PKCE and dynamic client registration, so no API key is
   needed. Tokens live in Claude Code's own credential store, never in the repo.
3. An Everygen subscription with credits (no free plan: Starter 200 / Pro 500 / Creator 1,000
   credits a month). Every tool call spends credits.

If a tool call fails with 401, re-run `/mcp` and log in again. A 403 means the token is missing
the scope that tool needs (see below): reconnect and grant it.

## Scopes → what they unlock

| Scope | Unlocks |
|---|---|
| `generation:read` | status, history, model list, credit balance |
| `image:generate` | stills, thumbnails, starting frames |
| `video:generate` | clips, ads, animate-a-photo |
| `voiceover:generate` | narration from a script |
| `audio:generate` | music / other audio |
| `voice:change` | re-voice existing audio or video |
| `media:upload` | push your own images/video/audio into the library as references |

Request the smallest set you need. Everygen re-checks the scope on every tool run.

## Tool discovery

Do **not** hardcode tool names. After login, read the live tool list from the `everygen`
server (it is served by MCP `tools/list`) and use the tool whose description matches the
job: generate image, generate video, voiceover, captions, upload media, check status/credits.
Tool names and input schemas can change between releases; the scope table above is stable.

## Model cheat sheet (from everygen.ai/llms-full.txt, 2026-11)

Video (starting credits = cheapest run: shortest length, lowest res, no inputs):

| Model | Best for | Max res | Length | Audio | From |
|---|---|---|---|---|---|
| Grok Imagine | fast stylised clips, edits | 720p | 1–15s | yes | 1 |
| Grok Imagine 1.5 | animate a still | 720p | 1–15s | yes | 2 |
| MiniMax H3 Max Turbo | fastest drafts | 1080p | 5–15s | yes | 3 |
| MiniMax H3 Max | fast, reliable | 720p | 5–15s | yes | 5 |
| Gemini Omni 1.1 Flash | realistic UGC/ads, video edits, extend | 4K | 3–10s | yes | 2 |
| Seedance 2 Mini / Fast | cheap drafts | 720p | 4–15s | optional | 3 / 4 |
| Seedance 2 | high quality, 4K | 4K | 4–15s | optional | 5 |
| Seedance 2.5 | highest quality | 1080p | 4–30s | optional | 7 |
| Kling 3.0 / Pro / Turbo | characters, motion control | 720p–1080p | 3–15s | optional/yes | 5–6 |
| Kling O1 / O1 Pro | edit video keeping a character | 720p | 5–10s | no | 7 / 10 |
| Kling 4.0 (Creator plan only) | up to 30s with image+video refs | 1080p | 3–30s | yes | 8 |

Images: Nano Banana 2 Lite (1 cr, fastest) · Nano Banana 2 (2–3, recommended) · Nano Banana
Pro (3–4, best, up to 14 refs, 4K) · GPT Image 2 / 2.5 (1–16, strong text and edits) ·
Seedream 5 Flash/Lite/Pro (1–2, strong text and layouts).

Rule of thumb: a 4-second Seedance 2.5 clip at 720p is 16 credits. On annual plans a credit
is roughly 5¢, so a finished 30–45s short with 4–6 clips, voiceover and captions tends to land
between 80 and 400 credits ($4–$20). Longer, higher-res, and reference inputs cost more.

## Playbook for the agent

1. **Start from a brief.** Copy `vault/_templates/video-brief.md` into
   `vault/40-outputs/<project>/<YYYYMMDD>-<slug>-brief.md`. Fill hook, beats, shot list,
   model per shot, aspect ratio, and a credit budget. Pull facts only from vault notes or
   NotebookLM outputs; link them with `[[wikilinks]]`. Never invent claims for narration.
2. **Check credits first** with the read tool. If the budget exceeds the balance, say so and
   stop; do not fire paid calls hoping they fit.
3. **Draft cheap, then upgrade.** First pass on MiniMax H3 Max Turbo, Seedance 2 Fast, or
   Grok Imagine at 480–720p. Only re-render the shots the user approves on Seedance 2.5,
   Kling 3.0 Turbo or Gemini Omni at 1080p+.
4. **Stills before motion.** For a story or explainer, generate a starting frame (Nano Banana
   2) and get a yes before animating it. Fixing a frame is 2 credits; fixing a clip is 16+.
5. **One paid call per confirmed step.** Say what you are about to generate and the expected
   credits before each paid call unless the user has told you to run the whole brief.
6. **File every result.** After each generation, write a card with
   `python integrations/everygen_cards.py` (see below) so the prompt, model, credits, URL
   and source links are in the vault. Link the card from the brief and the project MOC.
7. **Close out.** Append a "What worked / what to change" section to the brief. Offer a
   `learn` pass so prompt patterns that worked get remembered.

### Writing a card

```bash
python integrations/everygen_cards.py \
  --project gta6 --kind video --title "Vice-coast dusk drive, hook A" \
  --model "Seedance 2.5" --credits 16 --aspect 9:16 --duration 4 \
  --url "https://…/clip.mp4" \
  --prompt "…the exact prompt sent…" \
  --source "[[20261106-gta6-launch-shorts-plan]]" \
  --status draft
```
Kinds: `video`, `image`, `voiceover`, `audio`, `captions`. The card lands in
`vault/40-outputs/<project>/<timestamp>-<kind>-<slug>.md` with frontmatter the rest of the
loop can read (`deliverable`, `engine: everygen`, `model`, `credits`, `url`, `sources`, `status`).

### GTA 6 countdown lane (automated briefs)

`python integrations/countdown_briefs.py` writes today's-through-launch countdown briefs into
`vault/40-outputs/gta6/` (idempotent; `--all` for every day, `--dry-run` to preview). When
the user says "run today's countdown", open the brief dated today, follow its shot list, and
reuse the approved D-13 final clip rather than re-rendering the scene.

## Style defaults (from `vault/_memory/style-guide.md`)

- Narration is neutral and precise. No hype words, no price talk, no financial advice.
- Every factual line in a script traces to a vault note; mark uncertain claims as claimed, not known.
- Vertical 9:16 for Shorts/Reels/TikTok, 16:9 for YouTube long-form and thumbnails.
- Captions on by default for vertical output.

## Guardrails

- **Rights.** Only upload media you have the rights to use (Everygen ToS). For GTA 6 work,
  read `vault/20-notes/20261106-gta6-fan-content-rules.md` first: do not feed Rockstar
  trailers, screenshots, logos, character likenesses or music into any generator, and keep
  the lane to original, inspired-by visuals plus commentary.
- **Platform rules.** YouTube, TikTok and Meta have their own disclosure and reused-content
  rules for AI media; Everygen's monetization FAQ defers to them. Label AI content where the
  platform asks.
- **No secrets in the vault.** OAuth state stays in Claude Code; nothing from `~/.claude` is
  committed.
- **Only the official site.** `everygen.ai` (and `www.viewmax.io`) are the only official
  domains; `everygen-ai.com`, `everygenai.app` and `everygenai.io` are unrelated companies.
- **Cloud sessions.** The OAuth login needs a browser and the sandbox network may block
  `everygen.ai`. Do production runs from Claude Code on the user's own machine.
