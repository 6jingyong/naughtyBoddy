# P5.8 · Link health, repository moves and duplicate-identity review

Reviewed 2026-11-09. This is a **partial spot check** of GitHub repository metadata and a deterministic identity review of the local NaughtyBoddy catalogue. It does not claim to check every link. No providers, model weights, user content, GPU or AI model were accessed.

## Verified correction: ComfyUI migration

The old [comfyanonymous/ComfyUI](https://github.com/comfyanonymous/ComfyUI) GitHub repository API path currently returns **Moved Permanently**. The present upstream project is [Comfy-Org/ComfyUI](https://github.com/Comfy-Org/ComfyUI). Before P5.8, our original unreviewed ComfyUI profile and the source-imported new address appeared as two cards.

P5.8 changes the original profile URL to the canonical GitHub path, retains the old URL in its recorded sources, attaches its previously collected official feature evidence to the single surviving catalogue ID, and merges that source-directory candidate using the existing name+URL rule. The catalogue therefore moves from **107 to 106** displayed candidates, without deleting either provenance source.

The item remains unverified at the **product level**. Official documentation for a few supported ComfyUI features is not proof of adult-content compatibility or privacy.

## Partial link audit

[Structured observations](../catalog/link-health.json) contain:
- 18 repository-API metadata findings, including a recorded checked-on date, canonical repository path, archived/disabled flags, and last Git push time.
- 1 **conflicting-evidence** result: the [Libre Manga Translator](https://github.com/mrdhnto/libre-manga-translator) repository API returned 404 via the connected GitHub interface, while a recently indexed public GitHub page existed. **Status is unresolved**, not 'deleted'. Recheck with another session/source before changing it.
- 1 explicit, confirmed old-to-new ComfyUI GitHub migration mapping.

The 87 remaining candidates are **not checked** by this partial link snapshot; this is intentionally visible. The catalogue UI indicates a GitHub repo check, an unresolved conflict, or unknown state. There is no red 'dead project' label inferred from API 404 or time since last push.

**Very important:** a GitHub API 200 confirms only that public metadata was returned at that time. It does not prove the binary works, a release is downloadable, a model endpoint allows certain content, or that the maintainer still supports the project. Conversely, a quiet repository or old last-push date is not proof of abandonment.

## URL and identity duplicates: do not over-merge

The [identity audit](../nb_catalog_health.py) detects two candidate patterns:
- **Shared destination, different names.** One commercial endpoint can serve multiple model variants; one upstream GitHub repo can have several checkpoints or architectures. Keep separate records until versions/deployment identities are independently established.
- **Same normalized name, different destinations.** A base model's public weights and a hosted API may share a name. These are separate ways of using it, not necessarily duplicate tools.

The older importer already merges exact matching name+destination only. The P5.8 identity check deliberately **does not merge** anything else; it presents review groups. It does not infer identical model weights from names or endpoint URLs.

## Run locally: no network required

    python naughtyboddy.py studio
    # Visit http://127.0.0.1:8765/discover
    python nb_catalog.py validate
    python nb_catalog_health.py validate
    python nb_catalog_health.py summary
    python nb_catalog_health.py duplicates
    python nb_catalog_health.py needs-review
    python -m unittest discover -s tests -v

The page adds a **链接核查** facet: GitHub repository metadata checked, conflicting evidence, and unchecked. Each affected card contains the check date and a warning on scope. The bottom of the page shows the shared-link group list and recorded migrations.

Each check is a static, attributed snapshot. Selecting tags never sends URLs to a third party and never starts a background health crawler. To refresh, repeat public-source verification consciously, record the result with its date and source, and update [the snapshot](../catalog/link-health.json) in a reviewable PR.

## Limitations and next step

External model/API websites and most GitHub repository links are still unchecked. This release **does not validate 106 live websites** or claim zero broken links. Nor does it inspect browser-store distribution, software installability, anti-NSFW restrictions, source license inheritance, GPU needs, or output quality.

Next, add cautious **per-project lifecycle notes** (last release, archived flag, moved repository, unsupported platform) from official upstream sources; keep separate from benchmark, hardware and model content policies. Future link-refresh automation should only be opt-in, rate-limited, and should produce drafts for human review rather than automatically remove listings.
