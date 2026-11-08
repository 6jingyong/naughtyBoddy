# P3.1 — local model management in Studio

## Added UI operations

Open **本地模型管理** in the right inspector. The main Studio remains a project/novel editor, not a coding-agent shell.

- Detect host OS, RAM and NVIDIA GPU free memory. Non-NVIDIA accelerators are reported as unknown, not absent.
- Display installed local Ollama models and GGUF files under the Studio workspace's `models/` folder.
- Inspect Hugging Face model metadata, listed GGUF files, revision and license. A model label is never proof of adult-content compatibility.
- Download a selected, revision-pinned GGUF into the private workspace, with consent and a 1–32 GiB transfer cap; observe job status and received bytes. Download resumes from `.part` where supported.
- Request installation via **local** Ollama with explicit confirmation. Requires an Ollama server already running at its usual localhost address.
- Start/stop a managed `llama-server` process for an already downloaded GGUF. Requires `llama-server` on PATH. Only `127.0.0.1` is used; shell commands and user-supplied executables are disallowed.
- Run the fixed local `examples/translation_eval.json` sample suite only on request. Three cases provide heuristic flags and explicit manual review status; there is **no** automatic NSFW score or model leaderboard.

## Operational boundaries

- Model search/metadata may access Hugging Face/OpenRouter online, but never sends a user's book to them.
- GPU estimate is `GGUF file size + 2 GiB reserve` and does not predict actual model loadability, KV cache requirements or inference performance.
- Model download does not execute the GGUF or install backends. Review the upstream model license and model card before confirming.
- The managed process is only held while Studio runs; Studio shutdown terminates that process. The health endpoint distinguishes starting from responding, but a successful health response does not establish quality or safety.
- Private evaluation summaries live in `workspace/private/evaluations/`, without full prompts or responses. The GUI cannot issue arbitrary filesystem/shell commands.
- Jobs live in memory; interruptions are not automatically recovered, although GGUF partial transfers can be resumed. Do not claim cancellation or persistent job history.
- Do not use downloaded models to create illegal sexual content, exploitative content involving minors, nonconsensual intimate imagery or infringing reproductions.

## Offline validation

```bash
python -m unittest discover -s tests -v
node --check web/app.js
python naughtyboddy.py studio
```

Real model inference, GPU performance, service packaging, and browser visual QA remain deferred in `docs/TODO.md`.
