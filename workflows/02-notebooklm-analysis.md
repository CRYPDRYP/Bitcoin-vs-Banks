# Workflow 2 — NotebookLM Analysis

**Goal:** offload heavy reading/analysis to NotebookLM (Google's compute) and pull
the results back into the vault.

**Skill:** `notebooklm-handoff` · **Code:** `integrations/notebooklm_bridge.py`

## One-time setup
```bash
pip install -r requirements.txt
notebooklm login        # opens a browser — must be run in your own terminal
```

## Do it (automated)
Say: "Run a NotebookLM briefing on the sources tagged #fees."
Claude resolves the sources and runs:
```bash
python integrations/notebooklm_bridge.py handoff \
  --project "Bitcoin vs Banks" \
  --source <url-or-path> [--source ...] \
  --format briefing-doc \
  --append "Focus on like-for-like cost comparison."
```

Ask a follow-up against an existing notebook:
```bash
python integrations/notebooklm_bridge.py ask \
  --notebook <id> --project "Bitcoin vs Banks" --save \
  "Where do the sources disagree on remittance cost?"
```

## What happens
1. The bridge creates a notebook, adds your sources, and generates the artifact
   (briefing-doc / study-guide / blog-post / custom) — on Google's compute.
2. The result is written to `vault/40-outputs/bitcoin-vs-banks/` with frontmatter
   that links the sources and records the `notebook_id` for reuse.

## Manual fallback
If you can't automate (no login), the skill writes a prompt pack to
`vault/00-inbox/` for you to paste into NotebookLM, then files your pasted results
the same way. See `notebooklm-handoff/SKILL.md`, Path B.
