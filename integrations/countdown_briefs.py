#!/usr/bin/env python3
"""
countdown_briefs.py — generate the daily GTA 6 countdown briefs automatically.

One brief per day from today (or --from) through launch day, written to
vault/40-outputs/gta6/<YYYYMMDD>-d<N>-countdown-brief.md. Existing files are left alone, so
it is safe to run every day (or all at once). Narration lines are generated from the
official dates only: launch 2026-11-19, pre-load 2026-11-10 (Rockstar Newswire).

Usage:
  python integrations/countdown_briefs.py            # today → launch day
  python integrations/countdown_briefs.py --all      # every day D-13 → D-0
  python integrations/countdown_briefs.py --from 2026-11-10 --to 2026-11-12
  python integrations/countdown_briefs.py --dry-run  # list what would be written

No network calls. No secrets.
"""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTDIR = ROOT / "vault" / "40-outputs" / "gta6"
LAUNCH = dt.date(2026, 11, 19)
PRELOAD = dt.date(2026, 11, 10)
FIRST_DAY = LAUNCH - dt.timedelta(days=13)

WORDS = ["Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
         "Ten", "Eleven", "Twelve", "Thirteen"]

SCENE_PROMPT = (
    "Handheld phone footage at golden hour on a palm-lined coastal boulevard in a pastel "
    "art-deco beach city. Neon signs flicker on, a vintage convertible rolls past slowly, "
    "ocean on the left, humid haze, 2020s Florida feel. Natural ambient sound: surf, distant "
    "bass from a car stereo, gulls. One continuous shot, slight camera sway, no text, no "
    "logos, no recognisable people."
)
LAUNCH_PROMPT = (
    "Night on a neon-lit coastal boulevard in a pastel art-deco beach city, warm rain falling, "
    "reflections of pink and teal signs on wet asphalt, palms swaying, a few headlights "
    "passing slowly, humid tropical feel. Seamless loop. Natural sound: steady rain, distant "
    "traffic hiss, far-off thunder. No text, no logos, no recognisable people."
)


def narration(day: dt.date) -> list[str]:
    days = (LAUNCH - day).days
    lines: list[str] = []
    if days == 0:
        lines.append("Launch day. (known: 2026-11-19 on PlayStation 5 and Xbox Series X|S, Rockstar Newswire)")
    elif days == 1:
        lines.append("One day. (known: launch 2026-11-19, Rockstar Newswire)")
    else:
        lines.append(f"{WORDS[days]} days. (known: launch 2026-11-19, Rockstar Newswire)")

    if day < PRELOAD - dt.timedelta(days=1):
        lines.append("Pre-load opens on the tenth. (known: Rockstar Newswire, 2026-11-10)")
    elif day == PRELOAD - dt.timedelta(days=1):
        lines.append("Pre-load opens tomorrow. (known: Rockstar Newswire, 2026-11-10)")
    elif day == PRELOAD:
        lines.append("Pre-load is open as of today. (known: Rockstar Newswire, 2026-11-10)")
    elif days > 0:
        lines.append("Pre-load is already open. (known: Rockstar Newswire, from 2026-11-10)")

    if days == 0:
        lines.append("No gameplay, no cutscenes, no spoilers here. Go play. (framing line)")
    else:
        lines.append("Everything else is still unconfirmed. We'll only say what's official. (framing line)")
    return lines


