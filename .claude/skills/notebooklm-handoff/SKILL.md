---
name: notebooklm-handoff
description: Hand a set of captured sources to NotebookLM for deep analysis (briefing docs, study guides, Q&A) and ingest the results back into the vault. Use when the user says "analyze these", "run a NotebookLM handoff", "generate a briefing", "summarize the sources tagged X", or wants heavy reading done without spending Claude tokens.
---

# notebooklm-handoff

Offload heavy reading and analysis to NotebookLM (Google's compute), then pull the
results back into `vault/40-outputs/`. There are two paths — prefer the automated one.

## Path A — Automated (preferred)

Uses `integrations/notebooklm_bridge.py`, which drives the `notebooklm` CLI.

1. **Check prerequisites.** Ensure `notebooklm-py` is installed (`pip install notebooklm-py`)
   and the user has run `notebooklm login` once (it opens a browser — interactive,
   so the user must do it in their own terminal). If `python integrations/notebooklm_bridge.py`
   reports "Not authenticated", tell the user to run `notebooklm login` and stop.
2. **Gather the sources.** Resolve the set the user means — e.g. all notes in
   `vault/10-sources/` matching a tag. Each source becomes a `--source` argument:
   a URL, a local file path, a YouTube link, or inline text.
3. **Run the handoff:**
   ```bash
   python integrations/notebooklm_bridge.py handoff \
     --project "<Active Project>" \
     --source <url-or-path> [--source ...] \
     --format briefing-doc \
     --append "<focus instructions tailored to vault/_memory/style-guide.md>"
   ```
   Formats: `briefing-doc` (default), `study-guide`, `blog-post`, `custom`
   (with `--description "<full prompt>"`).
4. **Report back.** The bridge writes a markdown artifact into
   `vault/40-outputs/<project>/` with frontmatter linking the sources and notebook id.
   Tell the user the path and offer to run `synthesize` next.
5. **For Q&A** against an existing notebook:
   ```bash
   python integrations/notebooklm_bridge.py ask --notebook <id> \
     --project "<Active Project>" --save "<question>"
   ```

## Path B — Manual (fallback when login/automation isn't available)

1. Write a **prompt pack** to `vault/00-inbox/notebooklm-prompt-<date>.md`: the list
   of sources, plus 3–6 questions/prompts tailored to the user's interests and style.
2. Tell the user to: create a NotebookLM notebook, add those sources, and paste each
   prompt.
3. When they paste the output back, file it with `write_output`-style frontmatter into
   `vault/40-outputs/<project>/` so the rest of the loop treats it identically.

## Always

- Tailor prompts to `vault/_memory/style-guide.md` (tone, depth, format the user likes).
- Record the `notebook_id` in the output frontmatter so future runs can reuse the notebook.
