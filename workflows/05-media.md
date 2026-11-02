# Workflow 5 — Media (Wikimedia Commons)

**Goal:** illustrate explainers, briefings and posts with freely licensed charts, diagrams
and photos — each filed in the vault with its license and a ready-to-paste credit line.

**Skill:** `commons-media` · **Code:** `integrations/commons_bridge.py` ·
**Reference:** `docs/wikimedia-commons-api.md`

## One-time setup
```bash
export COMMONS_CONTACT="you@example.org"      # Wikimedia's User-Agent policy wants contact info
python integrations/commons_bridge.py doctor  # checks connectivity + vault paths
```
No extra dependencies: the bridge uses only the Python standard library.
Run it on your own machine — the cloud sandbox cannot reach *.wikimedia.org.

## Do it
Say to Claude Code:
- "Find a public-domain chart of bitcoin's price history for the stability thread."
- "Is there a free diagram of how card interchange fees flow?"
- "What's the license and credit line for File:Bitcoin.svg?"

Claude runs, roughly:
```bash
python integrations/commons_bridge.py search "bitcoin price" --filetype drawing --license no-sa
python integrations/commons_bridge.py info "File:Bitcoin Price.webp" --sdc
python integrations/commons_bridge.py fetch "File:Bitcoin Price.webp" \
  --project "Bitcoin vs Banks" --tag stability --why "…" --width 1600
```

## What happens
1. A CirrusSearch query hits Commons (`filetype:`, `filemime:`, `filew:`, `haswbstatement:`,
   `incategory:` keywords are available via flags).
2. Each hit comes back with license, author, credit, dimensions and a thumbnail, classified as
   `public-domain` / `attribution` / `share-alike` / `other` and filtered by your `--license`
   policy.
3. `fetch` downloads the original (or a server-rendered thumbnail at `--width`), verifies the
   SHA-1, saves it to `vault/50-assets/commons/`, and writes a source note in
   `vault/10-sources/` with frontmatter, embed, credit line, reuse checklist and categories.
4. You link the note into the MOC thread; the credit line travels with the image into any
   output.

## License policy cheat-sheet
| Flag | Includes | Use when |
|---|---|---|
| `--license pd` | Public domain, CC0 | You want zero attribution obligations |
| `--license no-sa` | PD + CC BY | The output is a derivative or has its own license |
| `--license free` (default) | PD + CC BY + CC BY-SA/GFDL + other free | Plain reuse with credit |
| `--license any` | everything incl. unknown | Research only — never publish from this |

## Tips
- SVGs (`--filetype drawing`) scale cleanly and rasterise to PNG thumbnails server-side.
- `info` shows how many Wikimedia pages use a file — a decent quality/vetting signal.
- Captures are one request at a time with a 0.35 s gap; that is intentional (200 req/min cap).
