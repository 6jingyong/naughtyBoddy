# P5.9 · Text-first product scope

**Decision date:** 2026-11-09.

**Main product:** NaughtyBoddy Discovery — a locally served, tag-based index of **lawful adult-oriented text creation tools**, without LLM-based search or free-text input.

**Supporting compatibility work:** local text-model backends, adapter checks, EPUB/TXT translation tests, glossary and context continuity, roleplay character memory and privacy boundaries.

**Paused / archived (not deleted):** image generation, manga OCR/editing, video/audio tools, ComfyUI custom workflows, model weight/video checkpoint catalogues and the older P4 comic editor. The original P5.6–P5.8 four-source snapshots, all media projects, historical tests and source code remain intact in the repository, but they are not part of current public Discovery.

## Why narrow

Image/video ecosystems often depend on individually assembled workflows, custom nodes, LoRA/checkpoint licenses, private visual assets, character/IP rights and complex hardware setups. A large directory is easier to create than to validate reliably. Text workflows offer a more tractable initial surface: EPUB, text generation, fictional character roleplay, interoperable text runtimes, and the user's ability to retain/edit/export their writing.

**Text is not exempt from rights issues.** The index must not imply permission to copy restricted novels, private chat logs or third-party character cards; the user's rights and applicable law remain relevant.

## Implementation

- \`nb_catalog.py\` and \`GET /api/catalog\` remain the **full, local-only archival research catalogue**, currently 106 records, with existing provenance, feature evidence, link checks and duplicate warnings.
- \`nb_text_catalog.py\` creates a **read-only strict text projection**. Only records with exactly \`["text"]\` as modality and exclusively text tasks are visible; multimodal tools, OCR/manga products and image/video/audio entries are excluded even if they produce written output.
- \`GET /api/catalog/text\` supplies the public \`/discover\` page. Only text-specific task and capability chips are present. External source counts and link health totals are recalculated over the narrowed visible view.
- \`/discover\` keeps existing multi-select tags with OR within a facet, AND across facets, no free-text prompt, no GPU call, no LLM, no third-party search and no telemetry.
- Previous visual/manga prototypes remain accessible as clearly marked **historical experiments** inside Studio for existing projects; no new feature development is planned there.

The view is **intentionally conservative**, and a text-capable tool may not appear if the recorded evidence also marks it as multimedia. The correct way to include it later is a **separately documented, narrowly scoped text-only profile**, not removing the actual media modalities or inventing a text-only capability.

## Current product priorities

1. **Text model discovery:** documented local, hosted and hybrid text backends, prompt/response constraints, verifiable compatibility, license and actual privacy paths.
2. **Long-form fiction:** authorized EPUB/TXT translation, glossary consistency, chapter integrity, partial resume and editable output.
3. **Fictional roleplay:** character cards, group-chat knowledge boundaries, separate memories, portability and user-controlled storage.

Only independently observed behavior earns a hands-on validation result. Vendor/third-party “uncensored” labels do not guarantee compatibility, legality or translation quality.

## Validate

    python nb_catalog.py validate
    python nb_text_catalog.py
    python nb_catalog_health.py validate
    python -m unittest discover -s tests -v
    node --check web/chooser.js

Run \`python naughtyboddy.py studio\`, open http://127.0.0.1:8765/discover and click tags. The image/video catalog is intentionally not displayed and is not automatically searched, downloaded or deleted.

**Upcoming:** evaluate the quality of text-only metadata and model/provider independence; do not restart broad image/video discovery until the text-first path has demonstrated real user value.
