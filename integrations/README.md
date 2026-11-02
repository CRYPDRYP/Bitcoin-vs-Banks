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

### Studio deliverables (audio, mindmap, flashcards, infographic)
```bash
# Create a notebook and add sources (YouTube / file / text auto-detected):
python notebooklm_bridge.py create --project "Bitcoin vs Banks" \
  --source "https://youtu.be/VIDEO_ID" --source ./papers/whitepaper.pdf

# Add more sources later:
python notebooklm_bridge.py add-source --notebook abc123 --source ./report.pdf

# Generate any subset of deliverables (omit --deliverable to make all four):
python notebooklm_bridge.py studio --project "Bitcoin vs Banks" --notebook abc123 \
  --deliverable audio --deliverable mindmap \
  --deliverable flashcards --deliverable infographic \
  --audio-format deep-dive --infographic-style professional \
  --description "Focus on settlement finality and fee comparison."
```
Each deliverable is written to `vault/40-outputs/<project>/` as a card with frontmatter
(`deliverable`, `status`, `notebook_id`, `artifact_id`, `url`, `sources`). See the
`notebooklm-studio` skill for the agent-facing playbook.

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

## `commons_bridge.py`

Finds, vets and files **licensed media** from Wikimedia Commons so outputs can be
illustrated with a correct credit line. Standard library only; built on the API deep dive in
`../docs/wikimedia-commons-api.md` (verified live 2026-11-02).

### Setup
```bash
export COMMONS_CONTACT="you@example.org"   # goes into the User-Agent (Wikimedia policy)
python commons_bridge.py doctor            # connectivity + vault paths
```
Run from your own machine — `*.wikimedia.org` is blocked in the cloud sandbox.

### Commands
```bash
# search Commons files; CirrusSearch keywords exposed as flags
python commons_bridge.py search "bitcoin atm" --filetype bitmap --min-width 1200 --license no-sa
python commons_bridge.py search "price chart" --depicts Q131723 --filetype drawing --json

# browse a category (files) and its subcategories
python commons_bridge.py category "Cryptocurrency charts" --subcats

# everything about one file, incl. Structured Data on Commons
python commons_bridge.py info "File:Bitcoin Price.webp" --sdc --resolve-labels

# just the attribution line, as md | text | html
python commons_bridge.py credit "File:Bitcoin.svg" --format text

# download (original, or a server-rendered --width thumbnail) + write the source note
python commons_bridge.py fetch "File:Bitcoin Price.webp" \
  --project "Bitcoin vs Banks" --tag stability --why "Ten-year price series" --width 1600 --sdc
```
`--license` policy on every command: `pd` · `no-sa` (PD + CC BY) · `free` (default) · `attribution` · `any`.
`--fixture <recorded.json>` replays a saved API response for offline demos.

### What it writes
- Media → `vault/50-assets/commons/<slug>[-<width>px].<ext>` (originals SHA-1-verified against the API).
- Source note → `vault/10-sources/YYYYMMDD-commons-<slug>.md` (template: `vault/_templates/media.md`)
  with license frontmatter, embed, credit line, reuse checklist, categories and structured data.

### Etiquette baked in
Descriptive User-Agent with contact, serial requests spaced ≥ 0.35 s (2026 cap is 200 req/min
for UA-only clients), gzip, `maxlag=5`, `Retry-After`-aware backoff on 429/503, `utm_*`
tracking parameters stripped from stored URLs.

### Tests
```bash
python -m unittest discover -s integrations/tests -v     # 27 tests, no network
```
Fixtures in `tests/fixtures/` are real responses recorded on 2026-11-02.
