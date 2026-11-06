#!/usr/bin/env python3
"""
everygen_cards.py — file an Everygen generation into the vault as an output card.

The Everygen MCP returns URLs and ids for each image / video / voiceover it makes. This
script turns one generation into a markdown card in vault/40-outputs/<project>/ with
frontmatter the rest of the Research Monster loop can read, mirroring the cards that
notebooklm_bridge.py writes for NotebookLM deliverables.

Usage:
  python integrations/everygen_cards.py --project gta6 --kind video \
      --title "Vice-coast dusk drive, hook A" --model "Seedance 2.5" --credits 16 \
      --aspect 9:16 --duration 4 --url https://example.com/clip.mp4 \
      --prompt "…" --source "[[20261106-gta6-launch-shorts-plan]]" --status draft

No network calls. No secrets. Prints the path it wrote.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUTS = ROOT / "vault" / "40-outputs"
KINDS = ("video", "image", "voiceover", "audio", "captions")
STATUSES = ("draft", "approved", "final", "published", "rejected")


def slugify(text: str, max_len: int = 48) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:max_len].rstrip("-") or "untitled"


def yaml_str(value: str) -> str:
    """Quote a scalar for YAML frontmatter (always double-quoted, escaped)."""
    return json.dumps(value, ensure_ascii=False)


def build_card(a: argparse.Namespace, now: dt.datetime) -> str:
    sources = list(a.source or [])
    tags = ["everygen", a.kind, a.project] + [t.lstrip("#") for t in (a.tag or [])]
    tags = list(dict.fromkeys(t for t in tags if t))  # de-dupe, keep order

    fm = [
        "---",
        f"title: {yaml_str(a.title)}",
        f"created: {now.strftime('%Y-%m-%d')}",
        "type: output",
        "engine: everygen",
        f"deliverable: {a.kind}",
        f"project: {yaml_str(a.project)}",
        f"model: {yaml_str(a.model)}",
        f"credits: {a.credits if a.credits is not None else 'null'}",
        f"aspect: {yaml_str(a.aspect) if a.aspect else 'null'}",
        f"duration_s: {a.duration if a.duration is not None else 'null'}",
        f"resolution: {yaml_str(a.resolution) if a.resolution else 'null'}",
        f"url: {yaml_str(a.url) if a.url else '\"\"'}",
        f"generation_id: {yaml_str(a.generation_id) if a.generation_id else '\"\"'}",
        f"status: {a.status}",
        "sources:",
    ]
    fm += [f"  - {yaml_str(s)}" for s in sources] or ["  []"]
    fm += ["tags: [" + ", ".join(tags) + "]", "---", ""]

    body = [
        f"# {a.title}",
        "",
        f"> {a.kind.capitalize()} made with Everygen · {a.model}"
        + (f" · {a.credits} credits" if a.credits is not None else ""),
        "",
    ]
    if a.url:
        if a.kind == "image":
            body += [f"![{a.title}]({a.url})", ""]
        body += [f"**Open:** {a.url}", ""]
    body += ["## Prompt", "", "```text", a.prompt.strip() if a.prompt else "(not recorded)", "```", ""]
    if a.negative_prompt:
        body += ["## Negative / avoid", "", "```text", a.negative_prompt.strip(), "```", ""]
    if a.references:
        body += ["## Reference inputs", ""] + [f"- {r}" for r in a.references] + [""]
    body += ["## Notes", "", a.notes.strip() if a.notes else "-", ""]
    body += ["## Related", ""]
    body += [f"- Brief:: {a.brief}" if a.brief else "- Brief:: "]
    body += [f"- Source:: {s}" for s in sources]
    body += [f"- MOC:: {a.moc}" if a.moc else "- MOC:: "]
    body += [""]
    return "\n".join(fm + body)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--project", required=True, help="vault/40-outputs/<project>/ (kebab-case)")
    p.add_argument("--kind", required=True, choices=KINDS)
    p.add_argument("--title", required=True)
    p.add_argument("--model", required=True, help='e.g. "Seedance 2.5", "Nano Banana 2"')
    p.add_argument("--prompt", default="", help="the exact prompt sent to Everygen")
    p.add_argument("--negative-prompt", default="")
    p.add_argument("--credits", type=int, default=None)
    p.add_argument("--aspect", default="", help="9:16, 16:9, 1:1 …")
    p.add_argument("--duration", type=float, default=None, help="seconds (video/audio)")
    p.add_argument("--resolution", default="", help="480p, 720p, 1080p, 4K")
    p.add_argument("--url", default="", help="asset URL returned by Everygen")
    p.add_argument("--generation-id", default="")
    p.add_argument("--status", default="draft", choices=STATUSES)
    p.add_argument("--source", action="append", help="[[wikilink]] to a vault note; repeatable")
    p.add_argument("--references", action="append", help="reference media used; repeatable")
    p.add_argument("--brief", default="", help="[[wikilink]] to the brief")
    p.add_argument("--moc", default="", help="[[wikilink]] to the project MOC")
    p.add_argument("--tag", action="append")
    p.add_argument("--notes", default="")
    p.add_argument("--outdir", default=None, help="override vault/40-outputs/<project>")
    p.add_argument("--dry-run", action="store_true", help="print the card instead of writing")
    a = p.parse_args(argv)

    a.project = slugify(a.project)
    now = dt.datetime.now()
    card = build_card(a, now)

    if a.dry_run:
        sys.stdout.write(card)
        return 0

    outdir = Path(a.outdir) if a.outdir else OUTPUTS / a.project
    outdir.mkdir(parents=True, exist_ok=True)
    fname = f"{now.strftime('%Y%m%d-%H%M%S')}-{a.kind}-{slugify(a.title)}.md"
    path = outdir / fname
    path.write_text(card, encoding="utf-8")
    try:
        shown = path.relative_to(ROOT)
    except ValueError:
        shown = path
    print(shown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
