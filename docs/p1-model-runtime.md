# P1 — model runtime and discovery verification

## Goals

- Let creators choose between a local Ollama model, a local GGUF served by llama.cpp, and a cloud OpenAI-compatible model.
- Inspect local system RAM and NVIDIA VRAM without uploading device information.
- Download selected public GGUF quantizations with a fixed Hugging Face revision and explicit user approval.
- Evaluate lawful adult-fiction task completion without conflating marketing labels or non-refusal with faithful completion.

## Data and trust boundaries

- Discovery accesses only model **metadata** from Hugging Face/OpenRouter and the chosen local Ollama inventory.
- Downloading GGUF is a large, opt-in network/disk operation. Model cards, upstream licenses and provider conditions are the user's responsibility. Files are **data**, never executed as scripts.
- `local serve-gguf` executes only a backend binary explicitly installed/selected by the user, in foreground, bound to loopback. The model file is validated as a present `.gguf` path; the extension is not a guarantee of trusted content.
- `evaluate` sends full prompts only to the selected model. It needs `--accept-remote` before a remote service is contacted. The P0 `probe` is already an explicit operation and may contact a chosen cloud provider.
- Evaluation results contain only case identifiers and heuristic flags unless user enables full response capture. No automatic sharing or background updates.
- Remote API authentication and any adult-content provider policy are the user's responsibility. Never upload sensitive documents for a public benchmark.

## Benchmark limitations

- Keyword refusal detection may miss euphemistic refusals and produce false positives.
- `expected_terms` checks literal string retention, which can fail for acceptable paraphrases and pass on a meaningless response.
- Adult compatibility and fiction quality remain `needs_human_review`. No safety-guardrail bypass is performed against third-party provider APIs.
- There is no model leaderboard or automatic rerouting in P1. Such actions would require real evaluation data, context limits, cost controls and authorization.

## P1 acceptance matrix

| Scenario | Expected |
|---|---|
| No GPU / no Ollama installed | `hardware` reports detected facts; `discover ollama` yields explicit error, not a fake empty catalog |
| Install without `--accept-download` | No API request or download |
| Hugging Face candidate | GGUF filenames, current commit, available license/gated metadata shown |
| Bad model path / traversal | Reject before download |
| Failed transfer | Keep `.part` + provenance for resume; do not output incomplete final GGUF |
| Local GGUF launch | Foreground `llama-server` binds loopback; needs installed binary |
| Cloud benchmark without consent | Refuse before sending a prompt |
| Benchmark report | Manual-review marker, failures visible, no implied compatibility verdict |
| Existing report path | Refuse overwrite |

### Beyond P1

Next: integrated local model manager GUI, compatibility tests on actual GPU hardware, support for Mac/AMD accelerator inventory, and an EPUB/TXT translator with paragraph IDs, glossary, checkpoints, and deterministic export. Do not build a text-only chat app as the final product.
