---
name: notebooklm-studio
description: Drive NotebookLM end-to-end via the notebooklm-py CLI — create notebooks, add sources (YouTube URLs, text, files), run analysis, and generate Studio deliverables (audio overview / podcast, mind map, flashcards, infographic). Use when the user says "make a podcast/audio overview", "generate a mindmap/flashcards/infographic", "build a NotebookLM notebook from these", "turn these sources into deliverables", or names any NotebookLM Studio output.
---

# notebooklm-studio

The full NotebookLM control surface for the Research Monster. Where `notebooklm-handoff`
focuses on briefings and Q&A, this skill covers the whole lifecycle and the **Studio
deliverables**: audio overview (podcast), mind map, flashcards, and infographic.

It wraps `integrations/notebooklm_bridge.py`, which drives the `notebooklm` CLI from the
**notebooklm-py** package (repo: https://github.com/teng-lin/notebooklm-py). Everything
runs on Google's compute, not Claude tokens, and results land in the vault.

## Prerequisites (once)

```bash
pip install -r requirements.txt          # installs notebooklm-py[browser]
python -m playwright install chromium     # browser engine used by login
notebooklm login                         # opens a browser — the USER must run this
                                         # in their own terminal; it can't run in a sandbox
```
If login says "Playwright not installed", run `pip install "notebooklm-py[browser]"`
then `python -m playwright install chromium`. If any command prints "Not authenticated",
stop and tell the user to run `notebooklm login`.

## Capabilities → commands

All commands are `python integrations/notebooklm_bridge.py <cmd> …`.

### 1. Create a notebook (and optionally add sources)
```bash
python integrations/notebooklm_bridge.py create \
  --project "Bitcoin vs Banks" \
  --source "https://youtu.be/VIDEO_ID" \
  --source "./papers/whitepaper.pdf" \
  --source "Plain text becomes an inline source too."
```
Prints the notebook id. Reuse it later with `--notebook <id>`.

### 2. Add sources to an existing notebook
Source type is auto-detected (YouTube → youtube, http(s) → url, existing path → file,
otherwise → inline text). No need to specify it.
```bash
python integrations/notebooklm_bridge.py add-source \
  --notebook abc123 --source "https://www.youtube.com/watch?v=..." --source "./report.pdf"
```

### 3. Generate Studio deliverables
One command makes any subset of the four. Omit `--deliverable` to make **all four**.
It will create a notebook from `--source` if you don't pass `--notebook`.
```bash
python integrations/notebooklm_bridge.py studio \
  --project "Bitcoin vs Banks" \
  --notebook abc123 \
  --deliverable audio --deliverable mindmap \
  --deliverable flashcards --deliverable infographic \
  --description "Focus on settlement finality and fee comparison."
```

Per-deliverable options (all optional — sensible defaults otherwise):

| Deliverable | Options |
|-------------|---------|
| `audio` (podcast) | `--audio-format {deep-dive,brief,critique,debate}` · `--audio-length {short,default,long}` |
| `flashcards` | `--flashcards-quantity {fewer,standard,more}` · `--flashcards-difficulty {easy,medium,hard}` |
| `infographic` | `--infographic-orientation {landscape,portrait,square}` · `--infographic-detail {concise,standard,detailed}` · `--infographic-style {auto,sketch-note,professional,bento-grid,editorial,instructional,bricks,clay,anime,kawaii,scientific}` |
| `mindmap` | `--mindmap-instructions "…"` |

Scope generation to specific sources with repeatable `--source-id <id>`.

### 4. Briefings / study guides / Q&A
For text reports and questions, use the `notebooklm-handoff` skill (`handoff` / `ask`
commands) — same bridge, same auth.

## What you get back

Each deliverable is written to `vault/40-outputs/<project>/<timestamp>-<kind>.md` as a
**card** with YAML frontmatter (`deliverable`, `status`, `notebook_id`, `artifact_id`,
`url`, `sources`, `tags`) plus:
- **audio** → a link to open the podcast in NotebookLM,
- **infographic** → an embedded image (`![]( )`) + link,
- **mindmap / flashcards** → a link to view, with the raw response folded in.

## Playbook for the agent

1. **Confirm auth** by running a command; if it reports not authenticated, stop and ask
   the user to `notebooklm login`.
2. **Resolve sources.** Pull YouTube URLs / file paths / text from the request or from
   `vault/10-sources/` (e.g. everything tagged `#fees`). Pass each as `--source`.
3. **Pick deliverables** the user asked for; if they say "everything" or "deliverables",
   make all four.
4. **Tailor `--description`** and style options to `vault/_memory/style-guide.md`
   (neutral tone, comparison-friendly, no hype).
5. **Run the command, then report** each output's vault path and any URL. Offer to
   `synthesize` the results or run a `learn` pass.
6. **Reuse notebooks.** Capture the printed notebook id and reuse it with `--notebook`
   for follow-up deliverables instead of re-uploading sources.

## Guardrails

- Audio generation can take a while; the bridge waits up to 20 minutes. Don't re-run on
  a perceived hang — check `notebooklm artifact list -n <id>` instead.
- Never commit `~/.notebooklm/` auth state. Never put secrets in source text.
- notebooklm-py is an **unofficial** community library; if a subcommand changes, check
  `notebooklm <group> --help` and the repo before assuming a flag exists.
