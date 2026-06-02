#!/usr/bin/env python3
"""
NotebookLM bridge for the Research Monster.

Drives the `notebooklm` CLI (provided by the `notebooklm-py` package) so the
NotebookLM "analysis engine" can be automated from Claude Code instead of
copy-pasting by hand. Heavy reading/analysis runs on Google's compute; the
results are written straight back into the Obsidian memory layer (vault/).

Typical use (from Claude Code, in plain language → these commands):

    # one-time, interactive, in a real terminal:
    notebooklm login

    # bundle vault sources into a fresh notebook and pull back a briefing doc:
    python integrations/notebooklm_bridge.py handoff \
        --project "Bitcoin vs Banks" \
        --source https://example.com/article \
        --source vault/10-sources/some-pdf.pdf \
        --format briefing-doc \
        --append "Compare settlement finality and fee structure."

    # ask a one-off question against an existing notebook and save the answer:
    python integrations/notebooklm_bridge.py ask \
        --notebook abc123 --project "Bitcoin vs Banks" \
        "What does the evidence say about chargeback fraud?"

The bridge wraps the CLI via subprocess (rather than the library client)
because the CLI surface is stable and documented, and it is exactly what a
human operator would script. All calls use `--json` + `--quiet` so output is
machine-parseable.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Local sibling module — works both when run as a script (integrations/ on
# sys.path) and when imported as integrations.notebooklm_bridge.
try:
    from . import mindmap_canvas
except ImportError:  # pragma: no cover - script execution
    import mindmap_canvas

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #

REPO_ROOT = Path(__file__).resolve().parent.parent
VAULT = REPO_ROOT / "vault"
OUTPUTS = VAULT / "40-outputs"

CLI = "notebooklm"


# --------------------------------------------------------------------------- #
# Low-level CLI plumbing
# --------------------------------------------------------------------------- #


class BridgeError(RuntimeError):
    """Raised when the notebooklm CLI is missing, unauthenticated, or errors."""


def _ensure_cli() -> None:
    if shutil.which(CLI) is None:
        raise BridgeError(
            f"`{CLI}` CLI not found. Install it with:  pip install notebooklm-py"
        )


def _run(args: list[str], *, want_json: bool = True) -> object:
    """Run `notebooklm --quiet <args> [--json]` and return parsed JSON (or text)."""
    _ensure_cli()
    cmd = [CLI, "--quiet", *args]
    if want_json and "--json" not in args:
        cmd.append("--json")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        # This CLI may emit its error payload on stdout or stderr; check both.
        combined = f"{proc.stderr or ''}\n{proc.stdout or ''}".strip()
        if re.search(r"(auth_required|not logged in|run .*login|unauthenticat|login first)",
                     combined, re.I):
            raise BridgeError(
                "NotebookLM is not authenticated. Run `notebooklm login` in a "
                "terminal first (it opens a browser)."
            )
        raise BridgeError(f"`{' '.join(cmd)}` failed:\n{combined}")

    out = (proc.stdout or "").strip()
    if not want_json:
        return out
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        # Some commands print a JSON object embedded in surrounding text.
        match = re.search(r"(\{.*\}|\[.*\])", out, re.S)
        if match:
            return json.loads(match.group(1))
        return out


def _first(d: object, *keys: str, default=None):
    """Find the first of `keys` anywhere in a (possibly nested) dict/list payload.

    The CLI wraps results in envelopes like {"notebook": {"id": ...}} or
    {"artifact": {"url": ...}}, so we breadth-first search nested containers
    rather than only the top level.
    """
    queue: list = [d]
    while queue:
        cur = queue.pop(0)
        if isinstance(cur, dict):
            for k in keys:
                if k in cur and cur[k] not in (None, ""):
                    return cur[k]
            queue.extend(cur.values())
        elif isinstance(cur, list):
            queue.extend(cur)
    return default


# --------------------------------------------------------------------------- #
# NotebookLM operations
# --------------------------------------------------------------------------- #


def check_auth() -> bool:
    """Best-effort auth check. Returns True if a session looks usable.

    Uses `list`, which requires authentication, so an unauthenticated profile
    surfaces here instead of midway through a handoff.
    """
    try:
        _run(["list"], want_json=True)
        return True
    except BridgeError:
        return False


def create_notebook(title: str) -> str:
    data = _run(["create", title])
    nb_id = _first(data, "id", "notebook_id", "notebookId")
    if not nb_id:
        raise BridgeError(f"Could not read new notebook id from: {data!r}")
    return str(nb_id)


def add_source(notebook: str, content: str, *, stype: str | None = None,
               title: str | None = None) -> dict:
    args = ["source", "add", content, "-n", notebook]
    if stype:
        args += ["--type", stype]
    if title:
        args += ["--title", title]
    data = _run(args)
    return data if isinstance(data, dict) else {"raw": data}


def ask(notebook: str, question: str, sources: list[str] | None = None) -> dict:
    args = ["ask", question, "-n", notebook]
    for s in sources or []:
        args += ["-s", s]
    data = _run(args)
    return data if isinstance(data, dict) else {"answer": str(data)}


def generate_report(notebook: str, *, fmt: str = "briefing-doc",
                    description: str | None = None, append: str | None = None,
                    timeout: int = 300) -> dict:
    args = ["generate", "report", "-n", notebook, "--format", fmt,
            "--wait", "--timeout", str(timeout)]
    if append and fmt != "custom":
        args += ["--append", append]
    if description:
        args.append(description)
    data = _run(args)
    return data if isinstance(data, dict) else {"raw": data}


def artifact_get(notebook: str, artifact_id: str) -> dict:
    data = _run(["artifact", "get", artifact_id, "-n", notebook])
    return data if isinstance(data, dict) else {"raw": data}


# --------------------------------------------------------------------------- #
# Deliverables (Studio): audio overview, mind map, flashcards, infographic
# --------------------------------------------------------------------------- #

# Maps a friendly deliverable name to its CLI subcommand and option schema.
# `options` maps a CLI flag to the argparse attribute that supplies its value.
DELIVERABLE_SPECS: dict[str, dict] = {
    "audio": {
        "subcmd": ["generate", "audio"],
        "wait": True, "timeout": 1200, "takes_description": True,
        "options": {"--format": "audio_format", "--length": "audio_length"},
        "emoji": "🎙️", "label": "audio overview (podcast)",
    },
    "mindmap": {
        "subcmd": ["generate", "mind-map"],
        "wait": False, "timeout": None, "takes_description": False,
        "options": {"--instructions": "mindmap_instructions"},
        "emoji": "🧠", "label": "mind map",
    },
    "flashcards": {
        "subcmd": ["generate", "flashcards"],
        "wait": True, "timeout": 300, "takes_description": True,
        "options": {"--quantity": "flashcards_quantity",
                    "--difficulty": "flashcards_difficulty"},
        "emoji": "🃏", "label": "flashcards",
    },
    "infographic": {
        "subcmd": ["generate", "infographic"],
        "wait": True, "timeout": 300, "takes_description": True,
        "options": {"--orientation": "infographic_orientation",
                    "--detail": "infographic_detail",
                    "--style": "infographic_style"},
        "emoji": "📊", "label": "infographic",
    },
}


def generate_deliverable(notebook: str, kind: str, *, description: str | None = None,
                         options: dict | None = None,
                         source_ids: list[str] | None = None) -> dict:
    """Generate one Studio deliverable and (where supported) wait for it."""
    if kind not in DELIVERABLE_SPECS:
        raise BridgeError(f"Unknown deliverable '{kind}'. "
                          f"Choose from: {', '.join(DELIVERABLE_SPECS)}")
    spec = DELIVERABLE_SPECS[kind]
    args = list(spec["subcmd"]) + ["-n", notebook]
    for flag, attr in spec["options"].items():
        val = (options or {}).get(attr)
        if val:
            args += [flag, str(val)]
    for sid in source_ids or []:
        args += ["-s", sid]
    if spec["wait"]:
        args += ["--wait", "--timeout", str(spec["timeout"])]
    if spec["takes_description"] and description:
        args.append(description)
    data = _run(args)
    return data if isinstance(data, dict) else {"raw": data}


def download_and_convert_mindmap(project: str, notebook: str, *,
                                 name: str | None = None,
                                 artifact_id: str | None = None) -> tuple[Path, Path]:
    """Download a mind map as JSON and convert it to an Obsidian .canvas file."""
    proj_dir = OUTPUTS / _slug(project)
    proj_dir.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = proj_dir / f"{stamp}-mindmap.json"

    args = ["download", "mind-map", "-n", notebook, str(json_path), "--force"]
    if name:
        args += ["--name", name]
    if artifact_id:
        args += ["--artifact", artifact_id]
    _run(args, want_json=False)

    canvas_path = mindmap_canvas.convert(json_path, proj_dir / f"{stamp}-mindmap.canvas")
    return json_path, canvas_path


def write_artifact_card(project: str, kind: str, payload: dict, *,
                        notebook: str, sources: list[str], options: dict) -> Path:
    """Write a deliverable 'card' into the vault: metadata + link/embed + raw JSON."""
    spec = DELIVERABLE_SPECS.get(kind, {"emoji": "📦", "label": kind})
    artifact_id = _first(payload, "id", "artifact_id", "artifactId")
    url = _first(payload, "url")
    status = _first(payload, "status", default="unknown")
    title = _first(payload, "title", default=f"{project} — {spec['label']}")

    # Enrich from `artifact get` when the generate call didn't return the URL yet.
    if artifact_id and not url:
        try:
            got = artifact_get(notebook, str(artifact_id))
            url = _first(got, "url") or url
            status = _first(got, "status", default=status)
            title = _first(got, "title", default=title)
            payload = {**payload, "_artifact_get": got}
        except BridgeError:
            pass

    # Body: link or embed depending on deliverable type.
    if url and kind == "infographic":
        media = f"![{title}]({url})\n\n[Open infographic]({url})"
    elif url:
        media = f"[▶ Open {spec['label']} in NotebookLM]({url})"
    else:
        media = ("_No direct URL returned — open the notebook in NotebookLM to view "
                 "this deliverable._")

    used = "\n".join(f"- `{k}`: {v}" for k, v in (options or {}).items() if v) or "- (defaults)"
    src_links = "\n".join(f"  - {s}" for s in sources) or "  - (existing notebook sources)"
    fm = (
        "---\n"
        f"title: \"{title}\"\n"
        f"created: {_dt.date.today().isoformat()}\n"
        "type: notebooklm-deliverable\n"
        f"deliverable: {kind}\n"
        f"status: {status}\n"
        "engine: notebooklm\n"
        f"notebook_id: {notebook}\n"
        f"artifact_id: {artifact_id or ''}\n"
        f"url: {url or ''}\n"
        f"project: \"{project}\"\n"
        "sources:\n"
        f"{src_links}\n"
        f"tags: [notebooklm, deliverable, {kind}]\n"
        "---\n\n"
    )
    body = (
        f"# {spec['emoji']} {title}\n\n"
        f"> {spec['label'].capitalize()} generated by NotebookLM · status: **{status}**\n"
        f"> MOC: [[{_slug(project)}]] · [[Bitcoin-vs-Banks]]\n\n"
        f"{media}\n\n"
        f"## Generation settings\n{used}\n\n"
        f"## Raw response\n```json\n{json.dumps(payload, indent=2, ensure_ascii=False)}\n```\n"
    )

    proj_dir = OUTPUTS / _slug(project)
    proj_dir.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = proj_dir / f"{stamp}-{kind}.md"
    path.write_text(fm + body, encoding="utf-8")
    return path



def extract_text(payload: dict) -> str:
    """Pull the human-readable body out of an artifact/ask JSON payload."""
    text = _first(payload, "content", "text", "markdown", "body", "answer",
                  "report", "summary")
    if isinstance(text, str) and text.strip():
        return text.strip()
    # Fall back to a readable dump so nothing is silently lost.
    return "```json\n" + json.dumps(payload, indent=2, ensure_ascii=False) + "\n```"


# --------------------------------------------------------------------------- #
# Vault helpers
# --------------------------------------------------------------------------- #


def _slug(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return s or "untitled"


def _classify(content: str) -> str | None:
    """Auto-detect source type so we can pass the right --type to the CLI."""
    if re.match(r"^https?://", content):
        if re.search(r"(youtube\.com|youtu\.be)", content):
            return "youtube"
        return "url"
    if Path(content).exists():
        return "file"
    return None  # let the CLI auto-detect / treat as text


def write_output(project: str, kind: str, body: str, *,
                 sources: list[str], notebook: str, artifact_id: str | None) -> Path:
    """Write a NotebookLM artifact into vault/40-outputs/<project>/ with frontmatter."""
    proj_dir = OUTPUTS / _slug(project)
    proj_dir.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    path = proj_dir / f"{stamp}-{_slug(kind)}.md"

    src_links = "\n".join(f"  - {s}" for s in sources) or "  - (none)"
    frontmatter = (
        "---\n"
        f"title: \"{project} — {kind}\"\n"
        f"created: {_dt.date.today().isoformat()}\n"
        "type: notebooklm-output\n"
        f"engine: notebooklm\n"
        f"notebook_id: {notebook}\n"
        f"artifact_id: {artifact_id or ''}\n"
        f"project: \"{project}\"\n"
        "sources:\n"
        f"{src_links}\n"
        "tags: [notebooklm, output]\n"
        "---\n\n"
    )
    moc = f"[[{_slug(project)}]] · [[Bitcoin-vs-Banks]]"
    path.write_text(f"{frontmatter}> Generated by NotebookLM. MOC: {moc}\n\n{body}\n",
                    encoding="utf-8")
    return path


# --------------------------------------------------------------------------- #
# High-level workflows
# --------------------------------------------------------------------------- #


def cmd_handoff(args: argparse.Namespace) -> int:
    if not check_auth():
        print("⚠  Not authenticated. Run `notebooklm login` first.", file=sys.stderr)
        return 2

    title = args.title or f"{args.project} — {_dt.date.today().isoformat()}"
    print(f"• Creating notebook: {title}")
    nb = create_notebook(title)
    print(f"  notebook id: {nb}")

    for src in args.source:
        stype = _classify(src)
        print(f"• Adding source ({stype or 'auto'}): {src}")
        add_source(nb, src, stype=stype)

    print(f"• Generating {args.format} (this runs on Google's compute)…")
    report = generate_report(nb, fmt=args.format, description=args.description,
                             append=args.append, timeout=args.timeout)
    artifact_id = _first(report, "id", "artifact_id", "artifactId")

    body_payload = report
    if artifact_id:
        try:
            body_payload = artifact_get(nb, str(artifact_id))
        except BridgeError:
            pass

    body = extract_text(body_payload)
    path = write_output(args.project, args.format, body,
                        sources=args.source, notebook=nb,
                        artifact_id=str(artifact_id) if artifact_id else None)
    print(f"✓ Wrote artifact → {path.relative_to(REPO_ROOT)}")
    print(f"  notebook id (reuse with --notebook): {nb}")
    return 0


def cmd_ask(args: argparse.Namespace) -> int:
    if not check_auth():
        print("⚠  Not authenticated. Run `notebooklm login` first.", file=sys.stderr)
        return 2
    result = ask(args.notebook, args.question, sources=args.source)
    body = extract_text(result)
    if args.save:
        path = write_output(args.project, f"qa-{_slug(args.question)[:40]}", body,
                            sources=args.source, notebook=args.notebook,
                            artifact_id=None)
        print(f"✓ Saved answer → {path.relative_to(REPO_ROOT)}")
    print("\n" + body)
    return 0


def _require_auth() -> bool:
    if not check_auth():
        print("⚠  Not authenticated. Run `notebooklm login` first.", file=sys.stderr)
        return False
    return True


def _resolve_notebook(args: argparse.Namespace) -> tuple[str, list[str]]:
    """Return (notebook_id, sources_added). Reuse --notebook, else create from --source."""
    sources = list(getattr(args, "source", []) or [])
    if getattr(args, "notebook", None):
        nb = args.notebook
        for src in sources:
            stype = _classify(src)
            print(f"• Adding source ({stype or 'auto'}): {src}")
            add_source(nb, src, stype=stype)
        return nb, sources
    if not sources:
        raise BridgeError("Provide either --notebook <id> or one or more --source.")
    title = getattr(args, "title", None) or f"{args.project} — {_dt.date.today().isoformat()}"
    print(f"• Creating notebook: {title}")
    nb = create_notebook(title)
    print(f"  notebook id: {nb}")
    for src in sources:
        stype = _classify(src)
        print(f"• Adding source ({stype or 'auto'}): {src}")
        add_source(nb, src, stype=stype)
    return nb, sources


def cmd_create(args: argparse.Namespace) -> int:
    if not _require_auth():
        return 2
    title = args.title or f"{args.project} — {_dt.date.today().isoformat()}"
    nb = create_notebook(title)
    for src in args.source:
        stype = _classify(src)
        print(f"• Adding source ({stype or 'auto'}): {src}")
        add_source(nb, src, stype=stype)
    print(f"✓ Notebook ready: {nb}")
    print(f"  reuse it with:  --notebook {nb}")
    return 0


def cmd_add_source(args: argparse.Namespace) -> int:
    if not _require_auth():
        return 2
    for src in args.source:
        stype = _classify(src)
        print(f"• Adding source ({stype or 'auto'}): {src}")
        add_source(args.notebook, src, stype=stype, title=args.title)
    print(f"✓ Added {len(args.source)} source(s) to {args.notebook}")
    return 0


def cmd_studio(args: argparse.Namespace) -> int:
    if not _require_auth():
        return 2
    nb, sources = _resolve_notebook(args)
    options = {
        "audio_format": args.audio_format, "audio_length": args.audio_length,
        "flashcards_quantity": args.flashcards_quantity,
        "flashcards_difficulty": args.flashcards_difficulty,
        "infographic_orientation": args.infographic_orientation,
        "infographic_detail": args.infographic_detail,
        "infographic_style": args.infographic_style,
        "mindmap_instructions": args.mindmap_instructions,
    }
    deliverables = args.deliverable or ["audio", "mindmap", "flashcards", "infographic"]
    rc = 0
    for kind in deliverables:
        spec = DELIVERABLE_SPECS[kind]
        print(f"{spec['emoji']} Generating {spec['label']} (on Google's compute)…")
        try:
            payload = generate_deliverable(nb, kind, description=args.description,
                                           options=options, source_ids=args.source_id)
            path = write_artifact_card(args.project, kind, payload,
                                       notebook=nb, sources=sources, options=options)
            print(f"   ✓ {kind} → {path.relative_to(REPO_ROOT)}")
            if kind == "mindmap":
                try:
                    _, canvas = download_and_convert_mindmap(args.project, nb)
                    print(f"   ✓ canvas → {canvas.relative_to(REPO_ROOT)}  "
                          f"(open in Obsidian to view it visually)")
                except BridgeError as e:
                    print(f"   • mindmap canvas skipped: {e}", file=sys.stderr)
        except BridgeError as e:
            rc = 1
            print(f"   ✗ {kind} failed: {e}", file=sys.stderr)
    print(f"\nNotebook id (reuse with --notebook): {nb}")
    return rc


def cmd_doctor(args: argparse.Namespace) -> int:
    """Check that the installation is finished: CLI present, logged in, vault ready."""
    ok = True

    # 1. CLI installed?
    cli_path = shutil.which(CLI)
    if cli_path:
        try:
            ver = subprocess.run([CLI, "--version"], capture_output=True, text=True).stdout.strip()
        except Exception:
            ver = "?"
        print(f"✓ notebooklm CLI installed  ({ver or cli_path})")
    else:
        ok = False
        print("✗ notebooklm CLI not found  →  pip install -r requirements.txt")

    # 2. Authenticated?
    if cli_path:
        if check_auth():
            print("✓ authenticated with NotebookLM")
        else:
            ok = False
            print("✗ not authenticated  →  notebooklm login   (opens a browser)")

    # 3. Vault layout present?
    needed = ["00-inbox", "10-sources", "20-notes", "30-synthesis", "40-outputs",
              "MOCs", "_memory", "_templates"]
    missing = [d for d in needed if not (VAULT / d).is_dir()]
    if missing:
        ok = False
        print(f"✗ vault folders missing: {', '.join(missing)}")
    else:
        print("✓ Obsidian vault layout present")

    # 4. SessionStart memory hook present?
    hook = REPO_ROOT / ".claude" / "hooks" / "load-memory.sh"
    print(f"{'✓' if hook.is_file() else '✗'} memory hook "
          f"({hook.relative_to(REPO_ROOT)})")

    print("\n" + ("🎉 Installation complete — try a `studio` or `handoff` run."
                  if ok else
                  "➡  Resolve the ✗ items above, then re-run: "
                  "python integrations/notebooklm_bridge.py doctor"))
    return 0 if ok else 1


def cmd_canvas(args: argparse.Namespace) -> int:
    """Download an existing notebook's mind map and convert it to an Obsidian Canvas."""
    if not _require_auth():
        return 2
    try:
        json_path, canvas_path = download_and_convert_mindmap(
            args.project, args.notebook, name=args.name, artifact_id=args.artifact)
    except BridgeError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1
    print(f"✓ Mind map JSON   → {json_path.relative_to(REPO_ROOT)}")
    print(f"✓ Obsidian Canvas → {canvas_path.relative_to(REPO_ROOT)}")
    print("Open the .canvas file in Obsidian (it renders as a visual mind map).")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="NotebookLM bridge for the Research Monster.")
    sub = p.add_subparsers(dest="command", required=True)

    cv = sub.add_parser("canvas",
                        help="Download a notebook's mind map and convert it to an "
                             "Obsidian Canvas (.canvas) for visual viewing.")
    cv.add_argument("--project", required=True, help="Project name (used for vault paths).")
    cv.add_argument("--notebook", required=True, help="Notebook id (partial ok).")
    cv.add_argument("--name", help="Pick a specific mind map by title (fuzzy match).")
    cv.add_argument("--artifact", help="Pick a specific mind map by artifact id.")
    cv.set_defaults(func=cmd_canvas)

    sub.add_parser("doctor",
                   help="Check the install: CLI present, logged in, vault ready."
                   ).set_defaults(func=cmd_doctor)


    c = sub.add_parser("create", help="Create a notebook and optionally add sources.")
    c.add_argument("--project", required=True, help="Project name (used for the title).")
    c.add_argument("--title", help="Notebook title (defaults to project + date).")
    c.add_argument("--source", action="append", default=[],
                   help="URL / file / YouTube / text to add. Repeatable.")
    c.set_defaults(func=cmd_create)

    s = sub.add_parser("add-source", help="Add one or more sources to an existing notebook.")
    s.add_argument("--notebook", required=True, help="Notebook id (partial ok).")
    s.add_argument("--source", action="append", default=[], required=True,
                   help="URL / file / YouTube / text. Repeatable.")
    s.add_argument("--title", help="Custom title for text/file sources.")
    s.set_defaults(func=cmd_add_source)

    d = sub.add_parser("studio",
                       help="Generate deliverables (audio, mindmap, flashcards, infographic).")
    d.add_argument("--project", required=True, help="Project name (used for vault paths).")
    d.add_argument("--notebook", help="Existing notebook id. Omit to create from --source.")
    d.add_argument("--title", help="Notebook title when creating (defaults to project + date).")
    d.add_argument("--source", action="append", default=[],
                   help="Sources to create a notebook from (if --notebook omitted). Repeatable.")
    d.add_argument("--deliverable", action="append",
                   choices=list(DELIVERABLE_SPECS),
                   help="Which deliverable(s) to make. Repeatable. Default: all four.")
    d.add_argument("--description", help="Shared focus prompt applied to deliverables that accept one.")
    d.add_argument("--source-id", action="append", default=[],
                   help="Limit generation to specific source ids. Repeatable.")
    # audio
    d.add_argument("--audio-format", choices=["deep-dive", "brief", "critique", "debate"])
    d.add_argument("--audio-length", choices=["short", "default", "long"])
    # flashcards
    d.add_argument("--flashcards-quantity", choices=["fewer", "standard", "more"])
    d.add_argument("--flashcards-difficulty", choices=["easy", "medium", "hard"])
    # infographic
    d.add_argument("--infographic-orientation", choices=["landscape", "portrait", "square"])
    d.add_argument("--infographic-detail", choices=["concise", "standard", "detailed"])
    d.add_argument("--infographic-style",
                   choices=["auto", "sketch-note", "professional", "bento-grid", "editorial",
                            "instructional", "bricks", "clay", "anime", "kawaii", "scientific"])
    # mindmap
    d.add_argument("--mindmap-instructions", help="Custom instructions for the mind map.")
    d.set_defaults(func=cmd_studio)

    h = sub.add_parser("handoff", help="Create a notebook from sources and pull a report.")
    h.add_argument("--project", required=True, help="Project name (used for vault paths).")
    h.add_argument("--title", help="Notebook title (defaults to project + date).")
    h.add_argument("--source", action="append", default=[],
                   help="A URL, file path, YouTube link, or inline text. Repeatable.")
    h.add_argument("--format", default="briefing-doc",
                   choices=["briefing-doc", "study-guide", "blog-post", "custom"])
    h.add_argument("--description", help="Custom report prompt (used with --format custom).")
    h.add_argument("--append", help="Extra instructions appended to non-custom formats.")
    h.add_argument("--timeout", type=int, default=300)
    h.set_defaults(func=cmd_handoff)

    a = sub.add_parser("ask", help="Ask an existing notebook a question.")
    a.add_argument("question")
    a.add_argument("--notebook", required=True, help="Notebook id (partial ok).")
    a.add_argument("--project", default="adhoc", help="Project name for vault path if saving.")
    a.add_argument("--source", action="append", default=[], help="Limit to source ids.")
    a.add_argument("--save", action="store_true", help="Save the answer into the vault.")
    a.set_defaults(func=cmd_ask)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except BridgeError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
