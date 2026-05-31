---
name: synthesize
description: Read the vault's notes and NotebookLM outputs on a topic and write a synthesis note plus update the relevant Map of Content (MOC). Use when the user says "synthesize", "tie this together", "what do we know about X", "update the MOC", or "write up the argument".
---

# synthesize

Turn raw captures and NotebookLM artifacts into a coherent, cited synthesis — the
part that actually advances the research.

## Steps

1. **Scope it.** Identify the topic/tag/question. Collect the relevant notes from
   `vault/10-sources/`, `vault/20-notes/`, and `vault/40-outputs/`.
2. **Read for claims and tensions.** Extract the key claims, the supporting evidence,
   and the disagreements between sources. Note what's still unknown.
3. **Write the synthesis** to `vault/30-synthesis/YYYYMMDD-<topic>.md` using
   `vault/_templates/synthesis.md`:
   - A 3–5 sentence thesis/answer up top.
   - Supporting points, each with `[[wikilinks]]` to the source notes they rest on.
   - A "Counterpoints / open questions" section — do not paper over disagreement.
   - Tailor depth and tone to `vault/_memory/style-guide.md`.
4. **Update the MOC** in `vault/MOCs/` (e.g. `Bitcoin-vs-Banks.md`): add a link to the
   new synthesis under the right heading and update the "Current state" summary.
5. **Confirm** with the user: the synthesis path, what it concludes, and the biggest
   remaining open question.

## Rules

- Every non-obvious claim must link to a source note. No floating assertions.
- Represent disagreement honestly; the system's value is judgment, not cheerleading.
- Prefer updating an existing synthesis over creating a near-duplicate.
