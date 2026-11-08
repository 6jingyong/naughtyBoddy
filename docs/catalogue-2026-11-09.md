# NaughtyBoddy · Needs & solutions catalogue (2026-11-09)

This is a **source-reviewed candidate catalogue**, not a ranked list or an endorsement. Each claim below comes from upstream documentation, except where a community report is clearly labeled. **No listed project has been installed or empirically tested for adult-content compatibility by this catalogue round.** Public-source dates and product capabilities may change.

## Long-form fiction translation

**User task:** translate authorized long fiction, preserve paragraphs, terms and lawful adult scenes; remain editable and resume after errors/model changes.

| Candidate | Documented capabilities | Still unknown |
| --- | --- | --- |
| [Bilingual Book Maker](https://github.com/yihong0618/bilingual_book_maker) | EPUB/TXT translation, multiple endpoints including local-compatible APIs, context/glossary/resume options | Adult-scene fidelity, cloud privacy by endpoint, model-switch quality |
| [Book Translator](https://github.com/KazKozDev/book-translator) | Localhost SQLite app, EPUB/TXT/PDF/DOCX input; Ollama integration | Real-world paragraph coverage, OCR for scanned input, adult fidelity |
| [Calibre](https://calibre-ebook.com/) | Ebook library, conversion and editing utility | Not a translation engine; requires another translator |

**Evidence:** official [BBM README](https://github.com/yihong0618/bilingual_book_maker), [Book Translator README](https://github.com/KazKozDev/book-translator/blob/main/README.md), [Calibre manual](https://manual.calibre-ebook.com/). No title is labeled as having passed a long-book test.

## Manga localization

**User task:** identify bubbles and text, translate, restore artwork, edit lettering and export, optionally wholly locally.

| Candidate | Documented capabilities | Still unknown |
| --- | --- | --- |
| [Libre Manga Translator](https://github.com/mrdhnto/libre-manga-translator) | Browser extension; local WebLLM, self-hosted API or cloud option; editable boxes and image cleanup | Independent OCR accuracy, quality by model, real network behavior |
| [ComiTrans](https://github.com/Aaaaamadeus/ComiTrans) | Windows GUI, local ONNX OCR/inpaint, API translation, manual lettering and PDF workflows | Local translation backend compatibility and actual art-preservation quality |
| [Koharu](https://github.com/koharu-rs/koharu) | Local GGUF or cloud translation, page editing, layered PSD export, GPU backends | Resource use, model-specific fidelity, reproducible editing benchmarks |

**Privacy nuance:** LMT's self-hosted API mode documents sending OCR text, but its Gemini mode sends a page image; ComiTrans documents optional whole-page multimodal translation. Provider selection is therefore part of a meaningful privacy test, not a mere settings checkbox.

## Private fictional roleplay

**User task:** run consenting-adult fictional dialogue with persistent personas and private local-friendly state, preferably portable across clients.

| Candidate | Documented capabilities | Still unknown |
| --- | --- | --- |
| [SillyTavern](https://github.com/SillyTavern/SillyTavern) | Character cards, history export/import, world-information ecosystem | Long-term persona stability, per-character knowledge boundaries, actual backend privacy |
| [RisuAI](https://github.com/risuai/RisuAI) | Lorebooks, group chats, prompts, input/output translation, plugin ecosystem | Portability details and real long-term memory quality |
| [Agnai](https://github.com/agnaistic/agnai) | Self-hosting, guest-only mode, multi-character conversations | Long-session consistency and access controls |
| [KoboldCpp](https://github.com/LostRuins/koboldcpp) | Local GGUF runtime, OpenAI-compatible API and a web UI | Backend alone cannot guarantee character memory or private knowledge boundaries |

**Community signal, not population data:** [Nov 7 report on NPC knowledge leakage](https://www.reddit.com/r/SillyTavernAI/comments/1xqampe/how_do_you_stop_characters_from_knowing_things/) and [Feb 24 discussion of continuity](https://www.reddit.com/r/SillyTavernAI/comments/1rdeo0l/ai_for_roleplay_longterm/). Neither demonstrates that every existing frontend lacks a solution.

## How to use the registry

Run `python nb_registry.py validate`, `python nb_registry.py needs`, `python nb_registry.py solutions`, and `python nb_registry.py match need-private-roleplay`. A matching tag is a discovery signal **not an assessment score**. Records store URLs and `reviewed_on`; all acceptance check outcomes are currently `not_run`.

## Next evidence collection

- Test one permitted real or synthetic benchmark per need with exact versions and hardware recorded.
- Ask users which specific step caused rework, and how much; do not conflate Reddit anecdotes with market size.
- Before upstream integration, audit licenses for code, checkpoints and bundled assets separately.
- Keep private books, roleplay chats, image scans and API keys out of public GitHub evidence records.
