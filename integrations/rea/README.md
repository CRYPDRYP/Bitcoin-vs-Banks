# integrations/rea — REA (Reverse Engineer Anything) for this repo

REA is an external, MIT-licensed MCP server (`morluto/rea`, npm `rea-agents`). Nothing here
vendors it; this folder holds the **opt-in wiring** and the checklist. Deep dive:
`../../docs/rea-reverse-engineering-stack.md`. Agent playbook: `.claude/skills/rea-investigate`.

## Setup (on your own machine — not in a cloud session)

```bash
node --version            # needs ^22.23.4 || ^24.22.1 || >=26.12.1
npx rea-agents@latest setup --client claude_code --dry-run   # preview the plan
npx rea-agents@latest setup --client claude_code             # approve, then restart Claude Code
npx rea-agents@latest doctor --client claude_code --skill --json
```
Setup writes `mcpServers.rea` to `~/.claude.json` and the `reverse-engineer-anything` skill to
`~/.claude/skills`, with backups. Deep native analysis also needs **one engine you install
yourself**: Ghidra (free, JDK 21+) or Hopper / IDA / Kuna (licensed). JavaScript/Electron and
.NET inspection need no engine. On Linux install `procps`.

### Keep it out of ordinary research sessions (recommended)
```bash
CLAUDE_CONFIG_DIR=~/.claude-rea npx rea-agents@latest setup --client claude_code
CLAUDE_CONFIG_DIR=~/.claude-rea claude          # a profile where REA is on
```

### Shrink the tool catalog
REA advertises ~170 tools. Scope them to what the job needs and use compact schemas:
```bash
npx rea-agents@latest setup --client claude_code \
  --tool-families session,native,direct,application
```
(`session` is always required for binaries. Add a family when a call fails with
"Tool … disabled".)

### Project-scoped alternative
`mcp.example.json` is a `.mcp.json` you can copy to the repo root. It is deliberately not
committed as `.mcp.json`: it would start REA in every session of this repo, including cloud
ones that cannot run it.

## Use
Ask in plain language with a local target available:
> "Use REA to find how `electrum` validates a payment request. Show the evidence."

The `rea-investigate` skill handles routing, evidence hygiene and filing results into the
vault. REA's guided prompts: `investigate_feature`, `compare_application_versions`,
`verify_reconstruction`, `trace_crash`, `audit_residual_unknowns`, `prepare_bounded_process_capture`.

## Authorization gate (non-negotiable)
Only targets you own or are authorized to examine. No DRM/license/anti-cheat circumvention,
no copying proprietary code/assets, no bypassing access controls. Runtime capture executes
the target: use a VM for anything untrusted. See REA's `DISCLAIMER.md`.

## Update / remove
```bash
npx rea-agents@latest setup          # refresh registration + skill after an update
claude mcp remove --scope user rea   # remove the registration (plus ~/.claude/skills/reverse-engineer-anything)
```
