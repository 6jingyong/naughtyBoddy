# Architecture notes — initial direction

## Product boundaries

NaughtyBoddy is an independent, local-first multimedia creation application. It is **not** the Human Harness project and should not inherit a coding-agent's execution or approval model. Think *media library + creative editor + replaceable AI tools*, not *terminal assistant*.

## Four product subsystems

| Subsystem | Responsibilities | What it does **not** own |
|---|---|---|
| Library | Original assets, chapters, project manifest, revisions, rights/provenance metadata | Model inference |
| Studio | Task-specific interfaces, previews, reproducible transforms, export | Model discovery |
| Discovery | Public metadata; curated candidate sources; verified capability tests and benchmark provenance | Inference engine |
| Runtime | Local/remote inference adapters; permissioned network calls; timeout and cost budgets | Creative editor state |

## Model record, eventually

- Identity and source: provider, unique model ID, upstream/revision, license.
- Runtime: local GGUF/Safetensors artifact details or remote endpoint; device fit and cost.
- Supported modalities and technical features: context, vision, audio, tool use.
- Claimed low-refusal metadata **separate** from actual test outcomes.
- Task-specific measured performance: refusal and content omission rates, translation fidelity, latency, stability; benchmark version and sample count.
- Privacy: Never send user assets to a third party during discovery. Explicitly warn before cloud inference.

The current CLI intentionally implements only a thin fraction of this contract. Its `adult_compatibility: untested` field must never be presented as a verified ranking.

## Design choices

1. Local inference is first-class: start by discovering installed Ollama models; then support launching a GGUF through a dedicated backend. Do not build a custom inference engine.
2. Standard HTTP chat completion is the **transport** for language-model inference, not a universal model capability schema. Image/video engines need distinct adapters.
3. Discovery and execution are decoupled. Provider outages, model changes, and content restrictions must not erase work or alter previous outputs.
4. Editable project artifacts and deterministic file conversion are foundational. Translation, for example, should use paragraph IDs, glossary, checkpoints and export independent of LLM output.
5. No broad web mirroring or unauthorized scraping. Third-party sources should be permission-aware connectors; obey access restrictions and licensing.
6. No untrusted model downloads or plugin installs without user approval. Keep prompts, project files and API credentials local unless the user knowingly chooses a remote provider.

## First concrete acceptance criteria

- Listing Ollama inventory works without uploading documents or saving credentials.
- OpenRouter and Hugging Face discovery works without claiming keywords prove low-refusal behavior.
- An explicit probe works with one local Ollama model and one OpenAI-compatible endpoint.
- Failure of one provider is visible, not silently disguised as zero available models.
- Offline parser/mock tests pass.

## Open design decisions

- Final project license (MIT, Apache-2.0, AGPL-3.0, or another choice).
- UI stack (desktop shell + local service vs browser-only). Decide after a working pipeline.
- Benchmark methodology for lawful adult-fiction compatibility, translation quality and refusals.
- GPU/device management strategy and external source connector permission model.
