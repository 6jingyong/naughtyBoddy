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
- [x] P4 first comic page/region manual editing and SVG draft export (no OCR/inpainting yet).
- [ ] Remaining media-specific pipelines: automated comics, subtitle/video processing, interactive fiction.
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

## P4 — Comic workflow (offline slice completed)

- [x] PNG/JPEG page import with user permission confirmation, bounded images and multi-page project metadata.
- [x] Draw/edit normalized dialogue boxes and original/translated text in a separate local comic library.
- [x] Translate individual regions through existing model adapters; model tool calling not required.
- [x] Revision conflict checks, mock/demo labeling, draft SVG export with escaped user content, HTTP tests.
- [ ] Plug in automated bubble detection/OCR and preserve reading order; evaluate existing dedicated engines and licenses.
- [ ] Non-destructive text removal, typography control and production PNG/CBZ export.
- [ ] Browser UI visual verification (headless Chromium blocked by local-network policy in current environment).
- [ ] Real-image/manual quality review and multilingual translation QA.

## P5 — Open ecosystem, needs → solutions → gaps (initial implementation)

- [x] Rewrite README toward quality, privacy, uniqueness, accessibility, user sovereignty and upstream collaboration.
- [x] Build a small offline, schema-checked registry of needs, candidate solutions, assessments and falsifiable gaps.
- [x] Add a CLI to inspect candidate solutions without treating metadata/tag matches as tested compatibility.
- [x] Add tests that reject unsubstantiated compatibility verdicts, broken references and malformed records.
- [ ] Validate user demand through real usage/interviews; **all current seed needs and gap descriptions are hypotheses, not measured market findings**.
- [ ] Review source documentation and actual licenses for candidate tools; record dated evidence, versions and relevant restrictions.
- [ ] Hands-on task-specific evaluations (hardware, privacy, adult-fiction compatibility, output quality) when real equipment and test data are available.
- [ ] Add a read-only registry browser to the Studio; not an automatic installer or unauthorized content connector.
- [ ] Consider cross-tool workflows and upstream contributions only after a reproduced compatibility problem is recorded.

## P5.2 — Source-linked user frictions

- [x] Preserve actual upstream docs, user issues, and community reports as separate evidence types.
- [x] Record existing mitigations before proposing any duplicate NaughtyBoddy work.
- [x] Link friction records to needs, candidate solutions, and hypotheses; provide offline CLI filtering.
- [x] Construct offline *synthetic fault-injection* fixtures for EPUB tag coverage, bubble IDs and fictional character knowledge visibility (P5.3).
- [ ] **Independently reproduce the actual upstream software issues** on explicit versions using licensed or synthetic input; synthetic checks alone do not establish upstream defects.
- [ ] Recheck upstream issue states/fixes on specific releases; GitHub issue 'open' is not proof a problem occurs in current version.
- [ ] Collect user corrections and negative cases without asking for or publishing private NSFW artifacts.

## P5.3 — Portable synthetic acceptance contracts

- [x] Add a self-contained 2-chapter EPUB3 example with real OPF/spine packaging and 8 stable text markers.
- [x] Detect missing, untranslated and swapped fixture segments; bound ZIP input size and reject unsafe member paths.
- [x] Add six-bubble target-ID checks and four-character per-context-channel fact visibility checks.
- [x] Provide expected-pass and expected-fail examples, CLI and CI; no real model inference required.
- [ ] Build an **opt-in** adapter against one mature upstream project on rights-cleared materials; never claim a synthetic failure is an upstream bug.
- [ ] Design human evaluation for translation fidelity and genuine model refusal behavior; exact fixture token matching is not a semantic score.

## P5.4 — Manga translation interchange and stable region IDs

- [x] Define `nb-comic-regions-v1` with opaque page alias, source/translation, normalized bounding box, explicit ID provenance.
- [x] Implement a **read-only** converter for the documented single-image project JSON format of hgmzhn/manga-translator-ui.
- [x] Verify index/source/optional bbox mapping, rejecting changed OCR text, reordered regions, malformed coordinates and duplicated IDs.
- [x] Pass the P5.3 six-bubble synthetic positive and shifted-ID negative controls without inference or network calls.
- [x] Keep absolute source image paths, masks and upstream edit metadata out of normalized output and logs; private translated text is written only at an explicitly provided path.
- [ ] Obtain and test a **real, properly authorized export** from a pinned upstream release; current fixtures only match the **documented shape**.
- [ ] Verify actual data exports for Koharu and ComiTrans before claiming an adapter for them; no guessed schemas.
- [ ] Measure real OCR/text alignment and semantic translation quality on owned/licensed content; P5.3 marker checks do not establish real fidelity.

