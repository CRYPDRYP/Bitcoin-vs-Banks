---
title: "GTA 6 launch-window shorts plan (Everygen)"
created: 2026-11-06
type: note
status: captured
project: gta6
tags: [gta6, produce, everygen, shorts, plan]
---

# GTA 6 launch-window shorts plan (Everygen)

> Thirteen days to launch (2026-11-19, PS5 and Xbox Series X|S; pre-load from 2026-11-10,
> up to ~212 GB per Rockstar). Interest peaks from pre-load day through launch week. This
> plan runs a daily cadence of original, IP-safe AI shorts made through the `everygen-produce`
> skill, each built from a brief and filed back into the vault.

Rights lane first: read [[20261106-gta6-fan-content-rules]]. Nothing below uses Rockstar
footage, art, logos, likenesses or music as generator input.

## Known facts to build on (official, 2026-11-06)
- Release: 2026-11-19 on PlayStation 5 and Xbox Series X|S. Pre-load from 2026-11-10.
- Setting: the state of Leonida, including Vice City. Leads: Jason Duval and Lucia Caminos
  (from Rockstar's trailers). Do not render their likenesses.
- Anything else (price, PC date, map size, online mode) is unconfirmed; say so on screen.

## Formats (pick per day)
| Format | Visuals (all original) | Narration source | Draft model | Final model | Est. credits |
|---|---|---|---|---|---|
| **Countdown card** (8–12s) | Neon coast dusk loop, big day counter burned in | one line | Grok Imagine (1) | Seedance 2.5 720p (16) | 20 |
| **"What we know" explainer** (30–45s) | 4–6 clips: pastel art-deco streets, palm highway, storm over a marina, night skyline | vault note, cited | MiniMax H3 Max Turbo (3 each) | Seedance 2.5 / Gemini Omni (16–30 each) | 120–200 |
| **Faceless news desk** (20–30s) | Original studio set + AI avatar, lower-third text | daily news note | Gemini Omni 1.1 Flash (2+) | same, 1080p | 60–120 |
| **Ranking / "5 things"** (30s) | 5 stylised vignettes | vault note | MiniMax Turbo | Seedance 2.5 | 100–160 |
| **Launch-night loop** (loopable 10–15s) | rain on a neon boulevard, sound on | none | Seedance 2 Fast (4) | Seedance 2.5 (16+) | 25 |
| **Thumbnail** (16:9) | bold text, high contrast, original scene | n/a | Nano Banana 2 (2–3) | Nano Banana Pro (3–4) | 4 |

Credit math: at ≈ 5¢/credit (annual plan), a 150-credit short ≈ $7.50. Fourteen shorts across
the window ≈ 1,500–2,500 credits, so Pro (500/mo + bonus) covers a light cadence and
Creator (1,000/mo + bonus) covers daily output with re-renders.

## Prompt starters (copy into a brief, adjust, then generate)
These describe a vibe, never a trademark. Keep "GTA" and "Rockstar" out of the image/video prompt.

**Coast dusk loop (9:16, sound on):**
```text
Handheld phone footage at golden hour on a palm-lined coastal boulevard in a pastel art-deco
beach city. Neon signs flicker on, a vintage convertible rolls past slowly, ocean on the left,
humid haze, 2020s Florida feel. Natural ambient sound: surf, distant bass from a car stereo,
gulls. One continuous shot, slight camera sway, no text, no logos, no recognisable people.
```

**Explainer clip, marina storm (9:16):**
```text
Cinematic wide shot of a luxury marina at night as a tropical storm rolls in, yachts rocking,
rain hitting neon-lit water, lightning behind a pastel skyline. Slow push-in, film grain,
anamorphic flares. Sound: wind, rain, distant thunder. No text, no logos, no faces.
```

**News desk frame (16:9 still, then animate):**
```text
A sleek modern news studio with a curved desk, teal and magenta accent lighting, a large
blank screen behind the desk, empty presenter chair, shallow depth of field, photoreal.
No text on screen, no logos.
```

**Thumbnail (16:9):**
```text
Bold YouTube thumbnail: a pastel art-deco skyline at dusk, giant lowercase white text
"13 days" with a thin neon outline, high contrast, almost no other elements.
```

## Daily cadence (D-13 → launch +3)
- **D-13 to D-10:** countdown cards + one "what we know" explainer; set up the news-desk
  frame and voice once, reuse it.
- **D-9 (pre-load day) to D-1:** news desk daily (pre-load sizes, store listings, official
  posts), one ranking short, thumbnails for each.
- **Launch day:** launch-night loop goes up at midnight local; news desk recap in the
  afternoon. No gameplay, no cutscenes, no spoilers.
- **Launch +1 to +3:** explainers on confirmed facts only; keep the rights note open.

## Workflow per short
1. Copy `vault/_templates/video-brief.md` → `vault/40-outputs/gta6/<date>-<slug>-brief.md`.
2. Fill narration from vault notes only; cite with `[[wikilinks]]`.
3. Run `everygen-produce`: check credits → stills → cheap drafts → approve → final renders →
   voiceover → captions.
4. Card every generation with `integrations/everygen_cards.py --project gta6 …`.
5. Link cards from the brief and from [[GTA6-Content]].

## Open questions
- Which Everygen tools exist for captions and voiceover via MCP (confirm from `tools/list`).
- Whether a single AI avatar can be kept consistent across days (Kling O1 or Gemini Omni
  "keep the character" edits are the candidates).

## Related
- MOC:: [[GTA6-Content]]
- [[20261106-everygen-ai]] · [[20261106-gta6-fan-content-rules]]
