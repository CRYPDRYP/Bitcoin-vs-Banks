# Architecture

The Research Monster is five cooperating layers. Each does one job; the value comes
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
   ▼                ▼                    ▼            ▼              ▼      │
research-capture notebooklm-handoff   synthesize  everygen-produce  learn   │
   │                │                    │            │              │      │
   │                ▼                    │            ▼              │      │
   │   ┌────────────────────────┐        │  ┌──────────────────────┐ │      │
   │   │      NOTEBOOKLM        │ analysis│  │      EVERYGEN        │ │      │
   │   │  (Google's compute via │ engine  │  │ (remote MCP, OAuth;  │ │      │
   │   │  notebooklm_bridge.py) │         │  │  Seedance/Kling/…)   │ │      │
   │   └───────────┬────────────┘         │  └──────────┬───────────┘ │      │
   │               │ artifacts            │             │ cards       │      │
   ▼               ▼                      ▼             ▼             ▼      │
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

### 4. Everygen — production
Short-form video, images, voiceovers and captions from the vault's research. Everygen is a
remote MCP server (`.mcp.json` → `https://everygen.ai/api/mcp`, OAuth 2.1 with PKCE via
`/mcp`) that fronts Seedance, Kling, Gemini Omni, MiniMax, Grok Imagine, Nano Banana and
GPT Image on a credit budget. The `everygen-produce` skill drives it (brief → stills →
cheap drafts → approved finals → voiceover → captions) and
`integrations/everygen_cards.py` writes each generation back to `vault/40-outputs/` as a
card. Rendering spends **Everygen credits**, not Claude tokens.

### 5. Obsidian — memory
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
every MOC in `vault/MOCs/` into the session. The `learn` skill writes updates back at the end.
Each pass distills more of your judgment into text the tooling reloads for free.

## Data flow contract
- NotebookLM artifacts land in `vault/40-outputs/<project>/` with frontmatter:
  `notebook_id`, `artifact_id`, `sources`, `project`, `tags`.
- Everygen cards land in `vault/40-outputs/<project>/` with frontmatter:
  `engine: everygen`, `deliverable`, `model`, `credits`, `url`, `sources`, `status`.
  Briefs sit beside them (`type: brief`) and link every card they produced.
- Syntheses link to source notes via `[[wikilinks]]`; MOCs link to syntheses and briefs.
- No secrets in the vault — NotebookLM auth lives in `~/.notebooklm/` (gitignored) and
  Everygen OAuth tokens live in Claude Code's credential store; neither is committed.
