# REA and the agent reverse-engineering stack — deep dive

> Field notes on **REA (Reverse Engineer Anything)**, `morluto/rea`, and the 19 companion
> repos a viral X post bundled with it. Researched from the primary sources on
> **2026-11-02** (repo at commit `93b8b82`, npm `rea-agents` 6.8.0) for the Research Monster.
> The post that triggered this is filed in the vault as
> `vault/10-sources/*-x-robiartec-*.md`.

**One-paragraph answer.** REA is an MIT-licensed, local-only CLI + MCP server (npm
`rea-agents`) that gives a coding agent such as Claude Code typed tools for inspecting
shipped software without its source: native binaries (through Ghidra, Hopper, IDA or Kuna),
JavaScript/Electron bundles, .NET assemblies, Android APKs, firmware, captures and live
browser/process behaviour. Every result carries its *Evidence* (offsets, instructions,
xrefs, bytes) and its limitations, and a "reconstruction obligation ledger" turns findings
into checkable claims that a clean-room re-implementation must satisfy. It went #1 on
GitHub Trending in October 2026, the README now claims 400k stars, and it is genuinely
useful — but the X post overstates authorship (17 of its "20 repos from the creator of REA"
are other people's tools) and invents terminology (`SPEC.md` is not a REA concept).

---

## 1. The post, decoded

`@robiartec`, 2026-11-01, Spanish, ~155k views. Claim: "the creator of REA just dropped 20
GitHub repos to build yourself a reverse-engineering studio", grouped in five blocks, plus a
loop: *binary → REA → SPEC.md → rebuild → oracle → retry*.

| Block | Repos named | Verified status |
|---|---|---|
| 01 Analysis core | `morluto/rea`, `NationalSecurityAgency/ghidra`, `LaurieWired/GhidraMCP`, `mrexodia/ida-pro-mcp` | Only `rea` is by morluto. Ghidra is the NSA's; the two MCP bridges are third-party and both are listed in morluto's awesome list. |
| 02 Mobile & apps | `skylot/jadx`, `iBotPeaches/Apktool`, `frida/frida`, `icsharpcode/ILSpy` | All third-party, all in the awesome list. REA integrates JADX, Apktool and Frida as *providers*. |
| 03 Binaries & low level | `radareorg/radare2`, `x64dbg/x64dbg`, `WerWolv/ImHex`, `angr/angr` | Third-party, all in the awesome list. REA can use Rizin/objdump offline; radare2 itself has its own MCP (`radareorg/radare2-mcp`). |
| 04 Network & execution | `mitmproxy/mitmproxy`, `dnSpyEx/dnSpy`, `rizinorg/rizin`, `EpicGames/raddebugger` | Third-party. REA ships a mitmproxy bridge and a Rizin provider. `raddebugger` appears in **neither** curated list. |
| 05 Rebuild & verify | `zhuyansen/awesome-ai-reverse-engineering` ("122 repos, scored"), `morluto/awesome-reverse-engineering`, "REA flows", "clean-room loop: SPEC.md, oracles, checks until it matches" | The first list is by Agent Skills Hub, not morluto, and says 117 repos today. The second *is* morluto's. "REA flows" = REA's six guided MCP prompts. "SPEC.md" does not exist in REA; the real artefacts are Evidence bundles and the **reconstruction obligation ledger**. |

So: two of twenty repos are morluto's (`rea`, `awesome-reverse-engineering`). The rest is a
reasonable, if generic, RE toolbox. The useful part of the post is the *loop*, which does
match how REA's showcases work (§4).

## 2. What REA actually is

| Fact | Value (verified) |
|---|---|
| Repo / license | https://github.com/morluto/rea · MIT (third-party tools keep their own licenses) |
| Package | npm `rea-agents` 6.8.0 (2026-10-25); 34 releases since 0.2.1 on 2026-07-12; bins `rea` and `rea-agents` |
| Runtime | Node.js `^22.23.4 \|\| ^24.22.1 \|\| >=26.12.1` (23 and 25 unsupported) + npm; Linux needs a procps-compatible `ps` |
| Distribution | `npx rea-agents setup`; Claude Code plugin marketplace (`/plugin marketplace add morluto/rea`); Codex plugin; MCP Registry `io.github.morluto/rea`; skill-only via `npx skills add morluto/rea --skill reverse-engineer-anything` |
| Locality | Analysis runs on your machine; only tool results go to your model provider |
| Reception | HN front page (814 points / 340 comments, mid-Oct 2026); GitHub Trending #1; README thanks for 400,000 stars |
| Website | https://rea.tools (guides, showcases) · Discord |

### 2.1 What it can look at (from the README's target table)
Native binaries (pseudocode, assembly, strings, symbols, xrefs via **Hopper / Ghidra / IDA /
Kuna**; objdump/Rizin for offline layout), Go and Rust build metadata, GPU code objects,
GGUF/safetensors model files, Unity IL2CPP metadata, Godot PCK, PE certificates/imports,
ELF notes, Apple `.ips` crashes, Linux kernel modules, Erlang BEAM, WASM, EVM bytecode,
SQLite files, Linux core dumps (pwntools/GDB), **JavaScript/Electron** (modules, imports,
source maps, routes, IPC — no native engine needed), websites (Chrome-family browser),
HAR/SAZ/mitmproxy captures, **.NET** assemblies (static, no engine), **Android** APKs
(headless JADX + JDK), APK signatures, Android devices (adb), JEB projects, Apktool
resources, Flutter apps, firmware (Binwalk/Unblob), pcap (TShark), logic-analyzer
recordings (sigrok), packages/bundles, process behaviour (PTY capture), PyInstaller.

Static JavaScript and .NET inspection never execute the target. Runtime capture does, under
your user account — the docs are explicit that "authorization to inspect an artifact does not
necessarily authorize execution".

### 2.2 Shape of the MCP surface
- **~172 tools** on `main` (measured by the project at commit `04089d5be`; an independent
  write-up counted 126 on 2026-10-08, so it is growing fast). Full input schemas weigh
  ~496 KB (~120k tokens) if a client sends them every turn; `compact` ~290 KB.
- Tools are grouped in **families** (`session`, `application`, `direct`, `native`,
  `artifact`, `firmware`, `browser`, `pcap`, `javascript-runtime`, `android`, `adb`,
  `apktool`, `frida`, `jeb`, `flutter`, `managed`, `electron`, …). `REA_MCP_TOOL_FAMILIES`
  scopes a registration; `session` is always needed for binaries.
- **Six guided prompts** (the "REA flows"): `investigate_feature`,
  `compare_application_versions`, `verify_reconstruction`, `trace_crash`,
  `audit_residual_unknowns`, `prepare_bounded_process_capture`.
- Key tools you will see: `open_binary`, `binary_session`, `analyze_function`
  (summary-first; dossier retained under `parent_evidence_id`), `trace_call_path`,
  `read_bytes`, `batch_decompile`, `analyze_javascript_application`,
  `trace_application_feature`, `inspect_artifact`, `inspect_android_package`,
  `inspect_managed_artifact`, `capture_browser_scenario`, `export_evidence_bundle`,
  `build_reconstruction_obligation_ledger`, `match_native_functions`, `reset_investigation`.
- Env knobs: `REA_MCP_INPUT_SCHEMA_PROFILE=compact|full`,
  `REA_MCP_OUTPUT_SCHEMA_PROFILE=compact|off`, `REA_GHIDRA_STARTUP_TIMEOUT_MS`,
  `REA_HOPPER_STARTUP_TIMEOUT_MS`, `REA_JADX_MCP_JAR`, `REA_JEB_MCP_URL`.

### 2.3 Design principles (AGENTS.md + skill)
- **Evidence-first.** Distinguish observations, derivations, inferences and unknowns.
  Every conclusion cites Evidence IDs and states coverage limits; "never imply that static
  analysis observed execution".
- **Summary-first.** Default replies are summaries; page the retained dossier instead of
  dumping 30k lines of pseudocode into context.
- **Fail-closed.** Ghidra runs on ephemeral databases and never modifies bytes; IDA is
  read-only; setup is additive, idempotent, backs up configs, never installs Node/Java/Ghidra.
- **Bring your own engine.** REA grants no license to IDA, Hopper or JEB; cracked tools are
  explicitly unauthorized.

## 3. The toolbox around it (what each companion repo is for)

| Tool | Role in an agent-driven RE study | REA relationship |
|---|---|---|
| **Ghidra** (NSA, Apache-2.0) | Free disassembler/decompiler, headless-capable; the default native engine | Provider (`docs/ghidra-provider.md`); needs JDK 21+; cold start on big binaries can take minutes, raise `REA_GHIDRA_STARTUP_TIMEOUT_MS` |
| **GhidraMCP** (LaurieWired) | Ghidra plugin + MCP server (decompile, list, rename) | Alternative/complement; don't run both bridges on one Ghidra project |
| **ida-pro-mcp** (mrexodia) | MCP for IDA Pro | REA has its own IDA provider with an optional native MCP bridge; Hex-Rays also ships an official `ida-mcp` |
| **jadx** | APK → Java | REA runs headless JADX for `inspect_android_package` |
| **Apktool** | Decode/rebuild APK resources | Provider for resource analysis |
| **Frida** | Dynamic instrumentation | Provider (`instrument-with-frida`) |
| **ILSpy / dnSpy** | .NET decompile / debug | REA's managed analysis is static and engine-free; use these for interactive work |
| **radare2 / rizin** | Terminal RE frameworks | Rizin is a supported offline provider; radare2 has its own MCP |
| **x64dbg / raddebugger** | Windows debuggers | Not integrated; manual tools |
| **ImHex** | Hex editor with pattern language | Manual; good for file-format work REA's artifact tools don't cover |
| **angr** | Symbolic execution | Not integrated; for constraint solving beyond REA's scope |
| **mitmproxy** | Intercepting proxy | REA bridge for native mitmproxy captures; HAR/SAZ also accepted |
| **awesome-reverse-engineering** (morluto) | Curated map "by task" | Where REA's own author points for everything REA doesn't do |
| **awesome-ai-reverse-engineering** (Agent Skills Hub) | 117 agent-RE repos, auto-graded by a model | Discovery; grading is automated, treat as a hint |

## 4. The loop the post describes, in REA's own terms

```
target ──► REA tools ──► Evidence (IDs, bytes, xrefs) ──► obligation ledger ──► clean-room impl ──► oracle ──► retry
```

1. **Investigate.** Agent asks a narrow question; REA routes by target type (`open_binary`,
   `analyze_javascript_application`, `inspect_android_package`, …) and returns evidence.
   In the DX-Ball showcase the first decompiler view was wrong (`FUN_00406400(void)` calling
   `__ftol`), and the *instructions* (`MOV EAX,[EBP+8]; FILD …`) exposed the missing input —
   exactly the "evidence over pseudocode" point.
2. **Ledger.** `build_reconstruction_obligation_ledger` turns authenticated Evidence into a
   deterministic list of claims the re-implementation must satisfy (CLI parsing behaviour,
   protocol handler, persistence migration, native ABI…). Static facts only create
   *candidates*; an obligation closes only with an owner, fixtures and a passing verifier of
   comparable authority. This is the closest real thing to the post's "SPEC.md".
3. **Rebuild** with normal coding tools, separating observed behaviour from design choices.
4. **Oracle.** Independent checks: DX-Ball runs the original x86 function in 3,205 cases
   against the C and replays the pinned VC4.0 compiler to match all 63 function bytes
   (`docs/ORACLES.md`, `BUILD_MATCHING.md` in `N0zoM1z0/dx-ball`); the project-level ledger
   reports 55 maintained C functions, 45,380 comparisons, 33 byte-matching functions.
   `match_native_functions` and `compare_functions` support this across builds.
5. **Retry** until the ledger closes; `audit_residual_unknowns` keeps unknowns explicit.

The clean-room caveat from REA's own docs: scoping which *sessions* see REA is not
clean-room separation. "The model that saw the original never writes the code" needs a
separate account or container with filesystem/network restrictions.

## 5. Integrating REA with this repo's Claude Code setup

Three routes, pick one (never two — you'd get two `rea` servers):

| Route | Command | Scope | Notes |
|---|---|---|---|
| **Guided setup** (recommended) | `npx rea-agents@latest setup --client claude_code` | User-level: `mcpServers.rea` in `~/.claude.json` + skill in `~/.claude/skills` | Shows a plan, asks approval, backs up. Add `--tool-families session,native,direct` to shrink the catalog; `--dry-run --json` to preview. |
| **Isolated profile** | `CLAUDE_CONFIG_DIR=~/.claude-rea npx rea-agents setup --client claude_code` then `CLAUDE_CONFIG_DIR=~/.claude-rea claude` | Separate Claude Code profile | Keeps REA out of ordinary research sessions. |
| **Plugin** | `/plugin marketplace add morluto/rea` · `/plugin install rea@rea` | Plugin-managed | Bundles the skill and its own server; `rea doctor` can't see it — check with `/mcp`. |

A project-scoped `.mcp.json` is possible (see `integrations/rea/mcp.example.json`) but is
**not** committed here: it would make every session in this repo, including cloud ones,
try to start a 170-tool server that needs Node 22+ and local engines. Copy it in when you
want REA on for this project; Claude Code will ask you to approve it.

What this repo adds on top of REA's own skill:
- `.claude/skills/rea-investigate/SKILL.md` — a playbook that files REA findings into the
  vault as evidence-linked notes and enforces the authorization gate.
- `workflows/06-reverse-engineering.md` — the runbook.
- `integrations/rea/` — setup checklist, example registration, scoping guidance.

## 6. Legal and safety line (from `DISCLAIMER.md`, verbatim in spirit)

Intended: security research, malware/incident analysis, vulnerability research and
coordinated disclosure, CTFs and education, interoperability, software preservation, and
"debugging or auditing software you own or are authorized to examine".

The project refuses to help with: circumventing DRM, license checks, anti-cheat or other
protection measures; game cheats or tampering with online services; bypassing auth, bot
protection or access controls on systems you are not authorized to test; copying
proprietary software or reproducing its protected code/assets; evading AI providers' usage
policies; reselling AI accounts. "Obtaining source-like output … does not grant rights to
the original program." Reverse engineering may be restricted by jurisdiction or by the
target's license. Run untrusted targets in a VM: runtime capture executes them.

**For Bitcoin vs Banks specifically:** open-source wallets and nodes (Bitcoin Core, Electrum,
LND…) are fair, useful targets when a claim about "how the rails actually work" needs the
shipped binary rather than the docs. Proprietary banking apps are generally *not*: their
terms of service typically forbid reverse engineering, so stay with published documentation,
regulatory filings and network-level observation of your own traffic.

## 7. Operational pitfalls (from docs, HN and independent write-ups)

1. **Timeouts.** Ghidra auto-analysis on a large binary can exceed a client's 60 s MCP
   timeout; raise the client timeout and `REA_GHIDRA_STARTUP_TIMEOUT_MS`.
2. **Context blow-up.** Avoid wide dumps (`batch_decompile`); use `trace_feature` /
   `analyze_function` summaries and `inspect_analysis_view` paging. Keep the tool catalog
   scoped with `--tool-families` and `REA_MCP_INPUT_SCHEMA_PROFILE=compact`.
3. **Memory.** 2–6 GB during headless disassembler runs; 16 GB hosts recommended.
4. **Platform.** Hopper is macOS/Linux; Windows Ghidra is experimental (`windows-ghidra-p0`).
5. **Linux `ps`.** Missing procps makes Ghidra/JADX/firmware/static-JS launches refuse.
6. **Version drift.** The skill on `main` may describe tools the installed npm release lacks;
   trust the live `tools/list`.
7. **Plugin vs setup.** `rea doctor` reports plugin installs as "missing"; don't "fix" that.
8. **ArtCraft confusion.** Viral coverage merged REA with ArtCraft's Adobe-alike apps; REA
   does not claim to have built them.
9. **Hobby-community backlash** is the loudest HN criticism (decomps "a prompt away"), not
   legal risk; quality of the TH04 reconstruction was judged "better than most AI decomps".

## 8. Sources (retrieved 2026-11-02)

- Post: https://x.com/robiartec/status/2116945895015231669 (read via FxTwitter JSON)
- Repo clone `morluto/rea` @ `93b8b82` — `README.md`, `AGENTS.md`, `DISCLAIMER.md`,
  `package.json`, `.claude-plugin/*`, `.agents/skills/reverse-engineer-anything/SKILL.md`,
  `docs/installation.md`, `docs/client-configuration.md`, `docs/mcp-contracts.md`,
  `docs/mcp-prompts.md`, `docs/reconstruction-obligation-ledgers.md`, `CHANGELOG.md`
- npm registry metadata for `rea-agents`
- https://rea.tools/showcase/dx-ball/
- https://github.com/morluto/awesome-reverse-engineering (raw README)
- https://github.com/zhuyansen/awesome-ai-reverse-engineering (raw README)
- https://hoangyell.com/rea-explained/ (2026-10-08) ·
  https://www.developersdigest.tech/blog/reverse-engineer-anything-rea-mcp-agents-guide-2026 (2026-10-14/18)
- https://news.ycombinator.com/item?id=50028275
