---
title: "Everygen AI (formerly Viewmax) — deep dive"
created: 2026-11-06
type: source
source_type: url
url: "https://everygen.ai/"
path: ""
author: "Viewmax LLC"
status: analyzed
tags: [everygen, tooling, video-generation, mcp, produce]
---

# Everygen AI (formerly Viewmax) — deep dive

> Everygen is a credit-based AI creative studio for short-form creators that fronts the
> major video and image models (Seedance, Kling, Gemini Omni, MiniMax, Grok Imagine,
> Nano Banana, GPT Image, Seedream) behind one web app and one remote MCP server. It is the
> **Produce** engine in this stack: research in, posted-ready media out.

Read on 2026-11-06 from `everygen.ai`, `/mcp`, `/developers`, `/pricing`, `/llms.txt`,
`/llms-full.txt`, `/openapi.json`, `/.well-known/oauth-authorization-server`, and the blog
post "How To Use Claude + Everygen MCP To Make Videos" (2026-06-18, updated 2026-10-18).

## What it is
- Web app at `everygen.ai`; Viewmax rebranded to Everygen ("same account, same credits").
  `viewmax.io` redirects. The company is Viewmax LLC. Unrelated look-alikes exist
  (`everygen-ai.com`, `everygenai.app`, `everygenai.io`); only `everygen.ai` is official.
- Positioned for YouTube Shorts, UGC ads, faceless story videos, thumbnails and product shots.
  Claims 5,000+ creators and "billions of views".
- **Wizard**: an in-app agent that plans a video, generates clips, images and voiceover, and
  asks approval for each paid step. **Director**: camera/lens/lighting controls for
  cinematic shots. **Shorts Studio**: proven short formats to re-skin. **Content Machine** and
  **AI Editing**: pick a reference video, hand it to Claude, Claude builds yours via the MCP.
- Edit tools: auto captions, caption remover, AI voiceover, voice changer, clone (swap
  people/places/products in a video), scriptwriter, multi-platform video downloader.

## Agent surface (the part we integrate)
- **MCP server:** `https://everygen.ai/api/mcp` (also `https://www.viewmax.io/api/mcp`),
  Streamable HTTP, JSON-RPC 2.0. Tool definitions come from `tools/list` after auth.
- **Auth:** OAuth 2.1 authorization-code with PKCE (S256). Issuer `https://www.viewmax.io`,
  dynamic client registration at `/api/auth/mcp/register`, refresh tokens supported.
  Claude Code's `/mcp` login handles the whole flow; no API key.
- **Scopes** (checked again on every tool run): `media:upload`, `image:generate`,
  `video:generate`, `voice:change`, `voiceover:generate`, `audio:generate`,
  `generation:read`, plus `openid profile email offline_access`.
- 401 → authorize; 403 → token lacks the tool's scope.
- There is no separate REST API: the OpenAPI document describes only the MCP transport and
  the OAuth scheme. Separate ChatGPT endpoint at `/api/chatgpt-mcp`.
- Works in Claude (connector), ChatGPT (plugin) and Cursor.

## Models (from llms-full.txt, 2026-11)
Video: Grok Imagine (1 cr, 720p, 1–15s) · Grok Imagine 1.5 (animate stills) · MiniMax H3 Max
/ Turbo (3–5 cr, fastest drafts, 1080p Turbo) · Seedance 2.5 (7 cr+, 1080p, 4–30s, best
quality) · Seedance 2 (4K, 4–15s) · Seedance 2 Mini / Fast (cheap drafts) · Gemini Omni 1.1
Flash (2 cr+, 4K, native audio, extend/edit) · Kling 3.0 / Pro / Turbo (motion control,
characters) · Kling O1 / O1 Pro (edit while keeping a character) · Kling 4.0 (30s, image +
video refs, Creator plan only).
Images: Nano Banana / 2 / 2 Lite / Pro (1–4 cr, up to 14 refs, 4K) · GPT Image 2 / 2.5
(1–16 cr) · Seedream 5 Flash / Lite / Pro (1–2 cr).

## Pricing (USD, 2026-11, no free plan)
| Plan | Monthly | Annual | Credits/mo | Notes |
|---|---|---|---|---|
| Starter | $24 | $9 ($108/yr) | 200 | 720p only, no 4K, no Kling 4.0 |
| Pro | $49 | $19 ($228/yr) | 500 (+500 one-time bonus on annual) | 4K, Seedance 2.5 1080p |
| Creator | $139 | $49 ($588/yr) | 1,000 (+1,000 bonus) | all models incl. Kling 4.0 |

- A 4s Seedance 2.5 clip at 720p = 16 credits. Plan credits do not roll over; top-ups last 90 days.
- Blog cost anchors: 60s animated ad = 385 credits ($19.25); 10s Seedance 2.5 draft at 480p
  = 18 credits ($0.90); a Zack-D-Films-style 3D explainer short ≈ 84 credits ($4.12). That
  implies ≈ 5¢ per credit on annual plans.
- Monetization allowed under Everygen ToS; each platform's AI/reused-content rules still apply.

## Why it matters for this stack
- Closes the loop: capture → NotebookLM analysis → synthesis → **produce** (shorts, thumbnails,
  explainers) → learn, without leaving Claude Code.
- Cost is predictable per clip, so a brief can carry a credit budget and the agent can
  check balance before spending.
- The documented Claude workflow (frame → animate → voiceover, cheap draft → upscale) maps
  directly to the `everygen-produce` skill's playbook.

## Caveats / confidence
- Tool names were not verified (tools/list needs OAuth; the cloud sandbox also blocks
  `everygen.ai`). The skill reads the live list instead of hardcoding. **Medium confidence**
  on anything beyond scopes and endpoints.
- Model availability and credit costs change often; re-read `llms-full.txt` before quoting.
- Unofficial look-alike domains exist; never log in anywhere but `everygen.ai`.

## Related
- MOC:: [[GTA6-Content]]
- MOC:: [[Bitcoin-vs-Banks]]
- See also:: [[20261106-gta6-fan-content-rules]], [[20261106-gta6-launch-shorts-plan]]
- Skill:: `.claude/skills/everygen-produce/SKILL.md` · Runbook:: `workflows/05-produce.md`
