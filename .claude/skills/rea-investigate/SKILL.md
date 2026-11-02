---
name: rea-investigate
description: Investigate shipped software (a binary, Electron app, APK, .NET assembly, firmware, capture or website) with the REA MCP server and file evidence-linked findings into the vault. Use when the user says "reverse engineer…", "how does <app> actually do X", "look inside the binary", "trace this feature/IPC", "compare these two builds", "clean-room rebuild", or when a research claim about how a system works can only be settled by the shipped artifact.
---

# rea-investigate

The Research Monster's "open the box" skill. REA (`morluto/rea`) gives this agent typed,
local-only reverse-engineering tools; this skill decides *whether* to use them, keeps the
evidence honest, and files what we learn so it compounds. Background:
`docs/rea-reverse-engineering-stack.md`. Setup: `integrations/rea/README.md`.

## 0. Gate — before any tool call
1. **Authorization.** Is the target software the user owns or is authorized to examine
   (own build, open-source release, authorized assessment, preservation)? If not, stop and
   say why. Never help with DRM/license/anti-cheat circumvention, copying proprietary
   code/assets, or bypassing access controls — REA's own disclaimer refuses these too.
   For this project: open-source wallets/nodes yes; proprietary banking apps generally no.
2. **Is REA even needed?** For a source repository, use normal code tools. REA is for
   *shipped* artifacts, decompilation, runtime evidence, or build-vs-build comparison.
3. **Where are we?** REA runs on the user's machine (Node 22+, an engine). In a cloud
   session, prepare the question and the exact commands and hand them over.
4. **Execution ≠ inspection.** Static analysis is safe; runtime capture runs the target under
   the user's account. Ask before any runtime tool on an untrusted binary; suggest a VM.

## 1. Frame the question
Turn the request into a checklist: *what claim, what evidence would settle it, what target
(path + SHA-256), what would count as done*. Link it to the thread (`#settlement`, `#fees`,
`#custody`, …) so the finding has a home in the MOC.

## 2. Route by target (REA's own rule)
| Target | First call |
|---|---|
| Native binary / archive (ZIP, APK, IPA, DMG, PyInstaller) | `open_binary` → `binary_session` (read `tool_availability`) → `analyze_function` / `trace_call_path` |
| ASAR or extracted Electron / JS tree | `analyze_javascript_application` with `detail: "summary"` → `inspect_analysis_view` → `trace_application_feature` |
| Android APK | `inspect_android_package` (needs headless JADX + JDK) |
| .NET assembly | `inspect_managed_artifact` (no engine) |
| Website / your own open browser | `list_browser_targets` or `capture_browser_scenario` with declared actions |
| HAR / SAZ / mitmproxy capture | `inspect_web_network_capture` |
| Firmware | `inspect_firmware_regions` / `extract_firmware` (Binwalk/Unblob, Linux) |
Or start from a guided prompt: `investigate_feature`, `compare_application_versions`,
`trace_crash`, `verify_reconstruction`, `audit_residual_unknowns`.

## 3. Work summary-first, evidence-always
- Narrow questions, batched around one hypothesis. No `batch_decompile` of whole modules.
- Keep `parent_evidence_id`s; page retained views instead of re-running analysis.
- When pseudocode and instructions disagree, trust instructions and `read_bytes` (DX-Ball
  lesson: the decompiler hid a stack input the asm made obvious).
- Separate **observed / inferred / unknown** in every statement. Never say static analysis
  "saw" execution. Keep negative searches bounded ("not found in the 3 modules inspected").
- Close `close_binary` when the engine is no longer needed; `export_evidence_bundle` /
  `reset_investigation --save_path` before ending so Evidence IDs survive.

## 4. Reconstruction (only if asked)
Rebuild with ordinary coding tools from the *evidence*, not from the pseudocode verbatim.
Use `build_reconstruction_obligation_ledger` to list the claims the rebuild must satisfy,
write an oracle (reference outputs from the original, byte/behaviour comparison), iterate
until the ledger closes. Note what a real clean room needs: a separate implementation
environment that cannot read REA, the target or the analysis output.

## 5. File it (this is what makes it compound)
Write `vault/20-notes/YYYYMMDD-<kebab-claim>.md` (template `vault/_templates/note.md`) with:
- the claim in one sentence and its status (observed / inferred / unresolved);
- target identity (name, version, SHA-256), engine/provider, REA version;
- the **Evidence IDs** and the key facts (addresses, instructions, bytes, module/IPC names);
- limitations and residual unknowns;
- `tags: [reverse-engineering, <thread>]`, `MOC:: [[Bitcoin-vs-Banks]]`.
Store exported Evidence bundles under `vault/50-assets/rea/<target-slug>/` (never commit
anything you are not allowed to redistribute; the bundle contains bytes from the target).
Add the note to the thread in the MOC and link related sources.

## 6. Report
Answer in plain language, tie each conclusion to its Evidence ID, list unknowns, and name
the note you filed. If the question was *not* settled, say so — a bounded "unknown" is a
valid result here.

## Troubleshooting
- Tools absent → user runs `npx rea-agents@latest doctor --client claude_code --json`, then
  `setup`, then restarts Claude Code. Plugin installs show as "missing" in doctor; check `/mcp`.
- `Tool … disabled` → the family is out of scope; rerun setup with a wider `--tool-families`.
- Ghidra timeouts → `REA_GHIDRA_STARTUP_TIMEOUT_MS`, bigger client timeout; cold starts can take minutes.
- `capability_unavailable` on Linux → install `procps`.
