# Workflow 1 — Capture

**Goal:** get raw material into the vault with zero friction so nothing is lost.

**Skill:** `research-capture`

## Do it
Say to Claude Code, in plain language:
- "Capture this: <url>"
- "Save this quote: …"
- "Add the PDF at ./papers/foo.pdf as a source"

## What happens
1. Claude classifies it (source vs. note).
2. It creates a note from `vault/_templates/` with frontmatter + tags.
3. It backlinks the note to `[[Bitcoin-vs-Banks]]` and related notes.
4. It tells you the path + tags, and offers to queue a NotebookLM handoff.

## Tips
- Capture liberally; curation happens later in synthesis.
- Reuse existing tags (see `vault/_memory/interests.md`).
