# NaughtyBoddy development TODO

This backlog tracks work intentionally **deferred**, including real-world testing that cannot currently be performed. Do not turn simulated/in-memory passes into live verification claims.

## P1.1 — Real hardware/model testing (deferred, non-blocking)

- [ ] Test real NVIDIA/AMD/Apple hardware inventory and GGUF memory-fit estimates across operating systems.
- [ ] Download a genuine public GGUF, verify provenance and checksum from an authoritative release, and exercise resume on interrupted transfer.
- [ ] Launch llama.cpp / KoboldCpp with a real local model; record startup errors, GPU/RAM usage, output and latency.
- [ ] Run a real Ollama-pulled model and ensure CLI discovery and inference work end-to-end.
- [ ] Exercise permitted hosted API calls and inspect error, rate-limit, billing and privacy behavior.
- [ ] Manually assess legal adult-fiction translation compatibility; record benchmark set, model revision, evaluator notes, refusal/omission caveats.

## P2 — Novel workflow follow-ups

- [x] TXT and ordinary EPUB import with OPF/spine order, chapter/paragraph IDs and source fingerprint.
- [x] Persistent per-segment translation checkpoints; resumption after a mid-job failure.
- [x] Editable glossary, audit flags, explicit cloud opt-in, bounded call count.
- [x] Refuse incomplete export, mark mock/demo output, normalized TXT/EPUB export and offline tests.
- [ ] Test generated EPUB with epubcheck and multiple actual e-reader applications.
- [ ] Preserve EPUB illustrations, cover, footnotes, formatting and navigation where rights and format permit.
- [x] Add manual side-by-side editing interface and configurable glossary.
- [ ] Add semantic quality checks, consistent naming/pronouns and review resolution workflow.
- [ ] Proper retry, backoff, progress events, true cost estimator and provider-specific output token budgets.
- [ ] More formats: PDF, OCR, markdown and HTML, using dedicated parsers.
- [ ] Support structured model output / batch translation, manual corrections and version history.
- [ ] Robust cancellation/stale-lock recovery, crash-hardening and cross-platform tests.

## P3 — Creative workbench

- [x] Build first Library/Studio/Discovery GUI around content artifacts, not chat/terminal commands (P3).
- [x] Local browser-based Studio with private projects, side-by-side edits, glossary, explicit model selection.
- [ ] Package local Studio for desktop (Windows/macOS/Linux); preserve user data between upgrades.
- [ ] Media-specific pipelines: comics, subtitle/video processing, interactive fiction.
- [ ] Permission-aware external source connectors; no unauthorized mirror scraping.
- [ ] Finalize OSI-approved license after owner selection (repository currently has no LICENSE file).

## P3.1 — UI and operational robustness

- [ ] Real browser visual/interaction QA on machines where Playwright loopback navigation is permitted; responsive, keyboard and accessibility tests.
- [ ] P1.1 real model/download/GPU/paid API tests remain deferred.
- [ ] Persist pending job records, cancellation, stale-lock recovery and bounded retries.
- [x] P3.1 GUI for local model metadata, explicit GGUF/Ollama downloads, managed llama-server launch/stop and fixed evaluation samples (offline tests).
- [ ] Validate GGUF download progress, real backend startup/readiness, file integrity, and downloads on real hardware (P1.1 deferred).
- [ ] UI job cancellation, persistent job history, crash recovery and resumable retries; only best-effort progress implemented.
- [ ] Project-level glossary edit revisions, conflict protection on concurrent edits and export checklists.
- [ ] Model routing by adult-fiction compatibility + translation quality; benchmark methodology and manual review. P3.1 only collects heuristic test results.
- [ ] Usage/cost estimates and actual token usage when returned by provider.
- [ ] Import existing P2 CLI projects into the GUI Library without copy or data loss.

## P3.2 — Profiles and conservative routing (implemented offline, live validation deferred)

- [x] Local manual profile store, explicit per-task compatibility and quality review, atomic private persistence.
- [x] On-demand routing from available local models and optionally OpenRouter metadata, with evidence status visible.
- [x] Do not use abliterated/uncensored keywords as verified ratings; no automatic model execution or cloud content transfer.
- [ ] Test real provider catalogs under rate limits, model retirement, availability and permission changes.
- [ ] Develop reproducible consenting-adult fiction benchmarks and reviewer protocol; current records are user reviews only.
- [ ] Improve tasks-specific vision/audio model capability metadata and work with image/video adapters.
- [ ] Optional integration spike: Pi AI/agent-core SDK as replaceable orchestration, not as a forked GUI/creative core (see ADR-001).
