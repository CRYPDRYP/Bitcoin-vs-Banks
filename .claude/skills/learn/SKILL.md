---
name: learn
description: Update the vault's memory layer (_memory/profile.md, interests.md, style-guide.md) at the end of a session so the system gets smarter every time. Use when the user says "update memory", "remember that I...", "learn from this session", or at the natural end of a research session.
---

# learn

This is the skill that makes the Research Monster *compound*. After a session, write
back what you learned about the user so the next `SessionStart` hook loads it
automatically.

## What to update

- **`vault/_memory/profile.md`** — durable facts about how the user works: their goals,
  their domain expertise, recurring constraints, decisions they've made.
- **`vault/_memory/interests.md`** — the topics/tags they keep returning to, ranked by
  recent activity. Promote tags that appeared this session; note new sub-threads.
- **`vault/_memory/style-guide.md`** — how they want analysis delivered: tone, length,
  format (tables vs prose), level of hedging, citation density, things to avoid.

## Steps

1. **Review the session.** What did the user capture, ask, accept, or reject? What
   corrections did they make to your output? Corrections are the strongest signal.
2. **Diff against current memory.** Only add or change what's genuinely new or changed.
   Keep the files tight — this is loaded into context every session, so prune stale or
   redundant lines.
3. **Write concise, declarative bullets.** Each line should be independently useful when
   read cold at the start of a future session. Date significant changes.
4. **Never store secrets** (API keys, tokens, passwords) in the memory layer.
5. **Confirm** the 2–4 things you learned so the user can correct you — then those
   corrections become the next thing you learn.

## Principle

The expensive resource is the user's judgment. Capture it as plain text so neither you
nor the user has to re-derive it next time.
