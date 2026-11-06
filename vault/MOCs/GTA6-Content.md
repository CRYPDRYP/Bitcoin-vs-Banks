---
title: "GTA 6 Content — MOC"
type: moc
tags: [moc, gta6, produce]
---

# 🎮 GTA 6 Content — Map of Content

Side project: original, IP-safe short-form content around the Grand Theft Auto VI launch
(2026-11-19), produced through Everygen from vault research. The `SessionStart` hook surfaces
this so Claude knows where production stands.

## Current state
- _Status:_ lane scaffolded. Everygen registered in `.mcp.json`; `everygen-produce` skill
  ready; rights rules captured; launch plan with prompts drafted. No generations yet.
- _Next:_ run `/mcp` login on your own machine → "Run the D-13 countdown brief" →
  approve the draft → final render, voiceover, captions → card it → `learn`.

## Rules of the lane
- [[20261106-gta6-fan-content-rules]] — what Rockstar allows; no Rockstar assets into any generator.

## Plan & briefs
- [[20261106-gta6-launch-shorts-plan]] — formats, prompts, cadence, credit math.
- [[20261106-d13-countdown-brief]] — first short, ready to run (≈40 credits).
- _(further briefs land in `vault/40-outputs/gta6/` as `<date>-<slug>-brief.md`)_

## Facts we can state on screen `#gta6-facts`
- Release 2026-11-19 (PS5, Xbox Series X|S); pre-load from 2026-11-10 (Rockstar Newswire).
- Setting: Leonida / Vice City; leads Jason Duval and Lucia Caminos (trailers).
- Everything else: unconfirmed until Rockstar says so.

## Outputs (Everygen)
- _(cards from `integrations/everygen_cards.py` appear in `vault/40-outputs/gta6/`)_

## Tooling
- [[20261106-everygen-ai]] — the engine, models, scopes, pricing.
- Skill: `.claude/skills/everygen-produce/SKILL.md` · Runbook: `workflows/05-produce.md`
