# ADR-001: Pi integration is optional, not an upstream fork

Status: **proposed** (2026-11-09). No Pi dependency has been added.

## Decision

NaughtyBoddy stays a standalone creative studio: Library/Studio/Discovery/Runtime.
Retain deterministic pipelines for books, comics, OCR and media conversion. Small
community fine-tuned models often lack reliable tool calling, so their inclusion
must not depend on running a tool-using autonomous agent.

Evaluate the maintained Pi project (`earendil-works/pi`, formerly `badlogic/pi-mono`)
for **specific reusable components**, not as the repo's base:

1. `@earendil-works/pi-ai`: a possible alternate model/provider adapter; first
   test compatibility with local Ollama/llama.cpp/KoboldCpp and cloud providers.
2. `@earendil-works/pi-agent-core`: optional free-form orchestration for genuinely
   exploratory content tasks, with a strict allowlist of creative tools.
3. Pi SDK and extensions: may be used for an isolated experiment. Do not inherit
   the coding CLI, shell/file-edit permissions, conversation-first UX or project schema.
4. Keep model discovery/routing, copyright and consent checks, model profiles,
   asset storage and workflow checkpoints under NaughtyBoddy control.

## Why no full fork now?

- Coding-agent defaults are not a good foundation for non-chat editors and media timelines.
- Python local models and EPUB workflows already work without a Node agent runtime.
- A full fork creates substantial upstream merge pressure.
- Pi's extensions can run with process privileges; arbitrary extensions and model
  downloads must not be auto-executed on a user's personal creative assets.
- Replacing transport/routing prematurely would destroy tests without proving
  benefit; Pi may help later with provider diversity and complex tool coordination.

## Integration gate

Only introduce Pi as an **optional adapter**, in a separate branch, after tests
verify two real local models (including non-tool-calling models), one cloud
provider, consent prompts, sandboxed tools, text privacy, checkpoint recovery,
and parity with existing translation quality. Pin exact package versions.

## Sources checked

- https://github.com/earendil-works/pi
- https://pi.dev/docs/latest/sdk
- https://pi.dev/docs/latest/extensions

Pi's current package names are under `@earendil-works/`, not historical
`@mariozechner/` names. MIT licensing applies to Pi, not to user assets or
to third-party model weights. NaughtyBoddy's own license remains undecided.
