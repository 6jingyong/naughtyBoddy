# P5.3 — Synthetic evaluation kit (2026-11-09)

**Goal:** turn three recurring user problems from P5.2 into small, reproducible, model-free *contract tests*. These are public reference fixtures, not ratings for existing adult AI projects.

| User friction | Test fixture | Contract checked | Not tested |
| --- | --- | --- | --- |
| Bilingual Book Maker tag coverage; long-book source omission | Two-chapter EPUB generator with 8 uniquely labeled h1/h2/p/div segments | Chapter order, segment presence, stable ID, exact artificial marker alignment | Natural translation quality, EPUB footnotes/CSS, actual BBM behavior |
| Koharu split/shifted balloon report | Six-bubble stable-ID JSON and corrupted mapping | Missing, duplicate and shifted IDs; target sentinel mismatch | OCR, bubble detection, typography, actual Koharu behavior |
| Fictional character's unobserved secrets | Four-character visibility table and leaked snapshots in history/lorebook | Presence-based fact visibility across three explicit context channels | Actual LLM knowledge, retrieval accuracy, any external frontend |

## Command

```bash
python nb_evalkit.py demo
python nb_evalkit.py generate-book --out-dir /tmp/nb-fixtures
python nb_evalkit.py check-book --epub /tmp/nb-fixtures/p_only_bad.epub
python nb_evalkit.py check-comic --candidate benchmarks/p53/comic_bad_shifted.json
python nb_evalkit.py check-memory --candidate benchmarks/p53/memory_bad_leak.json
```

The last three are **expected to fail** with actionable JSON error codes. The `demo` command succeeds when every positive control passes and every deliberately broken control fails. Source files are synthetic original test materials; never upload private books, chats or pages into GitHub issues.

## Implementation boundaries

- Python 3.11 stdlib; no network access, inference or external executable; tests can run on GitHub Actions.
- EPUB reader is deliberately bounded to this fixture schema. Do not use it as a replacement for Calibre, EbookLib or specialized parsing of arbitrary EPUBs.
- Fixed token pairs and explicit witness lists are observability scaffolding, **not** an assessment of realism, translation semantics, low-refusal compatibility, safety or quality.
- A user-created adapter for another software project may export the expected JSON contract; integration is **not yet implemented**.
- These fixtures map to P5.2 friction hypotheses, but do not validate that those upstream products reproduce the reported behavior.

## Next

The next real improvement is not a larger synthetic score. It is a reproducible adapter for one existing project, coupled with an actual user-facing review of the outputs. Avoid presenting injected failures as independent benchmark results.
