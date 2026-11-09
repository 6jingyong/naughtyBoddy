# P5.4 — Comic region interchange adapter (2026-11-09)

**Purpose:** help external manga-localization applications feed *existing*, synthetic **P5.3 structural** tests without implementing an OCR, translation or inpainting engine in NaughtyBoddy. The adapter reads JSON only, makes **no network requests and does not modify the upstream project**.

## Source evidence and compatibility boundary

- **First documented adapter:** [hgmzhn/manga-translator-ui](https://github.com/hgmzhn/manga-translator-ui). The [official troubleshooting guide](https://hgmzhn.github.io/manga-translator-ui/en/troubleshooting/output-json-and-rendering) says its `*_translations.json` project file is a nonempty object keyed by the source image path. Each value is either a legacy region list or a dict containing `regions`. Regions use `text`, `translation`, and quadrilateral `lines`; a project may contain `original_width`, `original_height`, masks, layout and editor state. The [export guide](https://hgmzhn.github.io/manga-translator-ui/en/desktop/translation/output-directory-and-workflow.html) documents saving project JSON and editable sidecars.
- This project is **not Koharu, ComiTrans or mrdhnto/Libre Manga Translator**; its JSON structure must not be casually assumed compatible with theirs. Koharu documents PSD/image outputs, ComiTrans documents batch/page editing, but we have not established an equivalent stable region JSON contract for either. Adapt those only after a documented or licensed real export is available.
- All examples here are hand-built **schema-shaped synthetic fixtures**. They were **not exported by or executed against** manga-translator-ui. Actual-version compatibility is **pending**.

## Normalized interchange contract

A local `nb-comic-regions-v1` document contains:

```json
{
  "schema_version": 1,
  "contract": "nb-comic-regions-v1",
  "page_id": "synthetic01",
  "id_stability": "mapped_source_guard",
  "source_format": "manga-translator-ui-project-json",
  "regions": [
    {"id": "b01", "source": "SRC_B01_START", "translation": "TGT_B01",
     "bbox": [0.016667, 0.025, 0.15, 0.075], "reading_order": 0}
  ]
}
```

`bbox` uses normalized 0–1 coordinates. `page_id` is an opaque alias, **never the original file path**. The adapter intentionally drops masks, image paths, styles, provider credentials and other fields. The output **does include source and translated text**, so keep it local; it is private creative material and must never be submitted as a public issue attachment without consent and rights.

`id_stability` determines whether **P5.3** alignment checks are meaningful:

- `positional_unstable`: generated `pos-0001`, `pos-0002`... from source region order. **No stable-ID audit is permitted**. A rerun may reorder regions.
- `mapped_source_guard`: an explicit separate map binds each source region index to a P5.3 ID and original OCR text, with optional normalized `bbox` anchor. Changed text/order/geometry makes conversion **fail closed**, not silently remap.
- `explicit_ids`: a native contract supplied by a system that manages its own stable IDs; downstream must still evaluate whether that system's ID persistence is trustworthy.

Repeated OCR strings (e.g. "Yes") are ambiguous and need bbox anchors. Even the explicit map is a test *contract*, not proof that natural-language translations are mapped semantically to the correct speaker.

## Offline commands

Python 3.11+, standard library only:

```bash
# Inspect a source's region count and ID status without printing private text:
python nb_comic_adapter.py import --format manga-translator-ui \
  --input benchmarks/p54/upstream-project-good.json --page-id synthetic01

# Bind IDs to source OCR strings, audit the P5.3 synthetic six-bubble fixture:
python nb_comic_adapter.py import --format manga-translator-ui \
  --input benchmarks/p54/upstream-project-good.json \
  --mapping benchmarks/p54/region-id-map.json \
  --audit-case benchmarks/p53/comic_case.json

# An intentionally shifted synthetic candidate must exit nonzero and list bubble IDs:
python nb_comic_adapter.py import --format manga-translator-ui \
  --input benchmarks/p54/upstream-project-bad.json \
  --mapping benchmarks/p54/region-id-map.json \
  --audit-case benchmarks/p53/comic_case.json

# Explicitly write normalized, **private** contract for use by other tools:
python nb_comic_adapter.py import --format manga-translator-ui \
  --input /path/to/your/local/project.json \
  --page-id page001 --mapping /path/to/private/map.json \
  --output /path/to/private/normalized.json

# Native-contract checks on the synthetic fixture:
python nb_comic_adapter.py audit --input /path/to/private/normalized.json \
  --case benchmarks/p53/comic_case.json

python -m unittest discover -s tests -v
```

The last `audit` command applies **only** when the normalized content is the synthetic six-bubble P5.3 fixture with exact `TGT_Bxx` markers. It is **not appropriate for real translations**: actual translated text cannot be assessed by matching artificial target tokens. Add real quality/omission benchmarking separately with licensed or self-created samples.

## Safety and fidelity limits

- `import` is **read-only** for the upstream JSON. Output writes require explicit `--output`; existing output files are protected unless `--overwrite` is selected. No inference, cloud API, OCR or network access.
- The upstream file may use a private *absolute image path as a dictionary key*. The adapter never copies this key into normalized output, or prints any source content in its default status. It is possible to leak content by explicitly saving and sharing the normalized contract; that is the user's responsibility.
- Only a **single-image project JSON** is accepted in this first slice. Multi-image files require explicit page selection; guessing which original file corresponds to a page is unsafe.
- Coordinates are checked against declared page dimensions and normalized; unsupported/malformed `lines` stop import rather than silently losing regions.
- This is not a general manga JSON import standard. Region `lines`, project file root and editability vary across upstream releases. Verify with a *real permitted export* before claiming genuine interoperability.
- The P5.3 synthetic check detects sentinel ID omissions, swaps, extra IDs and duplicates. It **cannot** measure OCR quality, translation correctness, NSFW compatibility, visual alignment, readability, or preservation of the source image.

## Next upstream-first verification

1. Obtain an actual small, redistributable or user-owned `*_translations.json` produced by a pinned manga-translator-ui release; compare field types and coordinate semantics against this adapter without publishing private content.
2. Ask Koharu/ComiTrans maintainers **only if necessary** whether they have a documented, optional, read-only region export; no issue spam and no duplicate pipeline implementation.
3. Test identity drift across runs with a page containing repeated dialogue and shifted/reordered boxes; record false positives as well as true faults.
4. On real samples, add independent human-visible checks for source-to-translation semantic alignment, speech-bubble position, and privacy. Do not call synthetic sentinel results an NSFW quality benchmark.
