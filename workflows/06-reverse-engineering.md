# Workflow 6 — Reverse engineering with REA

**Goal:** when a research claim depends on what shipped software *actually does*, open the
artifact with REA, get evidence (not vibes), and file it so the vault remembers.

**Skill:** `rea-investigate` · **Setup:** `integrations/rea/README.md` ·
**Reference:** `docs/rea-reverse-engineering-stack.md`

## One-time setup (your machine, not the cloud)
```bash
npx rea-agents@latest setup --client claude_code     # review plan → approve → restart Claude Code
# plus ONE native engine for binaries: Ghidra (free, JDK 21+), or Hopper/IDA/Kuna (licensed)
```
Prefer an isolated profile so REA's ~170 tools don't load in ordinary research sessions:
```bash
CLAUDE_CONFIG_DIR=~/.claude-rea npx rea-agents@latest setup --client claude_code
CLAUDE_CONFIG_DIR=~/.claude-rea claude
```

## Do it
Say, with the target available locally:
- "Use REA to find how Electrum builds a BIP-21 payment request. Show the evidence."
- "Compare the 27.0 and 28.0 Bitcoin Core binaries for changes in fee estimation."
- "Trace the IPC path behind the 'send' button in this Electron wallet."

## What happens
1. The skill checks the **authorization gate** (software you own / are allowed to examine)
   and whether REA is even needed (source repos don't need it).
2. REA routes by target (`open_binary`, `analyze_javascript_application`,
   `inspect_android_package`, …) and returns summary-first results with Evidence IDs.
3. Claude separates observed / inferred / unknown, follows instructions over pseudocode,
   and stops when the checklist is answered or bounded.
4. Findings land in `vault/20-notes/` with target hash, Evidence IDs and limitations;
   exported bundles in `vault/50-assets/rea/`; the MOC thread gets the link.

## The loop (if you rebuild something)
`target → REA evidence → obligation ledger → clean-room implementation → oracle → retry`
— REA's `build_reconstruction_obligation_ledger` + your own reference tests, as in the
DX-Ball showcase (3,205 behaviour cases, 63 matching compiled bytes).

## Rules
- Only authorized targets. No DRM/license/anti-cheat work. Proprietary banking apps are
  usually off-limits by their ToS; open-source wallets and nodes are fine.
- Runtime capture executes the target: VM for anything untrusted.
- Don't commit target bytes or Evidence bundles you can't redistribute.
