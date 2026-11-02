# Architecture

The Research Monster is four cooperating layers. Each does one job; the value comes
from how they feed each other.

```
            ┌──────────────────────────── you ────────────────────────────┐
            │  plain-language requests in Claude Code                       │
            ▼                                                               │
   ┌──────────────────┐                                                    │
   │   CLAUDE CODE     │  execution engine / orchestrator                  │
   │  + Skill Creator  │  (skills in .claude/skills/, built in natural lang)│
   └────────┬─────────┘                                                    │
            │ calls skills                                                 │
   ┌────────┴───────────────────────────────────────────────────┐         │
   │                                                             │         │
   ▼                          ▼                       ▼          ▼         │
research-capture     notebooklm-handoff          synthesize     learn      │
   │                          │                       │          │         │
   │                          ▼                       │          │         │
   │              ┌────────────────────────┐          │          │         │
   │              │      NOTEBOOKLM        │  analysis │          │         │
   │              │  (Google's compute via │  engine   │          │         │
   │              │  notebooklm_bridge.py) │           │          │         │
   │              └───────────┬────────────┘           │          │         │
   │                          │ artifacts              │          │         │
   ▼                          ▼                        ▼          ▼         │
 ┌───────────────────────────────────────────────────────────────────┐    │
 │                      OBSIDIAN VAULT  (memory layer)                 │    │
 │  00-inbox 10-sources 20-notes 30-synthesis 40-outputs MOCs _memory  │    │
 └───────────────────────────────┬───────────────────────────────────┘    │
                                  │  loaded at SessionStart                 │
                                  └─────────────────────────────────────────┘
```

## Layers

### 1. Claude Code — execution
Orchestrates everything. The user speaks plain language; Claude invokes the right
skill. Skills live in `.claude/skills/` and can be created/edited with **Skill Creator**.

### 2. Skill Creator — customization
Lets you mint new reusable skills in natural language. The shipped skills
(`research-capture`, `notebooklm-handoff`, `notebooklm-studio`, `synthesize`, `learn`,
`commons-media`, `rea-investigate`) are the starting set;
add your own as your workflow grows.

### 3. NotebookLM — analysis
Heavy reading, summarization, briefings, study guides, Q&A. Driven programmatically by
`integrations/notebooklm_bridge.py`, which wraps the `notebooklm` CLI (`notebooklm-py`).
Running analysis here spends **Google's** compute, not Claude tokens. Outputs are
written back into `vault/40-outputs/`.

### 3b. Wikimedia Commons — media
Illustrations for explainers and briefings. `integrations/commons_bridge.py` queries the
Commons Action API (search, `imageinfo`/`extmetadata` licensing, categories, structured data),
downloads the file into `vault/50-assets/commons/` and writes a source note with the license
and a credit line. Driven by the `commons-media` skill; API notes in `wikimedia-commons-api.md`.

### 3c. REA — evidence from shipped software (opt-in)
When a claim can only be settled by the binary, the `rea-investigate` skill drives the
external [REA](https://github.com/morluto/rea) MCP server (installed by the user, runs
locally) and files evidence-linked notes in `vault/20-notes/`. Not bundled; see
`integrations/rea/` and `rea-reverse-engineering-stack.md`.

### 4. Obsidian — memory
A plain-markdown vault. Everything the workflow produces is stored here, which makes it
(a) yours and local, (b) re-readable by Claude. The `_memory/` folder
(`profile.md`, `interests.md`, `style-guide.md`) is the distilled "smarts".

## The flywheel (why it gets smarter)

```
SessionStart hook  ──►  loads vault/_memory/ into context
        ▲                                   │
        │                                   ▼
   learn skill  ◄── corrections ──  you work the capture→analyze→synthesize loop
```

`.claude/hooks/load-memory.sh` runs on `SessionStart` and prints `vault/_memory/` +
the active MOC into the session. The `learn` skill writes updates back at the end.
Each pass distills more of your judgment into text the tooling reloads for free.

## Data flow contract
- NotebookLM artifacts land in `vault/40-outputs/<project>/` with frontmatter:
  `notebook_id`, `artifact_id`, `sources`, `project`, `tags`.
- Syntheses link to source notes via `[[wikilinks]]`; MOCs link to syntheses.
- Commons media land in `vault/50-assets/commons/` with a `type: source` / `source_type: media`
  note in `vault/10-sources/` carrying `license`, `license_class`, `attribution_required`, `sha1`
  and the credit line — never embed a file in an output without its note.
- X posts land in `vault/10-sources/` as `source_type: x-post` notes (via `integrations/x_capture.py`).
- REA findings land in `vault/20-notes/` with target SHA-256, Evidence IDs and limitations;
  exported Evidence bundles in `vault/50-assets/rea/` (never commit target bytes you can't redistribute).
- No secrets in the vault — auth lives in `~/.notebooklm/` (gitignored), never committed.
