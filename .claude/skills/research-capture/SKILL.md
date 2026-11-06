---
name: research-capture
description: Capture a source (URL, PDF/file, quote, or stray idea) into the Obsidian vault as a structured note. Use whenever the user says "capture", "save this", "add this source", "remember this", or drops a link/quote they want filed for later research.
---

# research-capture

Turn anything the user drops — a URL, a file path, a quote, a half-formed idea —
into a well-formed note in the vault's memory layer.

## Where things go

- A **source** (URL, PDF, paper, video) → `vault/10-sources/`
- An **atomic note / idea / claim** → `vault/20-notes/`
- Anything you can't classify yet → `vault/00-inbox/` (process later)

## Steps

1. **Classify** the input: source vs. note. If it's a URL, fetch the title and a
   1–2 sentence description (use WebFetch if available). If it's a file path,
   record the path and type.
2. **Create the note** using the matching template in `vault/_templates/`
   (`source.md` or `note.md`). Fill the frontmatter:
   - `title`, `created` (today), `type`, `url`/`path`, `tags`, and `status: captured`.
   - Add 2–5 topical `tags` consistent with `vault/_memory/interests.md`.
3. **Filename**: `YYYYMMDD-<kebab-title>.md`.
4. **Link it**: add a backlink to the active MOC (e.g. `[[Bitcoin-vs-Banks]]`) and to
   any obviously related existing notes (search the vault first).
5. **Confirm** to the user with the path and the tags you assigned, and ask if it
   should be queued for a NotebookLM handoff.

## Notes

- Never invent facts about a source you haven't read. If you fetched it, summarize;
  if you didn't, mark `status: captured` and leave the summary blank.
- Keep tags lowercase and reuse existing ones rather than minting near-duplicates.
- This skill only files things. Analysis is the `notebooklm-handoff` skill's job.
