# P5.6 · Source-attributed tag catalogue

**Direction change:** Discovery is the visible product. The older novel/comic editing and model tooling remain available for compatibility demonstrations and reproducible checks; they are not required by the catalogue.

## What was imported?

Four public GitHub **directory indexes**, pinned to the source README Git blob SHA on 2026-11-09:

| Dataset | Source | License of source text | Notes |
| --- | --- | --- | --- |
| Chinese adult-AI resource guide | [sichang-ai/awesome-uncensored-ai](https://github.com/sichang-ai/awesome-uncensored-ai) | CC BY-SA 4.0 | Maintainer openly identifies as an operator of one featured service; distinguish source claims from independent evidence. |
| Model/image list | [Anil-matcha/awesome-uncensored-ai-image-models](https://github.com/Anil-matcha/awesome-uncensored-ai-image-models) | CC BY 4.0 | Local and hosted model families mixed; no claim that any endpoint allows all adult content. |
| Low-refusal LLM list | [Anil-matcha/awesome-uncensored-llms](https://github.com/Anil-matcha/awesome-uncensored-llms) | CC BY 4.0 | Many variants are hosted-API labels; link to a provider does **not** verify checkpoint identity or refusal behavior. |
| Video model list | [Anil-matcha/awesome-uncensored-ai-video-models](https://github.com/Anil-matcha/awesome-uncensored-ai-video-models) | CC BY 4.0 | Hosted endpoints and local weights are separate access paths. |

The imported JSON snapshots in [catalog/imports/](../catalog/imports/) preserve source name, README blob SHA, license URL, source-disclosed conflict, short factual name/link and category tags. **No external review paragraphs, vendor scores, price tables, NSFW performance claims, private datasets or scripts were copied.** Each linked project/checkpoint retains its own license and provider rules.

Source directory permission applies to source material, **not** to the linked checkpoints, software or services. The NaughtyBoddy repository itself still requires an explicit software license before calling it open source in the legal sense.

## How users browse

Run:

    python naughtyboddy.py studio

Then open http://127.0.0.1:8765/discover. No prompt box, API token, LLM, cloud service or GPU required.

Users click any number of tags from five dimensions: content modality, creative task, deployment, item type and evidence state. Within one facet selected tags are **OR**; across facets selected groups are **AND**. Removing the last tag in a group removes that constraint. Results are filtered in the browser after a **single local** request to GET /api/catalog, without fetching external sites for each click.

Each result shows a direct outgoing project link, source-directory attribution, provenance and explicit lack of model, hardware, adult-compatibility and privacy validation. The tool link is not an endorsement. The directory is sorted by name, **not** by an invented quality score. Results can be browsed in batches.

## Curated profiles vs imported candidates

The original 16 NaughtyBoddy solution records remain in [registry/solutions/](../registry/solutions/), including reviewed project docs and task assessments. On the display layer a curated record takes precedence over an external import **only when both the name and destination URL match**; linked sources are preserved. Two different products/variants are never merged merely because their model names sound similar or they use the same provider.

Imported entries always have evidence status \`imported_unverified\`. The P5.6 code rejects records attempting to turn directory listing into a verified adult-content claim.

## Reproduction & limits

    python nb_catalog.py validate
    python nb_registry.py validate
    python -m unittest discover -s tests -v
    node --check web/chooser.js

The catalog is a snapshot, not a live update service; prices, restrictions and repos may change. Tags are imported from publishers' original section classifications and are **unverified metadata**. Users should check live official licensing/terms and benchmark records before relying on a tool for lawful adult creativity.

No actual adult-model test, GPU inference or browser visual QA has been performed in P5.6. The software does not automatically use, install or execute any imported project.

## Next

1. Add source-correction PRs and note stale/unavailable projects without erasing attribution.
2. Expand tag precision only where data can support it (e.g. LoRA, image-edit, voice cloning with consent, reversible editing, EPUB support).
3. Use the compatibility test kit to confirm specific project integrations **after** real sample outputs become available.
