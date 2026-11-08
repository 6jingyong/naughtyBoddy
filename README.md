# NaughtyBoddy

**Local-first creative workbench for lawful adult-oriented fiction and multimedia.**

NaughtyBoddy is a standalone creative application, not a coding-agent fork or an extension of Human Harness. It combines a personal content library, editable production workflows, model discovery and replaceable inference runtimes. The software is free to use; **the repository does not have a license yet**, so redistribution/modification rights are not granted until the maintainer selects an OSI-approved license.

> Current status: **P4 experimental Studio with comic page/region editing**. No installer, full multimedia editor, official model ranking or live GPU verification yet.

## Try the Studio GUI (Python 3.11+, no dependencies)

```bash
python naughtyboddy.py studio
# Opens http://127.0.0.1:8765
# Optional: python naughtyboddy.py studio --port 8766 --workspace /path/to/private/workspace --no-browser
```

The browser-based GUI provides:

- **Library**: import permitted DRM-free EPUB or UTF-8 TXT (up to 12 MiB); also create multi-page PNG/JPEG comic projects (12 MiB per page). Keep sources in local project folders.
- **Studio**: select novel chapters, view source/translation side by side, edit and save segments, manage a JSON glossary, and export EPUB or TXT. **Comic Studio (P4)** lets users draw/edit region boxes on pages, transcribe source text, translate individual regions with a chosen model and export draft self-contained SVG overlays.
- **Discovery**: search installed Ollama models, Hugging Face models or OpenRouter metadata; names tagged `uncensored` / `abliterated` are **candidates only**, not verified compatibility scores.
- **Runtime**: run a **bounded** translation batch using mock/demo mode, a local Ollama server, an OpenAI-compatible endpoint (including llama.cpp / KoboldCpp) or OpenRouter. Each remote job requires explicit opt-in.
- **Local model manager (P3.1)**: inspect machine RAM/NVIDIA memory estimates, local Ollama inventory and managed GGUF files; inspect Hugging Face GGUF metadata; explicitly install GGUF/Ollama models; launch/stop a managed loopback llama-server; run three opt-in task-specific model evaluation cases. Results remain in your private workspace.

- **Task-aware routing (P3.2)**: rank *currently usable* local model endpoints; optionally request OpenRouter metadata. Model labels and heuristic refusal tests do not count as proof. Save explicit local, per-task user-reviewed compatibility/quality notes. Recommendations populate, but never execute, an inference choice. Cloud text transmission remains separately opt-in.

The P4 industry research is recorded in [docs/industry-workflows-2026.md](docs/industry-workflows-2026.md): proven creative pipelines are predominantly software-directed rather than tool-calling LLM agents. The **Pi integration decision** is documented in [ADR-001](docs/ADR-001-pi-integration.md): no Pi fork now. Existing deterministic creative workflows stay in Python; Pi's `pi-ai` and optional `pi-agent-core` are candidates for a future isolated SDK experiment only.

Demo mode **does not translate** text; it labels and copies original segments so the workflow can be tested without a model. Incomplete exports are blocked; mock-based exports require an explicit checkbox and carry an obvious DEMO label. A manually edited segment replaces its machine translation, without changing other completed segments.

The server listens on `127.0.0.1` only, uses a per-session write token and does not serve arbitrary files. It neither uploads documents during import, browse, edit, or discovery nor downloads model binaries automatically. Model transfers are started only after explicit user confirmation (and GGUF license review). Remote API calls transmit the selected source excerpts to that provider and may charge money. API keys are read from local environment variables (e.g. `OPENROUTER_API_KEY`) and are not stored in projects. The first browser launch may request access to loopback; do not publish/forward the local service to the Internet.

> **Note**: Web UI is an early implementation. It does not yet support video/PDF/OCR, comic inpainting or full typesetting, retaining original EPUB CSS/images, editing an existing CLI project through the Library, import of nonstandard/DRM-restricted files, cost prediction, automatic retry or job cancellation. See [docs/TODO.md](docs/TODO.md).

## Optional local models

Install inference runtimes separately:

- [Ollama](https://ollama.com/) server on `http://127.0.0.1:11434` — use `discover --source ollama` to inspect inventory.
- [llama.cpp](https://github.com/ggml-org/llama.cpp) or [KoboldCpp](https://github.com/LostRuins/koboldcpp) — use their OpenAI-compatible `/v1` endpoints in the GUI or CLI.

The GUI local-model manager uses the existing opt-in CLI operations. It **does not install llama.cpp binaries**, and GPU fit is a rough file-size estimate, not a compatibility guarantee. The CLI also supports opt-in model pulls and revision-pinned GGUF downloads:

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

P4 adds comic-region and API tests while retaining local-model GUI tests, explicit-install and managed-process lifecycle tests, and an optional offline evaluation interface. Tests use no real paid API and no GPU; **real adult-fiction compatibility, actual model quality and GPU deployment remain unverified**. A headless-browser visual check can be blocked by the runtime environment's local-network policy; HTTP integration tests still cover key API interactions.

Architecture: [docs/architecture.md](docs/architecture.md) · [P1](docs/p1-model-runtime.md) · [P2](docs/p2-novel.md) · [P3 Studio](docs/p3-studio.md) · [P3.1 local models](docs/p31-model-manager.md) · [P4 Comics](docs/p4-comic-workflow.md) · [Industry workflows](docs/industry-workflows-2026.md) · [Backlog](docs/TODO.md)

## Scope & boundaries

This project supports lawful fictional adult creativity with owned or properly licensed source material. It does not offer copyrighted-content mirrors or unauthorized scraping. It does not support exploitative material involving minors, non-consensual intimate imagery or deceptive real-person impersonation. Sources, licenses and platform rules continue to apply when using open models or third-party APIs.
