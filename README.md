# 🧠 Research Monster

### Claude Code + Skill Creator + NotebookLM + Obsidian — a research workflow that gets smarter every time you use it.

Most research tools start over from zero with every session. This one **compounds**.
Every source you capture, every analysis NotebookLM produces, and every decision you make
gets written back into a local Obsidian vault. The next time you sit down, Claude Code reads
that vault first — so it already knows what you care about, how you think, and how you want
your analysis delivered.

The running example in this repo is **Bitcoin vs Banks**, but the framework is topic-agnostic.

---

## The Stack and Why It Works

Four tools. Each one handles a different layer of the problem.

| Layer | Tool | Job |
|-------|------|-----|
| **Execution** | **Claude Code** | Runs commands, calls skills, manages files, and orchestrates the entire pipeline. You talk to it in plain language; it does the work. |
| **Customization** | **Skill Creator** | A Claude Code plugin that lets you build reusable skills in natural language. Describe what you want, it generates and installs the skill. No programming required. |
| **Analysis** | **NotebookLM** | Google's AI research tool. Reads your sources and generates deep analysis, summaries, infographics, flashcards, and podcast scripts. When Claude Code offloads processing to NotebookLM, it spends *Google's* compute, not your Claude tokens. |
| **Memory** | **Obsidian** | A local, markdown-based knowledge system that stores everything the workflow produces. Over time Claude Code reads these files and learns how you think, what you care about, and how you want analysis delivered. |

---

## The Compounding Loop

```
        ┌─────────────────────────────────────────────────────────┐
        │                                                         │
        ▼                                                         │
  ┌──────────┐   ┌──────────────┐   ┌─────────────┐   ┌──────────┐
  │ CAPTURE  │──▶│  NOTEBOOKLM  │──▶│ SYNTHESIZE  │──▶│  LEARN   │
  │ sources  │   │   analysis   │   │  into MOCs  │   │ profile  │
  └──────────┘   └──────────────┘   └─────────────┘   └──────────┘
       │               │                  │                │
       └───────────────┴──────────────────┴────────────────┘
                            │
                    Obsidian vault (memory)
                            │
              read first at the start of every session
```

1. **Capture** — drop a URL, PDF, quote, or stray idea. Claude files it into the vault with
   structured frontmatter and tags. → `research-capture` skill
2. **NotebookLM handoff** — Claude bundles the relevant sources and writes a prompt pack you
   paste into NotebookLM. You paste the analysis back; Claude ingests it as an artifact. → `notebooklm-handoff` skill
3. **Synthesize** — Claude reads your notes + the NotebookLM outputs and writes a synthesis
   note and updates the relevant Map of Content (MOC). → `synthesize` skill
4. **Learn** — at the end of a session, Claude updates the memory layer (`_memory/`) with what
   it learned about your interests and style. → `learn` skill

The memory layer is what makes it a *monster*: it's loaded into context automatically at the
start of every session via a `SessionStart` hook.

---

## Repository Layout

```
.
├── .claude/
│   ├── settings.json          # registers the SessionStart memory hook
│   ├── hooks/
│   │   └── load-memory.sh      # prints the memory layer into context
│   └── skills/                 # the workflow skills
│       ├── research-capture/
│       ├── notebooklm-handoff/  # briefings, study guides, Q&A
│       ├── notebooklm-studio/   # audio / mindmap / flashcards / infographic
│       ├── synthesize/
│       └── learn/
├── vault/                      # the Obsidian memory layer (open this as a vault)
│   ├── 00-inbox/               # unprocessed captures land here
│   ├── 10-sources/             # one note per source
│   ├── 20-notes/               # your atomic notes
│   ├── 30-synthesis/           # synthesized arguments & comparisons
│   ├── 40-outputs/             # NotebookLM-generated artifacts
│   ├── MOCs/                   # Maps of Content (entry points)
│   ├── _templates/             # note templates
│   └── _memory/                # profile / interests / style — the "smarts"
├── workflows/                  # human-readable runbooks for each step
└── docs/architecture.md        # how the pieces fit together
```

---

## Quickstart

1. **Clone & open the vault.** Clone this repo locally and open the `vault/` folder as an
   Obsidian vault.
2. **Install the NotebookLM engine & log in** (interactive — needs a browser, so run it on
   your own machine, not in a cloud session):
   ```bash
   pip install -r requirements.txt
   notebooklm login
   python integrations/notebooklm_bridge.py doctor   # ✓ everything green = ready
   ```
3. **Start a Claude Code session** in this repo. The `SessionStart` hook loads your memory
   layer automatically, so Claude greets you already knowing your active project.
   (Skill Creator is optional — the skills in `.claude/skills/` work as-is.)
4. **Run the loop.** In plain language:
   - "Capture this article: <url>"
   - "Prep a NotebookLM handoff for the sources tagged #consensus"
   - "Make an audio overview, mindmap, flashcards, and infographic from these sources"
   - "Synthesize what we have on transaction fees"
   - "Update memory with what we learned today"

See [`workflows/`](workflows/) for the detailed runbook of each step and
[`docs/architecture.md`](docs/architecture.md) for the full design.

---

## Why "gets smarter every time"?

Because the expensive part of research — *your judgment* — gets captured as plain text the
tooling can re-read. Claude doesn't re-derive your priorities each session; it loads them.
NotebookLM does the bulk reading on Google's dime. Obsidian keeps it all local and yours.
The result is a flywheel: the more you use it, the less you have to re-explain.
