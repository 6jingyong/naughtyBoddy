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
- [ ] Add semantic quality checks, consistent naming/pronouns and editable side-by-side human review.
- [ ] Proper retry, backoff, progress events, true cost estimator and provider-specific output token budgets.
- [ ] More formats: PDF, OCR, markdown and HTML, using dedicated parsers.
- [ ] Support structured model output / batch translation, manual corrections and version history.
- [ ] Robust cancellation/stale-lock recovery, crash-hardening and cross-platform tests.

## P3 — Creative workbench

- [ ] Design Library/Studio/Discovery views around content artifacts, not chat/terminal commands.
- [ ] Local desktop packaging with privacy-first project folders and model switching.
- [ ] Media-specific pipelines: comics, subtitle/video processing, interactive fiction.
- [ ] Permission-aware external source connectors; no unauthorized mirror scraping.
- [ ] Finalize OSI-approved license after owner selection (repository currently has no LICENSE file).
