# P2 — Checkpointed novel translation (TXT / EPUB)

## Scope

A **functional, offline-testable** text pipeline, not a claim of production translation quality.

- Import UTF-8 `.txt` or DRM-free `.epub` you have rights to process.
- Discover EPUB chapter order from `META-INF/container.xml`, the OPF manifest, and its spine; no external URLs, DRM, images or scripts are executed.
- Split long paragraphs into stable, indexed chunks, and translate chapter headings as checkpointed segments too.
- Store originals, glossary, translation segments, provider/model IDs and review flags in a private local project directory. Inference never happens during import, status, audit or export.
- Translate a bounded number of pending segments per CLI invocation. Each successful response is committed to SQLite; a failure stops the run and leaves unfinished segments pending.
- Local Ollama, local OpenAI-compatible servers, and explicitly consented remote OpenRouter/custom APIs share P1's text inference adapter.
- Export complete projects to plain TXT or a **reflowable, normalized-text EPUB**. Incomplete results and mock/demo content are blocked by default; demo export requires `--allow-demo` and prominent demo labeling.
- Audit reports uncompleted segments and heuristic flags for missing required glossary terms, suspected refusal, and simulated output.

## Fast demo (no model required)

```bash
python naughtyboddy.py novel init --input examples/sample-book.txt --project private/book --glossary examples/sample-glossary.json
python naughtyboddy.py novel status --project private/book
python naughtyboddy.py novel translate --project private/book --provider mock --max-segments 100
python naughtyboddy.py novel audit --project private/book
python naughtyboddy.py novel export --project private/book --output private/demo.epub --allow-demo
```

The mock provider **copies input with a label; it is NOT a translator**. This exercises chapter tracking, checkpointing and export only.

## Real local inference (only after installing a model)

```bash
python naughtyboddy.py novel translate --project private/book --provider ollama --model YOUR_MODEL --max-segments 20
# OR llama-server / KoboldCpp with OpenAI-compatible endpoint
python naughtyboddy.py novel translate --project private/book --provider compatible --base-url http://127.0.0.1:8080/v1 --model YOUR_MODEL --max-segments 20
```

Cloud example (private excerpts are sent off-device, usage can incur fees):

```bash
# Set OPENROUTER_API_KEY in your local shell, not in the repository.
python naughtyboddy.py novel translate --project private/book --provider openrouter --model ORG/MODEL --accept-remote --max-segments 20
```

`--max-segments` bounds *inference calls per invocation*, not their token cost. The caller controls running repeated invocations, and no provider fallbacks happen automatically.

## Project state

```text
private/book/
  manifest.json      # Source fingerprint and project settings
  glossary.json      # Editable source->target terminology
  source.txt|epub    # Copied original input
  work.sqlite3       # Local translation segments + per-segment checkpoints
```

The private directory is never auto-uploaded or included in Discovery results. Do not commit project directories, novel source text, provider keys, or exported books to public Git.

## Integrity and limitations

- IDs are based on chapter, paragraph, chunk position and content fingerprint. The copied source and its SHA-256 are stored for provenance. Editing source means making a new project, not mutating past checkpoints.
- EPUB input rejects archive traversal, duplicate names, suspicious inflation, excessive entry counts, external manifest links, and oversized XHTML.
- EPUB exports include a working package/spine/nav and pass an offline ZIP integrity test and read-back parser. **No epubcheck or physical e-reader test yet.**
- **Original images, cover, CSS, emphasis, inline styles, embedded fonts, footnotes, complex navigation, and exact book layout are NOT preserved.** This is a normalized text-only export suitable as a first pipeline test.
- Literal source or generated HTML is XML-escaped on export; it is not executable.
- A complete segment count detects missing work, **not semantic omission or translation quality**. Refusal and glossary checks are heuristic and need human review.
- Prompting uses previous translated text in the same chapter for local continuity and the glossary. Long-range character relationship tracking and whole-book semantic checks remain future work.
- A stale `.translate.lock` may need manual removal after an unclean termination; do this only when no translation is currently running.
- Mock responses are NOT merged with final output by default. A demo export must be requested explicitly and labeled.
- Input EPUB support is limited to straightforward spine-listed HTML/XHTML and UTF-8. DRM, PDFs, scanned books, fan-fiction sites, and automatic downloading are out of scope.

## Offline verification

```bash
python -W error::ResourceWarning -m unittest discover -s tests -v
```

Offline mocks test parser security, TXT/EPUB reading and writing, resume, glossary flags, opt-in remote permission, escaping and the CLI. Hardware/model/API quality are not verified by these tests.
