# integrations/

Code that connects the Research Monster to external engines.

## `notebooklm_bridge.py`

Drives the `notebooklm` CLI (from `notebooklm-py`) so NotebookLM analysis can be
automated from Claude Code. See `../workflows/02-notebooklm-analysis.md` for the full
runbook.

### Setup
```bash
pip install -r ../requirements.txt   # or: pip install notebooklm-py
notebooklm login                     # interactive; opens a browser. Run in your terminal.
```

### Commands
```bash
# Create a notebook from sources and pull back a report:
python notebooklm_bridge.py handoff \
  --project "Bitcoin vs Banks" \
  --source https://example.com/article \
  --source ./papers/whitepaper.pdf \
  --format briefing-doc \
  --append "Compare settlement finality and fees."

# Ask an existing notebook a question and save the answer into the vault:
python notebooklm_bridge.py ask \
  --notebook abc123 --project "Bitcoin vs Banks" --save \
  "Where do the sources disagree on remittance cost?"
```

Report formats: `briefing-doc` (default), `study-guide`, `blog-post`, `custom`
(pair with `--description "<full prompt>"`).

### How it works
- Wraps the CLI via `subprocess` with `--json --quiet` and parses the result.
- Auto-detects each source type (url / youtube / file / text).
- Writes artifacts to `vault/40-outputs/<project>/` with frontmatter that records the
  `notebook_id` (so you can reuse the notebook) and links the sources.
- Surfaces a clear message and exits non-zero if you aren't logged in.

### Notes
- Authentication state is stored by the CLI under `~/.notebooklm/` — **never committed**.
- `notebooklm-py` is an unofficial, community library for automating NotebookLM; the
  bridge depends only on its documented CLI surface so it degrades gracefully.
