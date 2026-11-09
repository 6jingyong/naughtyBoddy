# P5.4 synthetic manga-translator-ui-shaped JSON

These files are **hand-authored synthetic input**, *not* output captured from any third-party executable. Source texts are artificial `SRC_Bxx` markers; translations are `TGT_Bxx` markers. Only six OCR rectangles and the image dimensions are populated.

- `upstream-project-good.json`: documented upstream project JSON shape including one absolute-image-key, image dimensions, OCR `lines` polygons and `text`/`translation` per region. The key is fake; `mask_raw` is an inert string not decoded by this adapter.
- `upstream-project-bad.json`: b02 is blank; b03 incorrectly contains b02's target sentinel. Should produce `wrong_target_token` and `shifted_target_token`.
- `region-id-map.json`: explicit synthetic region ID mapping with OCR-source guards and an optional bbox anchor, needed to run the P5.3 alignment check.

Usage: see [`docs/p54-comic-adapter.md`](../../docs/p54-comic-adapter.md).

All content is original synthetic fixture data. No external project's logo, screenshot, copyrighted comic page or model output is included.
