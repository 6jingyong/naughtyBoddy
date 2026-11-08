# NaughtyBoddy

**An open, user-sovereign ecosystem for lawful adult AI creativity.**

**NaughtyBoddy 不是一个要与其他 NSFW 创作软件争夺用户的“万能 Agent”。** 我们希望帮助任何人发现、理解、使用、改进已有的创作能力，并在真正存在需求缺口时创造新的工具。好用的社区项目不是竞争对手，而是值得推荐、贡献和共同建设的成果。

NaughtyBoddy is an **independent, local-first initiative** for lawful adult-oriented fiction and multimedia. Its direction is **Discovery → Infrastructure → Gap-driven Innovation**, rather than a monolithic NSFW agent or a fork of Pi, Codex, or Human Harness. It aims to improve access to existing creative tools, not replace them.

> **Development status:** exploratory P0–P4 prototypes exist (model discovery, local inference adapters, editable novel and comic workflow demos). **P5 is a direction change toward a needs-and-solutions knowledge base.** These prototypes are not evidence of production readiness, real model quality, or a complete adult-creation platform.

> **Licensing notice:** Software is intended to be free and open source, but this repository **does not yet contain a LICENSE**. Until a license is explicitly selected and added, public visibility is **not** permission to copy, modify, or redistribute the code. See the licensing TODO. Upstream model and tool licenses are separate.

## Mission · 我们希望解决什么

The objective is not profit maximization, platform lock-in, or assembling another directory of provocative AI websites. It is to make *useful creative capabilities* more accessible without sacrificing individual control.

We evaluate solutions along five user-facing dimensions:

| Principle | What success means |
| --- | --- |
| **Quality · 高质量** | Real task completion, faithful transforms, editable results, consistent characters and terminology; not benchmark hype. |
| **Privacy · 隐私** | Local-first assets, transparent network boundaries, no silent uploads or telemetry, explicit consent for remote processing. |
| **Uniqueness · 独特性** | Supports uncommon creative intentions, niche workflows and personal styles, not only generic text/image generation. |
| **Accessibility · 易获取** | Reachable on modest hardware, clear setup, documented costs, discoverable tools and reproducible workflows. |
| **User sovereignty · 用户自主权** | Portable files, modifiable workflows, replaceable models and runtimes; no forced ecosystem or vendor dependence. |

**Our default response to a user need:** find good existing tools → verify the experience and constraints → recommend and document them → contribute fixes/adapters upstream → build a new specialized workflow or infrastructure only for a confirmed gap.

**Existing NSFW tools are collaborators and references, not adversaries.** A successful recommendation or upstream patch is as valuable as a new NaughtyBoddy feature.

## What we're building next · P5

P5 focuses on a **Needs → Solutions → Gaps** registry: user jobs-to-be-done, current tools/workflows, hardware and license requirements, verifiable evidence, unresolved friction and reproducible evaluations. Discovery should search for **usable solutions** (not just model names). Infrastructure should lower integration friction while retaining the option of standalone specialist tools.

The design assumes **local low-refusal models may have poor or no tool-calling capability**. Deterministic software owns task steps, state, retries and exports; models perform explicit inference steps. Optional agent planners must not become a dependency for basic workflows.

We do **not** claim that a project's `uncensored` / `abliterated` label guarantees adult-content compatibility, fidelity, or safety. Those properties require versioned, task-specific real tests. Unperformed hardware/browser/provider checks remain in [the backlog](docs/TODO.md).

Contributions are welcome as **documented use cases, reproducible gaps, evidence, source-verified tool information and proposed integrations**. Never include private prompts, personal content, credentials, or unlicensed source material in a public issue.

### Explore the P5 registry (offline)

```bash
python nb_registry.py validate
python nb_registry.py needs
python nb_registry.py solutions
python nb_registry.py match need-manga-localization
python nb_registry.py gaps
```

Records are plain JSON with explicit evidence status. P5 currently contains **proposed needs and unverified tool candidates**, not a verified best-tools ranking. Read the [P5 contribution and validation guide](docs/p5-needs-registry.md) before asserting a tool works or a market gap exists. The initial registry needs no API key, model, GPU or network connection.

## Existing prototype (P0–P4)

The current code is a *testbed*, not a commitment to implement every vertical editor in-house. Its novel/comic workflows can serve as references for external integration. The GUI is experimental and real GPU/model evaluation is deferred.

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
