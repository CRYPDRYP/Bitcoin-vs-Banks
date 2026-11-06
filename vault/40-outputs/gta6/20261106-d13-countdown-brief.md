---
title: "D-13 countdown card — neon coast dusk"
created: 2026-11-06
type: brief
project: gta6
engine: everygen
format: short
aspect: "9:16"
target_length_s: 10
credit_budget: 40
status: planned
tags: [gta6, produce, everygen, countdown]
---

# D-13 countdown card — neon coast dusk

First short of the launch window. One original loopable scene, a burned-in day counter,
one narration line, captions on. Rights lane: [[20261106-gta6-fan-content-rules]].
Format and cadence: [[20261106-gta6-launch-shorts-plan]].

## Hook (first 2 seconds)
> The counter fills the frame on beat one: **13**. Then the city.

## Narration / script
1. "Thirteen days." (known: launch 2026-11-19, Rockstar Newswire)
2. "Pre-load opens on the tenth." (known: Rockstar Newswire, 2026-11-10)
3. "Everything else is still unconfirmed. We'll only say what's official." (framing line)

## Shot list
| # | Beat | Visual prompt (exact) | Model | Res / len | Est. credits | Card |
|---|------|------------------------|-------|-----------|--------------|------|
| 1 | Draft | Handheld phone footage at golden hour on a palm-lined coastal boulevard in a pastel art-deco beach city. Neon signs flicker on, a vintage convertible rolls past slowly, ocean on the left, humid haze, 2020s Florida feel. Natural ambient sound: surf, distant bass from a car stereo, gulls. One continuous shot, slight camera sway, no text, no logos, no recognisable people. | Seedance 2 Fast | 720p / 10s | ≈8 | |
| 2 | Final (same prompt, only after draft approved) | as above | Seedance 2.5 | 1080p / 10s | ≈25 | |
| 3 | Counter overlay | "13" in bold lowercase white with a thin neon outline, centred, then shrinks to the top third | captions / text tool, or edit locally | — | 0–2 | |

## Audio
- Voiceover: calm, neutral, unhurried; three lines above; no hype.
- Music / SFX: native clip audio only (surf, bass, gulls). No licensed tracks.
- Captions: on, large, bottom third, plain white.

## Sources used
- [[20261106-gta6-launch-shorts-plan]]
- [[GTA6-Content]] (facts section)

## Rights check
- [x] No third-party footage, logos, likenesses or music fed into any generator
- [ ] Platform AI-disclosure handled at upload (YouTube altered/synthetic, TikTok AI label)

## Run it
Say: "Run the D-13 countdown brief." The agent will check credits, make shot 1 as a draft,
show it, and only on a yes render shot 2, then voiceover, then captions, carding each step:
```bash
python integrations/everygen_cards.py --project gta6 --kind video \
  --title "D-13 countdown, draft" --model "Seedance 2 Fast" --credits 8 --aspect 9:16 \
  --duration 10 --resolution 720p --url "<asset url>" --prompt "<exact prompt>" \
  --brief "[[20261106-d13-countdown-brief]]" --moc "[[GTA6-Content]]" --status draft
```
Re-use: for D-12 through D-1, duplicate this brief, change the number and the narration date
line, and re-use the approved final clip instead of re-rendering it (counter overlay only).

## Results
_(cards land here)_

## What worked / what to change
-
