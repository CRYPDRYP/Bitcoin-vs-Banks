# Workflow 4 — Learn (the flywheel)

**Goal:** make the system smarter every session by writing what it learned back into
the memory layer.

**Skill:** `learn`

## Do it
At the end of a session say: "Update memory with what we learned today."

## What happens
1. Claude reviews the session — especially your corrections (the strongest signal).
2. It updates `vault/_memory/`:
   - `profile.md` — durable facts about how you work.
   - `interests.md` — re-ranked topics/threads.
   - `style-guide.md` — how you want analysis delivered.
3. It confirms the 2–4 things it learned so you can correct them.

## Why this matters
The `SessionStart` hook (`.claude/hooks/load-memory.sh`) loads `vault/_memory/` into
context at the start of **every** session. So next time, Claude already knows your
priorities and style — you stop re-explaining yourself. That's the compounding loop.
