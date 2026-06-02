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
Lets you mint new reusable skills in natural language. The four shipped skills
(`research-capture`, `notebooklm-handoff`, `synthesize`, `learn`) are the starting set;
add your own as your workflow grows.

### 3. NotebookLM — analysis
Heavy reading, summarization, briefings, study guides, Q&A. Driven programmatically by
`integrations/notebooklm_bridge.py`, which wraps the `notebooklm` CLI (`notebooklm-py`).
Running analysis here spends **Google's** compute, not Claude tokens. Outputs are
written back into `vault/40-outputs/`.

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
- No secrets in the vault — auth lives in `~/.notebooklm/` (gitignored), never committed.
