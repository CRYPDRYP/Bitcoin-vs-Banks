# Workflow 3 — Synthesize

**Goal:** turn captures + NotebookLM outputs into a cited synthesis and update the MOC.

**Skill:** `synthesize`

## Do it
Say: "Synthesize what we know about settlement finality."

## What happens
1. Claude collects the relevant notes and outputs.
2. It writes `vault/30-synthesis/YYYYMMDD-<topic>.md`: a thesis, supporting points
   (each linked to its source), a comparison table, and open questions.
3. It updates `vault/MOCs/Bitcoin-vs-Banks.md` — adds the synthesis link and refreshes
   "Current state".

## Tips
- Every claim links to a source note. Disagreement is represented, not smoothed over.
- Re-synthesize as new sources land; prefer updating over duplicating.
