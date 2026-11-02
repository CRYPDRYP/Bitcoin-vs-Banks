---
title: "@robiartec: the REA reverse-engineering stack (20 repos)"
created: 2026-11-02
type: source
source_type: x-post
url: "https://x.com/robiartec/status/2116945895015231669"
author: "rob."
author_handle: "robiartec"
author_followers: 104220
posted: "2026-11-01T17:30:06+00:00"
lang: "es"
engagement: {likes: 2466, reposts: 378, replies: 54, bookmarks: 3311, views: 155104}
community_note: false
status: captured
project: "Bitcoin vs Banks"
tags: [x-post, tooling, reverse-engineering]
---

# 🐦 @robiartec: the REA reverse-engineering stack (20 repos)

> Post by **rob.** (@robiartec, verified) on 2026-11-01 · [original](https://x.com/robiartec/status/2116945895015231669) · captured via FxTwitter

## Text
> ESTO ES RELAMENTE P*TAMENTE PELIGROSO...
> 
> el creador de REA acaba de soltar 20 repos de GitHub para montarte un p*to estudio de ingeniería inversa:
> 
> [01] núcleo de análisis
> > REA: un único MCP que se conecta a todo http://github.com/morluto/rea
> > Ghidra: decompilador, gratis http://github.com/NationalSecuri…
> > GhidraMCP: deja que tu agente maneje Ghidra http://github.com/LaurieWired/Gh…
> > ida-pro-mcp: conecta tu agente a IDA Pro http://github.com/mrexodia/ida-p…
> 
> [02] móvil y apps
> > jadx: convierte APKs de Android de vuelta a Java http://github.com/skylot/jadx
> > Apktool: desmonta APKs y vuelve a montarlas http://github.com/iBotPeaches/Ap…
> > Frida: engánchate a las apps mientras se ejecutan http://github.com/frida/frida
> > ILSpy: decompila .NET http://github.com/icsharpcode/IL…
> 
> [03] binarios y bajo nivel
> > radare2: framework de RE que vive en tu terminal http://github.com/radareorg/rada…
> > x64dbg: depurador para Windows http://github.com/x64dbg/x64dbg
> > ImHex: editor hexadecimal con su propio lenguaje de patrones http://github.com/WerWolv/ImHex
> > angr: motor de ejecución simbólica http://github.com/angr/angr
> 
> [04] red y ejecución
> > mitmproxy: se pone en medio y lee el tráfico http://github.com/mitmproxy/mitm…
> > dnSpy: depura y edita apps .NET http://github.com/dnSpyEx/dnSpy
> > rizin: el fork de radare2 http://github.com/rizinorg/rizin
> > raddebugger: el depurador de Epic Games http://github.com/EpicGames/radd…
> 
> [05] reconstruir y verificar
> > awesome-ai-reverse-engineering: 122 repos, todos puntuados http://github.com/zhuyansen/awes…
> > awesome-reverse-engineering: seleccionado por el creador de REA http://github.com/morluto/awesom…
> > flujos de REA: prompts de investigación listos para usar, vienen con REA
> > bucle clean-room: SPEC.md, oráculos y comprobaciones hasta que coincida
> 
> cómo funciona: binario -> REA -> SPEC.md -> reconstruir -> oráculo -> reintentar
> 
> guárdate esto, apúntalo a cualquier app y mira cómo se explica sola.

## Links in the post
- http://github.com/morluto/rea (https://t.co/sE3MOSYxHG)
- http://github.com/NationalSecuri (https://t.co/lbaJuUnflN) _(truncated by X; resolve via the t.co link)_
- http://github.com/LaurieWired/Gh (https://t.co/U9TrOq4eRK) _(truncated by X; resolve via the t.co link)_
- http://github.com/mrexodia/ida-p (https://t.co/ApO5fU1SiF) _(truncated by X; resolve via the t.co link)_
- http://github.com/skylot/jadx (https://t.co/jRQ54WNcEm)
- http://github.com/iBotPeaches/Ap (https://t.co/0ewVT6VcfW) _(truncated by X; resolve via the t.co link)_
- http://github.com/frida/frida (https://t.co/QV8f0cW3pJ)
- http://github.com/icsharpcode/IL (https://t.co/cjzoxaxuhC) _(truncated by X; resolve via the t.co link)_
- http://github.com/radareorg/rada (https://t.co/hGOMvgUPE3) _(truncated by X; resolve via the t.co link)_
- http://github.com/x64dbg/x64dbg (https://t.co/Pg5rmltX3A)
- http://github.com/WerWolv/ImHex (https://t.co/sgVuKAFi3J)
- http://github.com/angr/angr (https://t.co/uBijdpN2CV)
- http://github.com/mitmproxy/mitm (https://t.co/aTWukNI2cd) _(truncated by X; resolve via the t.co link)_
- http://github.com/dnSpyEx/dnSpy (https://t.co/UDDAvArcsC)
- http://github.com/rizinorg/rizin (https://t.co/siG2Vw5ose) _(truncated by X; resolve via the t.co link)_
- http://github.com/EpicGames/radd (https://t.co/XVfi410Cui) _(truncated by X; resolve via the t.co link)_
- http://github.com/zhuyansen/awes (https://t.co/Bs6RYsnxAn) _(truncated by X; resolve via the t.co link)_
- http://github.com/morluto/awesom (https://t.co/Mo7AajnvVR) _(truncated by X; resolve via the t.co link)_

## Media
- video: https://video.twimg.com/amplify_video/2116945737418190848/vid/avc1/1500x1620/lI1cBNAamgVmwQ5L.mp4?tag=29 (thumb: https://pbs.twimg.com/amplify_video_thumb/2116945737418190848/img/-1olWOD81QBoo0Wy.jpg) · 21.61s

## Why it matters
- Entry point for the REA deep dive — an agent-driven way to check how shipped software (e.g. open-source wallets/nodes) actually behaves, i.e. mechanism over narrative.

## Key claims / data
- Claim: "the creator of REA just released 20 repos". **Checked:** only `morluto/rea` and `morluto/awesome-reverse-engineering` are morluto's; the other 18 are third-party tools (Ghidra is the NSA's, etc.) and `EpicGames/raddebugger` is in neither curated list.
- Claim: a loop `binary → REA → SPEC.md → rebuild → oracle → retry`. **Checked:** REA has no `SPEC.md`; its real artefacts are Evidence bundles and the *reconstruction obligation ledger*. The oracle idea matches REA's DX-Ball showcase (3,205 behaviour cases, 63 matching compiled bytes).
- Claim: `awesome-ai-reverse-engineering` has "122 repos, all scored". **Checked:** it is by Agent Skills Hub (not morluto), lists 117 repos today, and the grading is done by a model reading READMEs.
- Links truncated by X resolved from the lists: `NationalSecurityAgency/ghidra`, `LaurieWired/GhidraMCP`, `mrexodia/ida-pro-mcp`, `iBotPeaches/Apktool`, `icsharpcode/ILSpy`, `radareorg/radare2`, `mitmproxy/mitmproxy`, `EpicGames/raddebugger`, `zhuyansen/awesome-ai-reverse-engineering`, `morluto/awesome-reverse-engineering`.
- Full analysis: [docs/rea-reverse-engineering-stack.md](../../docs/rea-reverse-engineering-stack.md) (outside the vault, in the repo).

## Related
- MOC:: [[bitcoin-vs-banks]] · [[Bitcoin-vs-Banks]]
- See also:: `workflows/06-reverse-engineering.md` · skill `rea-investigate` · `integrations/rea/README.md`
