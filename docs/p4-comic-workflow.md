# P4 — Comic Studio (first runnable editing slice)

This is a local-first **editable page/region pipeline**, not a completed manga OCR/cleaning package.

## Workflow implemented

1. Import a PNG or JPEG page only after confirming rights to process it. Original bytes are retained in `workspace/comics/<id>/pages/`.
2. Create and manage pages and normalized `[x,y,width,height]` text boxes in `comic.json`.
3. Transcribe a dialogue region manually or replace the transcription with OCR output in a later adapter.
4. Translate a selected region using the existing Ollama, compatible API, or OpenRouter adapter. The application controls each step. **The model never chooses tools.** The mock provider returns `DEMO`, not a translation.
5. Review and edit both transcription and translation. Edits have monotonic region revisions; late model results cannot overwrite newer edits.
6. Export the current page as a **self-contained SVG** with an embedded original image and a basic white-box text overlay. Source files are never overwritten. Production-quality inpainting, multilingual typesetting and CBZ/PNG exports are deferred.

## Safety and privacy guarantees for P4

- The server is loopback-only; data-changing requests require the existing CSRF token.
- Image uploads limited to 12 MiB; parsed dimensions limited to 42 megapixels and 15,000 pixels on either axis. IDs are fixed 32-digit lowercase hex strings.
- Model inference is opt-in. For cloud providers and remote compatible URLs, explicit approval is required. No image bytes are sent to the translation model, only manually transcribed text.
- User text is HTML-escaped inside exported SVG. There is no auto-execution of OCR/model weights/plugins.
- Mock translations and incomplete source transcriptions cannot be silently exported as finished text.
- The output is a **draft**; do not publish without rights and human QC. Original artistic lettering, complex text placement, vertical orientation and SFX require dedicated processors.

## Next adapter work

- Evaluate Libre Manga Translator (AGPL-3.0-or-later), ComiTrans (inspect license before reuse), or isolated open OCR/segmentation/inpainting components. Do not copy AGPL code into a project with an undecided license.
- Introduce an OCR/region-detection adapter with a typed JSON contract: page dimensions, boxes, confidence, source, language, reading order.
- Add original-text masks and a clean-plate editing layer, then export raster PNG/CBZ and human-readable audit logs.
- Add batch/page checkpoint management and meaningful cancel/retry.
- Run actual visual QA in a local browser; this environment blocks headless Chromium loopback navigation.

## Local checks

`python -m unittest discover -s tests -v` and `node --check web/app.js`.

No live GPU, real adult-text inference, quality benchmark, or browser screenshot pass is claimed by the P4 tests.
