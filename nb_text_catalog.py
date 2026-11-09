"""Text-first public discovery view over the unchanged P5.8 full research archive.

No network, LLM, new content uploads or deletion of archived media records.
This projection is intentionally strict: a mixed-modality or image-driven tool
must not leak into text-only Discovery merely because it has OCR or an LLM.
"""
from __future__ import annotations

from collections import Counter

from nb_catalog import catalogue
from nb_catalog_health import identity_review

TEXT_TASKS = {"roleplay", "novel_translation", "text_generation", "runtime"}
TEXT_CAPABILITIES = {
    "epub_input", "epub_output", "epub_editor",
    "resume_jobs", "glossary", "editable_translation",
    "gguf", "compatible_api", "character_card", "lorebook",
    "group_chat", "character_history", "character_memory",
    "character_lore_filter", "long_term_memory",
}
FACET_ORDER = ("task", "deployment", "type", "capability", "evidence", "link_health")


def is_text_first(item: dict) -> bool:
    """Explicitly exclude image/video/audio even if their OCR/output uses text."""
    return (
        item.get("modalities") == ["text"]
        and bool(set(item.get("tasks", [])) & TEXT_TASKS)
        and set(item.get("tasks", [])).issubset(TEXT_TASKS)
    )


def text_catalogue() -> dict:
    original = catalogue()
    items = []
    for row in original["items"]:
        if not is_text_first(row):
            continue
        copy = dict(row)
        copy["tasks"] = [t for t in row["tasks"] if t in TEXT_TASKS]
        copy["capability_evidence"] = [
            evidence for evidence in row.get("capability_evidence", [])
            if evidence["id"] in TEXT_CAPABILITIES
        ]
        copy["capabilities"] = [e["id"] for e in copy["capability_evidence"]]
        items.append(copy)

    facets = {}
    for facet in FACET_ORDER:
        if facet == "capability":
            active = {cap for row in items for cap in row["capabilities"]}
            choices = [x for x in original["facets"]["capability"] if x["id"] in active]
        elif facet == "task":
            active = {t for row in items for t in row["tasks"]}
            choices = [x for x in original["facets"]["task"] if x["id"] in TEXT_TASKS & active]
        else:
            active = {row[facet] for row in items}
            choices = [x for x in original["facets"][facet] if x["id"] in active]
        facets[facet] = choices

    included_source_names = {
        src["name"] for item in items for src in item["sources"]
        if src.get("readme_sha")
    }
    sources = []
    for source in original["sources"]:
        if source["name"] in included_source_names:
            source_copy = dict(source)
            # Only count included candidate cards referring to this directory;
            # these are not its original number of imported raw rows.
            source_copy["count"] = sum(
                any(s["name"] == source["name"] for s in item["sources"])
                for item in items
            )
            source_copy["count_scope"] = "text_first_visible_cards"
            sources.append(source_copy)

    health = original["health_summary"]
    counts = Counter(item["link_health"] for item in items)
    health_summary = {
        "checked_on": health["checked_on"],
        "counts": {k: counts.get(k, 0)
                   for k in ("repository_metadata_found", "conflicting_evidence", "not_checked")},
        "scope": "partial GitHub metadata checks, text-only records",
        "migrations": [],  # Previous ComfyUI migration belongs only to the archived media catalogue.
        "limitations": health["limitations"],
    }
    return {
        "schema_version": 1,
        "scope": "text_first",
        "items": items,
        "facets": facets,
        "sources": sources,
        "health_summary": health_summary,
        "identity_review": identity_review(items),
        "archive_summary": {
            "full_catalogue_items": len(original["items"]),
            "text_first_items": len(items),
            "media_or_mixed_items_archived": len(original["items"]) - len(items),
            "media_sources_preserved_in_repo": True,
        },
        "disclaimer": (
            "只展示文字创作/翻译/角色互动/文字模型与推理工具。"
            "图像、漫画、音频、视频及混合模态条目只保存在历史资料库，不进入本页。"
            "功能、成人内容支持、版权许可、隐私和硬件兼容仍需要分别核验。"
        ),
        "model_invocations": 0,
        "network_requests": 0,
    }


if __name__ == "__main__":
    import json
    print(json.dumps({
        "scope": "text_first",
        "archive": text_catalogue()["archive_summary"],
        "visible_sources": [s["name"] for s in text_catalogue()["sources"]],
        "valid": True,
    }, ensure_ascii=False, indent=2))
