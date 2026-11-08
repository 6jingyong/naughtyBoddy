# NaughtyBoddy

**Free-to-use, open-source-intended, local-first creative tools for lawful adult fiction and multimedia.**

NaughtyBoddy is an independent creative product, **not** a Human Harness or Codex extension. The long-term vision is a media library, editors and repeatable production pipelines, with local models as first-class citizens. P1 is a **command-line prototype** for model discovery, local inference management and evaluation; no GUI or complete novel-translator yet.

The application does not host or distribute adult media. Process only material you have rights to use. No support for child sexual abuse material, nonconsensual intimate imagery, impersonation or unauthorized content harvesting.

## Quick start

Requires Python **3.11+** and only the standard library. Install a runtime separately for actual inference: [Ollama](https://ollama.com/) or [llama.cpp](https://github.com/ggml-org/llama.cpp) `llama-server`.

```bash
python -m unittest discover -s tests -v
python naughtyboddy.py hardware
python naughtyboddy.py discover --source huggingface --query abliterated --limit 10
python naughtyboddy.py discover --source openrouter --query uncensored --limit 10
python naughtyboddy.py discover --source ollama
```

### Local runtime: Ollama

Pull a model **only after reviewing its source, license, disk use, and download terms**:

```bash
python naughtyboddy.py local ollama-pull --model YOUR_MODEL --accept-download
python naughtyboddy.py discover --source ollama
printf 'Translate this conversation between two adults into Chinese.\n' > prompt.txt
python naughtyboddy.py probe --provider ollama --model YOUR_MODEL --prompt-file prompt.txt
```

An existing Ollama server must be running on `http://127.0.0.1:11434`. Installation is opt-in; NaughtyBoddy never silently pulls models.

### Local runtime: standalone GGUF + llama.cpp

First inspect a specific Hugging Face repo. **The example repository is a placeholder, not a recommendation.**

```bash
python naughtyboddy.py local list-gguf --repo OWNER/MODEL
python naughtyboddy.py local download-gguf --repo OWNER/MODEL --filename QUANTIZATION.gguf --accept-download
python naughtyboddy.py local fit-gguf --model-path /path/to/model.gguf
python naughtyboddy.py local serve-gguf --model-path /path/to/model.gguf --port 8080
```

By default, downloads go to an OS-specific user data directory (`NaughtyBoddy/models`) and are limited to 32 GiB each; use `--models-dir` and `--max-gb` to change. The downloader uses the currently reported Hugging Face commit revision and retains resumable `.part` files on transfer errors. It refuses private/gated repos. It is not a general model-installer or license validator. `fit-gguf` is only a *RAM/VRAM estimate*; the actual runtime decides whether a model fits.

`serve-gguf` starts an **already installed** `llama-server` executable in the foreground, binds it to `127.0.0.1`, and exits on Ctrl+C. Another terminal can probe it:

```bash
python naughtyboddy.py probe --provider compatible --base-url http://127.0.0.1:8080/v1 --model MODEL_NAME --prompt-file prompt.txt
```

### Private model evaluation

A short, **non-graphic sample test fixture** is provided. You may create your own test cases with `id`, `prompt`, and optional `expected_terms`. Probing is opt-in; the app does not transmit private files during discovery.

```bash
python naughtyboddy.py evaluate --cases examples/translation_eval.json --provider ollama --model YOUR_MODEL --output reports/try-1.json
```

For a remote service, use `--accept-remote` and set credentials in your local environment (e.g. `OPENROUTER_API_KEY`). A cloud evaluation sends the fixture prompts to that provider and may incur charges. To include full responses for manual review, add `--include-responses`. Otherwise responses are **not saved** in evaluation reports. Existing report files are not overwritten and Unix reports are created with private owner permissions.

The evaluator reports **suspected refusals**, term-preservation checks, failed calls and the raw case count; these are *heuristics*, **not** validated adult-compatibility scores or translation-quality rankings. Compare models using the same fixture and manually inspect output before recommending one.

## Current scope

| Subsystem | Implemented | Still pending |
|---|---|---|
| Library | None | Assets, revisions and permissions |
| Studio | Minimal task test fixtures | EPUB/PDF handling, translation editor and export |
| Discovery | HF/OpenRouter metadata, local Ollama inventory | Scheduled refresh, verified comparisons, provenance DB |
| Runtime | Ollama, OpenAI-compatible text API, GGUF download, llama-server launcher | Model formats beyond GGUF, GPU backends, persistent process manager |
| Evaluation | Local JSON test cases, metrics, private outputs | Human-review interface, calibrated benchmarks |

Docs: [architecture](docs/architecture.md), [P1 technical notes](docs/p1-model-runtime.md).

## License

**Not yet chosen.** This repository intends to be free and open source, but there is no grant of open-source redistribution/modification rights until the maintainer selects and adds a license. Do not assume missing licensing is permissive.

## P2 — Novel translation workflow (offline-testable)

**P2 is built on top of P1.** Import a UTF-8 TXT or DRM-free EPUB and checkpoint every translated segment (including chapter titles) in a private SQLite project. This is a text-only pipeline: images, EPUB layout, footnotes and complex formatting are not yet preserved.

Try an end-to-end **mock demonstration** (mock only labels and copies text; it does *not* translate):

```bash
python naughtyboddy.py novel init --input examples/sample-book.txt --project private/demo --glossary examples/sample-glossary.json
python naughtyboddy.py novel status --project private/demo
python naughtyboddy.py novel translate --project private/demo --provider mock --max-segments 100
python naughtyboddy.py novel audit --project private/demo
python naughtyboddy.py novel export --project private/demo --output private/demo.epub --allow-demo
```

For **real local model** inference once a compatible backend is running:

```bash
python naughtyboddy.py novel translate --project private/demo --provider ollama --model YOUR_LOCAL_MODEL --max-segments 20
# Or use --provider compatible --base-url http://127.0.0.1:8080/v1 --model YOUR_MODEL
```

For a **remote service**, pass `--accept-remote`; the book text is then sent to the selected provider and calls may incur fees. No cloud fallback or automatic upload occurs during import/status/export. All translation operations have a bounded call count per run.

Full scope, limitations and verification: [docs/p2-novel.md](docs/p2-novel.md). Pending live model tests and future work: [docs/TODO.md](docs/TODO.md).
