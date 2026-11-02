---
name: commons-media
description: Find, vet and file properly licensed media (charts, diagrams, photos, PDFs) from Wikimedia Commons into the vault with a ready-to-paste credit line. Use when the user says "find an image/chart/diagram for…", "illustrate this", "is there a free picture of…", "get media from Commons", "what license is this file", "credit line for…", or when an explainer/briefing/post needs a visual.
---

# commons-media

The Research Monster's picture desk. It wraps `integrations/commons_bridge.py`, which talks to
the Wikimedia Commons API (see `docs/wikimedia-commons-api.md` for the deep dive). Everything
it files carries its **license, author and credit line**, so nothing we publish is missing
attribution.

## Ground rules
- **Run it on the user's machine when possible.** `*.wikimedia.org` is blocked in the cloud
  sandbox; if a command fails with "Could not reach", say so and hand the user the command.
- **License policy before aesthetics.** Default `--license free`. If the output will be a
  derivative (infographic, annotated chart) or published under a different license, use
  `--license no-sa` (public domain + CC BY only). Never use `unknown`-license files.
- **Always surface the credit line** and any ⚠ flags (ShareAlike, non-copyright restrictions
  such as trademarks or personality rights). Commons gives no warranty — link the file page.
- **Download, don't hotlink.** `fetch` saves to `vault/50-assets/commons/` and verifies SHA-1.
- **Never invent what an image shows.** Describe only what Commons' description says, or what
  the user confirms after looking at it.
- Ask the user to set `COMMONS_CONTACT=you@example.org` once (Wikimedia's User-Agent policy).

## Steps

1. **Pin the need.** Which thread (`#fees`, `#settlement`, …) and what kind of visual: chart
   (`--filetype bitmap` or `--filetype drawing` for SVG), photo (`bitmap`), diagram (`drawing`),
   document (`--mime application/pdf`)? Output type decides the license policy (above).
2. **Search** (one `filetype` per query; try a Wikidata `--depicts Q…` or `--category` when
   keywords are noisy):
   ```bash
   python integrations/commons_bridge.py search "bitcoin price history" --filetype drawing --license no-sa
   python integrations/commons_bridge.py search "remittance" --depicts Q1341 --min-width 1200
   python integrations/commons_bridge.py category "Cryptocurrency charts" --subcats
   ```
   Add `--json` when you want to reason over the results rather than show them.
3. **Shortlist 3–5** for the user: title, what it shows, license flag (`PD`/`BY`/`SA`), size,
   file-page link. Lead with PD/CC BY. Call out anything ShareAlike or restricted.
4. **Inspect** the pick (adds categories, how many Wikimedia pages use it, structured data):
   ```bash
   python integrations/commons_bridge.py info "File:Bitcoin Price.webp" --sdc
   ```
5. **Fetch + file** once the user chooses:
   ```bash
   python integrations/commons_bridge.py fetch "File:Bitcoin Price.webp" \
     --project "Bitcoin vs Banks" --tag stability --why "Ten-year price series for the volatility thread" \
     --width 1600 --sdc
   ```
   This writes the file to `vault/50-assets/commons/` and a source note
   (`vault/10-sources/YYYYMMDD-commons-<slug>.md`, from `vault/_templates/media.md`) with
   frontmatter, the embedded image, the credit line, a reuse checklist and categories.
6. **Link it.** Add the note to the right thread in `vault/MOCs/Bitcoin-vs-Banks.md` and to any
   related source/synthesis notes. If the image feeds a NotebookLM deliverable, mention the
   credit line in that handoff.
7. **Report**: path of the file, path of the note, the credit line verbatim, and any ⚠ flags.

## Credit line format
`Author, [Title](file page), [License](deed), via Wikimedia Commons` — Markdown by default;
`credit "File:…" --format text|html` for other media. Public-domain/CC0 files don't legally
require it; include it anyway for provenance.

## Troubleshooting
- `403` → User-Agent rejected; set `COMMONS_CONTACT`.
- `429`/`503` → the bridge waits for `Retry-After` and retries; don't run several in parallel.
- "Could not reach commons.wikimedia.org" → sandbox block; run locally.
- `python integrations/commons_bridge.py doctor` checks connectivity, UA and vault paths.
- Offline demo of any command: add `--fixture integrations/tests/fixtures/search_bitcoin.json`.
