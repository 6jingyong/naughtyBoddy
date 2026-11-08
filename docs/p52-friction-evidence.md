# P5.2 · Real-world frictions, existing mitigations and remaining tests

**Reviewed 2026-11-09.** This is a source-linked, editorial research snapshot, not a product ranking or verified user study. **No local installation or reproduction was performed.** Each record in [`registry/frictions/`](../registry/frictions/) distinguishes an upstream documented design choice from a user issue or a Reddit community report.

## Novel translation

| Friction / evidence | Existing response | Unanswered validation |
| --- | --- | --- |
| **EPUB tag selection:** [Bilingual Book Maker documentation](https://github.com/yihong0618/bilingual_book_maker) states that `p` elements are the baseline selection. | Use `--translate-tags` (e.g. h1,h2,h3,p,div) or inspect EPUB plan mode; both already documented. | Compare translated segment coverage on real DRM-free EPUB variations. |
| **Resume vs throughput:** [BBM README](https://github.com/yihong0618/bilingual_book_maker) says `--resume` cannot be combined with `--parallel-workers`. | Use sequential resume where recovery matters. | Is this tradeoff actually a problem on constrained local models? |
| **Local/cloud ambiguity:** [Tolmach Book Translator](https://github.com/KazKozDev/book-translator) supports local Ollama *and* Ollama Cloud models. | Select a genuinely installed local model if local-only processing is required. | Inspect UI disclosure and network traffic per backend. |

No adult-fiction model refusal/quality score is attached. The translations and hardware have not been benchmarked.

## Manga localization

| Friction / evidence | Existing response | Remaining work |
| --- | --- | --- |
| **Balloon misalignment:** [Koharu #1157](https://github.com/koharu-rs/koharu/issues/1157) reports split/missing segments shifting subsequent text. | Reporter proposes punctuation, length and source-prefix checks; this is **not** a verified upstream fix. | Reproduce and automatically detect mis-mapping before export. |
| **Unreadably small vertical text:** [Koharu #846](https://github.com/mayocream/koharu/issues/846). | Reporter proposes expanding source rectangles toward speech bubbles; **unverified suggestion**, not an existing fix. | Test vertical Japanese/Chinese regions and artwork-safe typesetting. |
| **Unknown best OCR engine:** [Koharu #1160](https://github.com/koharu-rs/koharu/issues/1160) contains one contributor's small multilingual comparison. | Settings already allows users to select OCR engine; the missing part is reliable language-specific guidance. | Collect versioned, multi-sample evaluation, not a universal percentage based on one chapter. |
| **Provider privacy boundary:** [Libre Manga Translator](https://github.com/mrdhnto/libre-manga-translator) documents local mode, OCR-text-only self-hosted mode and full-image cloud mode. | Select local/server mode for private source imagery and verify target endpoint. | Inspect actual outbound traffic; no false promise that any arbitrary compatible endpoint is local. |

The first three are reported upstream issues; the fourth is a documented behavior. Do not rank these projects based on issue counts.

## Private fictional roleplay

| Friction / evidence | Existing response | Remaining work |
| --- | --- | --- |
| **Out-of-scene knowledge leakage:** [November 7 community report](https://www.reddit.com/r/SillyTavernAI/comments/1xqampe/how_do_you_stop_characters_from_knowing_things/) and [SillyTavern group-chat docs](https://github.com/SillyTavern/SillyTavern-Docs/blob/main/Usage/Characters/groupchats.md) describe shared history. | [World Info Character Filter](https://github.com/SillyTavern/SillyTavern-Docs/blob/main/Usage/worldinfo.md), [Presence](https://github.com/leandrojofre/SillyTavern-Presence) and [Dragon Memories Manager](https://github.com/TheDartDragon/Dragon-Memories-Manager) already address parts of this. [Molfar Vertep](https://github.com/MolfarWav/Molfar.Vertep) is an experimental alternative, not a proven superior one. | Test which context sources still expose secrets, especially narrator roles and untracked history. |
| **Presence dependency:** [Dragon Memories Manager README](https://github.com/TheDartDragon/Dragon-Memories-Manager) warns isolation fails without correct presence metadata. | Install/enable Presence, ensure records contain attendee data, review generated memories. | Check missing metadata, imported chats and version changes. |
| **Manual lorebook maintenance:** [SillyTavern World Info docs](https://github.com/SillyTavern/SillyTavern-Docs/blob/main/Usage/worldinfo.md) support entry-level character filtering. | Use Character Filter today; optionally pair with Presence/DMM rather than rebuilding the same function. | Quantify the manual bookkeeping burden on long multi-character stories. |

**Important correction:** 'No solution for independent character memory' is not an accurate market claim. At least two existing SillyTavern extensions implement important pieces already. The remaining question is *robustness and ease of use*, not whether isolation is conceptually possible.

## How to use the evidence catalogue

```bash
python nb_registry.py validate
python nb_registry.py frictions
python nb_registry.py frictions --need need-private-roleplay
python nb_registry.py match need-manga-localization
python -m unittest discover -s tests -v
```

`frictions` returns primary links, symptom, user impact, **documented vs proposed mitigation**, related tools/gaps, and a falsifiable test plan. `match` now also returns related friction IDs for each candidate. It **does not** promote a candidate to a recommendation or assign an NSFW-compatibility score.

## Next actions (upstream-first)

1. **Public knowledge contribution:** gather existing instructions and corrections for each user friction. File an upstream issue *only if the behavior is reproducible and not already reported*; do not spam maintainers.
2. **Small evaluation kit:** make licensed or synthetic test fixtures for an EPUB tag-coverage audit, six dialogue bubbles with one intentionally shifted ID, and four fictional characters with private scenes. Keep originals private.
3. **Only after testing:** determine if NaughtyBoddy should contribute a validation plugin, an installation guide, an adapter, or a standalone component. Do not write a duplicate comic translator or roleplay frontend merely because a source thread reports friction.
