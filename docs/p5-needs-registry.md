# P5 — Needs → Solutions → Gaps registry

**Purpose:** help users and open-source maintainers locate existing solutions to *lawful adult creative tasks*, understand what is and is not verified, and identify genuinely missing capabilities before writing another specialist app.

The registry is a **small, offline editorial dataset**, not a scraper, an NSFW model ranking, a content search engine, a package installer or a store. Source content, user files and prompts never leave a user's machine when browsing these records.

## Workflow

1. **Need:** write a specific job-to-be-done, hardware/privacy constraints and reproducible acceptance checks. Initial needs are *hypotheses*, not a sample of surveyed users.
2. **Solutions:** enter existing projects and official links with explicit verification states; licenses remain `null` until confirmed. A tag match is a search aid **not proof of support or compatibility**.
3. **Assessment:** test a specific solution for a specific need, on each acceptance check. `fit: meets` or `partial` requires reviewed evidence, recorded observations and a relevant environment; `hands_on_verified` requires executed checks.
4. **Gap:** propose a falsifiable capability gap, then confirm it through user interviews, reproducible experiments or source evidence. Do not call a gap a fact because a search yielded nothing.
5. **Act:** prefer accurate recommendations and upstream contributions; implement an independent adapter or workflow only when the gap is real and the existing project cannot reasonably fill it.

## CLI (Python 3.11+, standard library)

```bash
python nb_registry.py validate
python nb_registry.py needs
python nb_registry.py solutions
python nb_registry.py match need-manga-localization
python nb_registry.py gaps
python -m unittest discover -s tests -v
```

All registry records are plain JSON in `registry/{needs,solutions,assessments,gaps}`. The CLI does **not** fetch URLs or execute models and is safe to use offline. It validates schema versions, cross references and evidence labels; it does not establish truth of claims. Do not import confidential prompts, unpublished manuscripts or paid content into public registry records.

## Evidence vocabulary

- `hypothesis`: inferred user need or untested claim.
- `reported`: user's experience or other report, not independently verified.
- `documentation_reviewed`: source documentation actually inspected; record the URLs and specific observations.
- `hands_on_verified`: real, reproducible run with environment details and check results.

There is **no generic star rating**, “unrestricted” stamp, automatic compatibility verdict, or unverified claim that an API works for adult material. Recheck availability, model versions, licenses and platform restrictions before publishing recommendations. A model's marketing terms do not establish low refusal or fidelity.

## Initial contributions

A useful first contribution is a *specific missing user task* and an acceptance check, not a request for a universal agent. Example: “My 8GB GPU should translate a chapter of an authorized adult novel locally while preserving a 50-name glossary; quantify manual corrections.” Attach no private source text. A synthetic or explicitly licensed test sample is preferable.

The seed projects in this repository are **candidates only**. Their exact features, licenses, NSFW compatibility, installation steps, GPU requirements and quality have **not yet been hands-on verified** by P5.

## Next iterations

- Give the Studio GUI a read-only needs/solutions browser; keep import/edit permissions local.
- Evaluate source freshness with dated records; add an upstream contribution tracker (issues and PRs, no invented claims).
- Design a portable workflow capability manifest *after* reviewing existing plugin conventions (ComfyUI, SillyTavern, etc.), not before.
- When real machine or user testing is available, collect benchmark provenance and results; never confuse mock tests with model quality.

## P5.2 · Friction evidence records

An optional fifth registry folder, `registry/frictions/`, captures narrowly defined user problems or documented design tradeoffs, **not automatic feature requests**. The record must have a need ID, linked solutions, primary public source URLs, evidence type, user impact, an existing mitigation distinguished as `documented`, `proposed`, or `unknown`, and a falsifiable verification plan.

```bash
python nb_registry.py frictions
python nb_registry.py frictions --need need-manga-localization
```

The CLI only reads local JSON and does not fetch sources. Adding a URL in the record does not mean the issue is currently open or universally reproducible. `match` includes related friction IDs but never treats their count as a quality rating. More: [research](p52-friction-evidence.md).
