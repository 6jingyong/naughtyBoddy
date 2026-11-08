# NaughtyBoddy

**Local-first creative workbench for lawful adult-oriented fiction and multimedia.**

NaughtyBoddy is a standalone creative application, not a coding-agent fork or an extension of Human Harness. It combines a personal content library, editable production workflows, model discovery and replaceable inference runtimes. The software is free to use; **the repository does not have a license yet**, so redistribution/modification rights are not granted until the maintainer selects an OSI-approved license.

> Current status: **P3 experimental, working local browser-based Studio**. No installer, model download GUI, full multimedia editor, official model ranking or live GPU verification yet.

## Try the Studio GUI (Python 3.11+, no dependencies)

```bash
python naughtyboddy.py studio
# Opens http://127.0.0.1:8765
# Optional: python naughtyboddy.py studio --port 8766 --workspace /path/to/private/workspace --no-browser
```

The browser-based GUI provides:

- **Library**: import permitted DRM-free EPUB or UTF-8 TXT (up to 12 MiB); keep source and checkpoint database in a local project folder.
- **Studio**: select chapters, view source/translation side by side, edit and save segments, manage a JSON glossary, view progress/audit, export EPUB or TXT.
- **Discovery**: search installed Ollama models, Hugging Face models or OpenRouter metadata; names tagged `uncensored` / `abliterated` are **candidates only**, not verified compatibility scores.
- **Runtime**: run a **bounded** translation batch using mock/demo mode, a local Ollama server, an OpenAI-compatible endpoint (including llama.cpp / KoboldCpp) or OpenRouter. Each remote job requires explicit opt-in.

Demo mode **does not translate** text; it labels and copies original segments so the workflow can be tested without a model. Incomplete exports are blocked; mock-based exports require an explicit checkbox and carry an obvious DEMO label. A manually edited segment replaces its machine translation, without changing other completed segments.

The server listens on `127.0.0.1` only, uses a per-session write token and does not serve arbitrary files. It neither uploads documents during import, browse, edit, or discovery nor downloads model binaries automatically. Remote API calls transmit the selected source excerpts to that provider and may charge money. API keys are read from local environment variables (e.g. `OPENROUTER_API_KEY`) and are not stored in projects. The first browser launch may request access to loopback; do not publish/forward the local service to the Internet.

> **Note**: Web UI is an early implementation. It does not yet support video/PDF/OCR, retaining original EPUB CSS/images, drag-and-drop model installation, editing an existing CLI project through the Library, import of nonstandard/DRM-restricted files, cost prediction, automatic retry or job cancellation. See [docs/TODO.md](docs/TODO.md).

## Optional local models

Install inference runtimes separately:

- [Ollama](https://ollama.com/) server on `http://127.0.0.1:11434` — use `discover --source ollama` to inspect inventory.
- [llama.cpp](https://github.com/ggml-org/llama.cpp) or [KoboldCpp](https://github.com/LostRuins/koboldcpp) — use their OpenAI-compatible `/v1` endpoints in the GUI or CLI.

The existing CLI also supports opt-in model pulls and verified-revision GGUF downloads:

```bash
python naughtyboddy.py hardware
python naughtyboddy.py discover --source huggingface --query abliterated --limit 10
python naughtyboddy.py local list-gguf --repo OWNER/MODEL
python naughtyboddy.py local download-gguf --repo OWNER/MODEL --filename FILE.gguf --accept-download
python naughtyboddy.py local fit-gguf --model-path /path/to/model.gguf
python naughtyboddy.py local serve-gguf --model-path /path/to/model.gguf --port 8080
```

Review the upstream model's legal rights, provenance, license, storage and hardware needs before downloading. A model advertised as low-refusal may still omit material, refuse legitimate content or hallucinate. Quantized models vary widely in quality and resource requirements.

## CLI novel workflow

```bash
python naughtyboddy.py novel init --input examples/sample-book.txt --project private/demo --glossary examples/sample-glossary.json
python naughtyboddy.py novel status --project private/demo
python naughtyboddy.py novel translate --project private/demo --provider mock --max-segments 20
python naughtyboddy.py novel audit --project private/demo
# Only when all segments are complete:
python naughtyboddy.py novel export --project private/demo --output private/demo.epub --allow-demo
```

Use `--provider ollama --model YOUR_LOCAL_MODEL` for a running local Ollama model, or `--provider compatible --base-url http://127.0.0.1:8080/v1 --model YOUR_MODEL`. Remote services require `--accept-remote`. The project checkpoint database survives model switches.

## Development checks

```bash
python -m unittest discover -s tests -v
node --check web/app.js     # optional, requires Node.js
```

P3 adds HTTP/API tests, mock workflow tests and a local GUI. Tests use no real paid API and no GPU; **real adult-fiction compatibility, actual model quality and GPU deployment remain unverified**. A headless-browser visual check can be blocked by the runtime environment's local-network policy; HTTP integration tests still cover key API interactions.

Architecture: [docs/architecture.md](docs/architecture.md) · [P1](docs/p1-model-runtime.md) · [P2](docs/p2-novel.md) · [P3 Studio](docs/p3-studio.md) · [Backlog](docs/TODO.md)

## Scope & boundaries

This project supports lawful fictional adult creativity with owned or properly licensed source material. It does not offer copyrighted-content mirrors or unauthorized scraping. It does not support exploitative material involving minors, non-consensual intimate imagery or deceptive real-person impersonation. Sources, licenses and platform rules continue to apply when using open models or third-party APIs.
