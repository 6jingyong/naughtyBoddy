# P5.3 — Public synthetic acceptance fixtures

All tokens and people are fictional, original, non-explicit and intentionally free of copyrighted/private source material. These samples may be used to test **software workflow contracts**, not model skill or willingness to generate adult content.

## Included scenarios

| Scenario | Positive control | Deliberate failure | Detects |
| --- | --- | --- | --- |
| EPUB structure | generated `good.epub` | generated `p_only_bad.epub`, `missing_bad.epub`, `swapped_bad.epub` | Chapters, h1/h2/div vs p coverage, dropped paragraphs, swapped synthetic markers |
| Six-bubble comic | `comic_good.json` | `comic_bad_shifted.json` | Bubble IDs and synthetic translation-token displacement |
| Four-character story | `memory_good.json` | `memory_bad_leak.json` | Private fact visible to wrong character in history or lorebook |

Model replies are **not** generated in these fixtures. `SRC_` and `TGT_` are exact sentinels; the checks explicitly compare those tokens. This cannot validate a real Japanese-to-Chinese translation, inpainting quality, content restrictions, actual memory semantics, or long-term character quality.

## Reproduce without an AI model

From repository root (Python 3.11+, standard library):

```bash
python nb_evalkit.py demo
python nb_evalkit.py generate-book --out-dir /tmp/nb-fixtures
python nb_evalkit.py check-book --epub /tmp/nb-fixtures/good.epub
python nb_evalkit.py check-comic --candidate benchmarks/p53/comic_bad_shifted.json
python nb_evalkit.py check-memory --candidate benchmarks/p53/memory_bad_leak.json
python -m unittest discover -s tests -v
```

`demo` **passes** only if the positive cases pass and all four deliberately corrupted cases fail. Single negative checks intentionally exit code `1` for detected issues. Invalid files/schema exit `2`. A passing `demo` means the detectors responded to injected faults, **not** that any external AI tool passed this benchmark.

## How to extend for real tools later

1. Run the external tool on a rights-cleared sample using your own copy, locally. Do not submit original manuscripts or images to public GitHub.
2. Build an adapter that emits stable IDs, translated segments and source-to-target alignment, or per-character fact-visibility logs.
3. Adapt the manifest to synthetic target markers and check its output; preserve the exact tool version, inference endpoint, model revision, hardware and privacy mode.
4. For non-synthetic translation, human evaluators must judge semantic fidelity. For model-based roleplay, textual observation is not proof of hidden context/memory contents.
5. Add provenance and test outcomes only when actually run. Upstream PRs/issues are not filed automatically.

Related registry research: `docs/p52-friction-evidence.md`. Existing projects such as SillyTavern, Presence, Dragon Memories Manager, Koharu and Bilingual Book Maker remain independent community software, not bundled components of this kit.