## P5.5 — Choice-only solution finder

- [x] Four predefined questions (task, privacy, hardware, main preference), no free-text input or LLM.
- [x] Read-only local catalogue results with clear workflow/extension/backend roles and documentation links.
- [x] Show unknown local support separately; never fabricate GPU fit, adult compatibility, ease-of-installation scores or privacy audit.
- [ ] Test the visual interaction and keyboard focus in a browser on an environment that permits localhost access.
- [ ] Expand user choice vocabulary only when actual evidence supports useful distinctions.
- [ ] Verify real tool compatibility, model-specific hardware and data boundaries (deferred live tests).

## P5.6 — Tag-based external-directory Discovery

- [x] Import factual candidate labels from four public external directory lists, with pinned GitHub SHA, source URL and license attribution.
- [x] Preserve old project documentation-review profiles and avoid promoting third-party tags into verified capability scores.
- [x] Replace the fixed four-question Discovery page with multi-select tags: same facet OR; cross-facet AND.
- [x] Keep all filtering local, no user free text, no model calls, no automatic installer.
- [ ] Cross-check source entries against official project sites and current release status.
- [ ] Browser visual and accessibility QA on an environment permitting localhost.
- [ ] Research more fine-grained verified tags for workflows and quality (do not invent benchmark data).

## P5.7 — Documented fine-capability discovery

- [x] Source-reviewed, conditions-aware capability tags with strict item IDs and stable evidence links.
- [x] Add specific capability facet and per-item evidence/conditions disclosure in /discover.
- [x] Avoid treating indirect model backends, lorebooks, chat history and privacy as interchangeable.
- [x] Narrow the BBM EPUB tag-selection issue to actual limited translation modes.
- [ ] Test installed tool and model versions with appropriate authorized/synthetic samples.
- [ ] Fix stale and moved upstream URLs; broaden capability coverage only with primary documentation.
- [ ] Run browser visual and keyboard accessibility checks outside CI.

## P5.8 — Catalogue health and careful deduplication

- [x] Confirm official ComfyUI GitHub migration and reconcile duplicate display cards without discarding old source attribution.
- [x] Capture a date-stamped partial GitHub repository API spot-check, with archived flag/last pushed timestamp and explicit limits.
- [x] Treat conflicting metadata (including a 404 with a recently indexed source) as **needs review**, not as proof of deletion.
- [x] Report shared destination URLs and same-name/different-URL groups without merging distinct models.
- [x] Show check provenance/unknown status in Discovery; no automatic network calls on tag selection.
- [ ] Cross-check the unresolved Libre Manga Translator repository-API result independently.
- [ ] Expand link metadata coverage beyond the sampled GitHub projects, especially hosted service links.
- [ ] Review real releases and update capability descriptions that may be stale; do not infer abandonment from old code push.
- [ ] Browser visual/keyboard QA on a machine with full UI support.

## P5.9 — Text-first scope reduction

- [x] Restrict public Discovery to text-only projects, text models, roleplay, long-form fiction/translation and compatible local runtimes.
- [x] Preserve image/video/audio/manga directory snapshots, adapter experiments, synthetic fixtures and P4 editor as archived work; do not destroy previous data.
- [x] Use a separate deterministic text-only API projection; eliminate image, video, audio and multimedia filters from public Discovery.
- [x] Maintain local-only original catalogue API for existing research tools/tests; no LLM or network required to filter tags.
- [ ] Verify real text workflow usability, versioned local-model compatibility and privacy boundaries using authorized or synthetic text only.
- [ ] Prioritize roleplay memory isolation, ebook translations, reproducible text quality/fidelity evaluation and true runtime availability.
- [ ] Consider whether to move archived media tools out of the visible Studio UI completely after user-facing migration and data retention are verified.
