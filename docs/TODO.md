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
- [ ] Manage local GGUF downloads, launch inference engines, detect Ollama status from the GUI (CLI-only currently).
- [ ] Project-level glossary edit revisions, conflict protection on concurrent edits and export checklists.
- [ ] Model routing by adult-fiction compatibility + translation quality; benchmark methodology and manual review.
- [ ] Usage/cost estimates and actual token usage when returned by provider.
- [ ] Import existing P2 CLI projects into the GUI Library without copy or data loss.
