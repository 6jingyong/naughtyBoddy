# P5.7 — Source-backed fine-grained capability tags

Reviewed: 2026-11-09. This release **does not expand the external catalog**. It adds a sourced capability layer to selected existing tools. It is not a benchmark and not a verified adult-content compatibility statement.

## New facet in Discovery

Open the local Studio route /discover and use **具体能力（有来源）**, a sixth facet alongside modality, task, deployment, kind and evidence status.

Examples:
- 漫画翻译 + OCR 识别: candidate manga tools with OCR documented upstream.
- 漫画翻译 + PSD 分层导出: Koharu (official README documented).
- 文字 + GGUF 模型: tools that actually document GGUF loading or use, not every client that can send prompts to a GGUF-powered server.
- 角色互动 + 按角色筛选世界书: lorebook entry filtering in SillyTavern.
- 角色互动 + 按角色过滤历史: Presence's chat-history filtering, which is **different** from lorebook filtering.
- 图像 + LoRA 加载: ComfyUI (model/workflow-dependent).

**Facet logic:** multiple capability tags selected within one facet mean OR. Across distinct facets they mean AND. Missing tags mean **undocumented or not yet catalogued**, not that the tool cannot perform the task.

## Provenance and limitation contract

All positive claims are in [catalog/capability-evidence.json](../catalog/capability-evidence.json). Each requires an exact catalogue item ID, capability key, upstream HTTPS documentation, a readable applicability condition, the document-review date, and the fixed status upstream_documented. Any unknown/deleted target fails registry validation instead of quietly dropping a source link.

A separate official-source classification override enriches ComfyUI with video/audio capabilities in addition to image workflows. Its general external directory listing is **still marked imported_unverified**. Documenting one feature does not certify the whole product or its access policy.

Never assign a capability from a model name, unverified product descriptions, API provider name, or an assistant guess. Source documentation is weaker than actual installed tests; performance, memory use, private-data handling and lawful adult-content support remain untested.

## Corrections made in this round

**EPUB translation:** Current [Bilingual Book Maker documentation](https://github.com/yihong0618/bilingual_book_maker) says conversational/JSON-schema endpoints automatically classify EPUB tags. The prior description of generic 'p-only default' was overbroad. Paragraph-only fallback applies to certain non-conversational MT or disabled/failed classification paths. The recorded friction is now narrowed to those modes. Bilingual Book Maker can access Ollama but does not itself load GGUF; it receives a local-compatible-API tag, not GGUF.

**Roleplay memory:** [SillyTavern's World Info Character Filter](https://docs.sillytavern.app/usage/core-concepts/worldinfo/) controls lorebook entries; it does not make shared group history private. [Presence](https://github.com/leandrojofre/SillyTavern-Presence) covers tracked message visibility; [Dragon Memories Manager](https://github.com/TheDartDragon/Dragon-Memories-Manager) needs Presence metadata to isolate per-character summaries. The tags deliberately distinguish those functions.

**ComfyUI:** Official [README](https://github.com/Comfy-Org/ComfyUI) documents JSON node workflows, LoRA, inpainting, image/video/audio, and an optional --offline mode. Cloud partner nodes are a separate data path; 'offline option' is not a blanket privacy audit.

## Run

    python naughtyboddy.py studio
    # Open http://127.0.0.1:8765/discover

    python nb_catalog.py validate
    python nb_registry.py validate
    python -m unittest discover -s tests -v
    node --check web/chooser.js

Each candidate card shows several capability chips and a collapsible list of direct source links and conditions. No free-text prompt or model call is necessary. This phase has not run independent GPU, end-to-end adult quality, privacy traffic capture or browser visual acceptance tests.

Next: audit stale/broken links, then use versions and permissioned synthetic/real input to start a separate **hands-on capability verification** dataset without overwriting these documentation records.