def brief(day: dt.date) -> str:
    days = (LAUNCH - day).days
    label = "Launch day" if days == 0 else f"D-{days}"
    is_first = day == FIRST_DAY
    is_launch = days == 0
    scene = LAUNCH_PROMPT if is_launch else SCENE_PROMPT
    budget = 40 if (is_first or is_launch) else 15
    hook = (
        "> Rain on neon. No counter. The title card just says **today**."
        if is_launch
        else f"> The counter fills the frame on beat one: **{days}**. Then the city."
    )
    reuse_note = (
        "New scene for launch night (loopable). Render once, reuse for the launch-week recap."
        if is_launch
        else (
            "First render of the scene; later days reuse the approved final."
            if is_first
            else "Reuse the approved D-13 final clip. Only the counter, narration and captions change."
        )
    )
    shot_rows = (
        f"| 1 | Draft | {scene} | Seedance 2 Fast | 720p / 10s | ≈8 | |\n"
        f"| 2 | Final (same prompt, only after draft approved) | as above | Seedance 2.5 | 1080p / 10s | ≈25 | |\n"
        if (is_first or is_launch)
        else "| 1 | Scene | reuse approved final from [[20261106-d13-countdown-brief]] | — | 1080p / 10s | 0 | |\n"
    )
    counter_row = (
        "" if is_launch else
        f'| {3 if (is_first) else 2} | Counter overlay | "{days}" in bold lowercase white with a thin neon outline, centred, then shrinks to the top third | captions / text tool, or edit locally | — | 0–2 | |\n'
    )
    narr = "\n".join(f"{i}. \"{line.split(' (')[0]}\" ({line.split(' (', 1)[1]}" for i, line in enumerate(narration(day), 1))
    return f"""---
title: "{label} countdown card — neon coast {'rain loop' if is_launch else 'dusk'}"
created: {day.isoformat()}
type: brief
project: gta6
engine: everygen
format: {'loop' if is_launch else 'short'}
aspect: "9:16"
target_length_s: 10
credit_budget: {budget}
status: planned
tags: [gta6, produce, everygen, countdown]
---

# {label} countdown card — neon coast {'rain loop' if is_launch else 'dusk'}

Generated by `integrations/countdown_briefs.py` for {day.isoformat()}. {reuse_note}
Rights lane: [[20261106-gta6-fan-content-rules]]. Plan: [[20261106-gta6-launch-shorts-plan]].

## Hook (first 2 seconds)
{hook}

## Narration / script
{narr}

## Shot list
| # | Beat | Visual prompt (exact) | Model | Res / len | Est. credits | Card |
|---|------|------------------------|-------|-----------|--------------|------|
{shot_rows}{counter_row}
## Audio
- Voiceover: calm, neutral, unhurried; the lines above; no hype.
- Music / SFX: native clip audio only. No licensed tracks.
- Captions: on, large, bottom third, plain white.

## Sources used
- [[20261106-gta6-launch-shorts-plan]]
- [[GTA6-Content]] (facts section)

## Rights check
- [x] No third-party footage, logos, likenesses or music fed into any generator
- [ ] Platform AI-disclosure handled at upload (YouTube altered/synthetic, TikTok AI label)

## Run it
Say: "Run the {label} countdown brief." The agent checks credits, {'drafts shot 1, waits for a yes, renders the final,' if (is_first or is_launch) else 'reuses the approved scene,'} then voiceover and captions, carding each step:
```bash
python integrations/everygen_cards.py --project gta6 --kind voiceover \\
  --title "{label} countdown, narration" --model "Everygen voice" --credits 2 \\
  --url "<asset url>" --prompt "<the narration lines>" \\
  --brief "[[{day.strftime('%Y%m%d')}-{'d0' if is_launch else f'd{days}'}-countdown-brief]]" --moc "[[GTA6-Content]]" --status draft
```

## Results
_(cards land here)_

## What worked / what to change
-
"""


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--from", dest="start", type=dt.date.fromisoformat, default=None)
    p.add_argument("--to", dest="end", type=dt.date.fromisoformat, default=LAUNCH)
    p.add_argument("--all", action="store_true", help="D-13 through launch day")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)

    start = FIRST_DAY if a.all else (a.start or dt.date.today())
    start = max(start, FIRST_DAY)
    end = min(a.end, LAUNCH)
    if start > end:
        print("nothing to do: start is after launch day")
        return 0

    OUTDIR.mkdir(parents=True, exist_ok=True)
    written, skipped = [], []
    day = start
    while day <= end:
        days = (LAUNCH - day).days
        path = OUTDIR / f"{day.strftime('%Y%m%d')}-d{days}-countdown-brief.md"
        if path.exists():
            skipped.append(path)
        else:
            if not a.dry_run:
                path.write_text(brief(day), encoding="utf-8")
            written.append(path)
        day += dt.timedelta(days=1)

    for pth in written:
        print(("would write " if a.dry_run else "wrote   ") + str(pth.relative_to(ROOT)))
    for pth in skipped:
        print("exists  " + str(pth.relative_to(ROOT)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
