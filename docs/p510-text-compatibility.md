# P5.10 · Text frontend ↔ inference runtime compatibility relationships

**Reviewed 2026-11-09.** This is the first *documented-connection* layer for NaughtyBoddy's text-only Discovery. It does **not** execute any model, install software, probe an endpoint, or certify adult-content performance.

## What this graph actually establishes

The source-linked [catalog/text-compatibility.json](../catalog/text-compatibility.json) contains ten explicitly typed relationships: **9 upstream-documented connections/dependencies/format paths** and **1 protocol-only candidate awaiting tests**. Every edge has named endpoints, API profile, primary source URL(s), setup steps, limitations and an exact test plan. Edges cannot be implicitly inferred from model names or joined into universal compatibility claims.

| App or component | Target | Relation | Documentation status |
| --- | --- | --- | --- |
| [SillyTavern](https://docs.sillytavern.app/usage/api-connections/) | [KoboldCpp](https://koboldcpp.net/docs/api/connect-apps/) | Dedicated KoboldCpp Text Completion connection | Documented, not locally tested |
| SillyTavern | [Ollama](https://docs.ollama.com/api/introduction) | Ollama local connection | Documented, not locally tested |
| [Bilingual Book Maker](https://github.com/yihong0618/bilingual_book_maker) | Ollama | OpenAI-compatible /v1 subset | Documented, not locally tested |
| [Book Translator / Tolmach](https://github.com/KazKozDev/book-translator) | Ollama | Native Ollama text translation pipeline | Documented, not locally tested |
| [SillyTavern Presence](https://github.com/leandrojofre/SillyTavern-Presence) | SillyTavern | Extension host | Documented |
| [Dragon Memories Manager](https://github.com/TheDartDragon/Dragon-Memories-Manager) | SillyTavern | Extension host | Documented |
| Dragon Memories Manager | Presence | Dependency **for reliable character isolation** | Documented; not hard requirement for every feature |
| KoboldCpp | GGUF | Can load a model file in GGUF format | Documented, no particular checkpoint tested |
| Ollama | GGUF | Can import pre-quantized GGUF via Modelfile | Documented, no particular checkpoint tested |
| Bilingual Book Maker | KoboldCpp | Hypothetical OpenAI-compatible /v1 bridge | **Protocol candidate only**, no direct pair-specific validation |

### Why only these relations?

- KoboldCpp offers dedicated KoboldCpp/KoboldAI and OpenAI-compatible /v1 paths. In the dedicated SillyTavern mode, the documented base address is \`http://localhost:5001\` without \`/v1\`. API profile matters.
- Ollama documents local \`http://localhost:11434\` and its OpenAI subset at \`http://localhost:11434/v1\`. Its cloud models are *not equivalent* to local checkpoints for privacy.
- Bilingual Book Maker gives an explicit Ollama /v1 example; Book Translator documents model roles and warns that \`-cloud\` model selections can send texts to Ollama Cloud.
- GGUF is a **model file format**, not a model family, licensing statement, quality test or guarantee that arbitrary weights load on the target hardware. Ollama's GGUF import requires a Modelfile and a pre-quantized GGUF.
- SillyTavern Presence and Dragon Memories Manager are client extensions rather than generation backends. DMM explicitly warns that absent Presence metadata can make a supposedly individual summary include everyone's messages.
- RisuAI, Agnai and every imported named 'uncensored' or 'abliterated' model have **no inferred pairings** in this version. That means *unresearched*, not incompatible.

**Never assume transitivity:** even if Tool A speaks an OpenAI-compatible schema and Runtime B offers /v1, their specific parameters, streaming, error handling, sampler maps, model name selection and prompt templating can differ. The BBM↔KoboldCpp pair is explicitly marked \`protocol_inferred_not_tested\`, not 'documented working'.

## User experience (no LLM)

Launch the existing local Studio, open \`/discover\` and use the **连接方式（有来源）** facet together with text creative task/deployment/evidence tags. Each tool with an explicit relationship exposes an expandable **连接与依赖关系** area. It distinguishes incoming from outgoing connections, lists the other tool or format, offers official source documents, limitations, relevant config steps and a non-executable localhost address hint when available.

Choosing tags only filters one local JSON response; it does not connect to inference servers. No model selection, adult-content prompt or personal manuscript is submitted.

## Evidence safety / future work

A documented edge is **weaker** than an observed operational pair, and an observed operational pair would still not prove all model weights or all adult creative content will work. Planned hands-on tests should capture:
- Actual named versions (client, server and exact installed model/checkpoint digest), memory and OS.
- API path, prompt/template structure, parameter/streaming support, and pass/fail reasons.
- Local-vs-cloud requests, outbound traffic and any private or user-supplied text exposure (use synthetic/authorized text).
- Reproducible positive and negative tests; check full chapter retention for translators and stable per-character context for roleplay.

No negative compatibility conclusion has been drawn for unlisted pairs. Existing generic API plugin systems remain available but no automatic breadth claims are imported.

## Developer commands

    python nb_text_compat.py validate
    python nb_text_compat.py list
    python nb_text_compat.py candidates
    python nb_text_compat.py for-item --item reviewed-solution-sillytavern
    python -m unittest discover -s tests -v
    node --check web/chooser.js

All commands are local and offline. Previous 106-entry archive and 52-entry public text catalogue are unchanged in size. Repo software licensing remains outstanding.
