"""NaughtyBoddy P5.6 — source-attributed offline tag catalogue.

External directory *names/links/categories* are candidate leads, not verified
adult-compatibility claims or endorsements. No LLM, model request or network.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from nb_registry import DEFAULT_ROOT as REGISTRY_ROOT, read_registry

ROOT = Path(__file__).resolve().parent / "catalog" / "imports"
MAX_SNAPSHOT_BYTES = 350_000
KINDS = {"tool", "service", "model", "runtime", "extension", "workflow", "component", "utility"}
MODALITIES = {"text", "image", "video", "audio"}
TASKS = {"roleplay", "novel_translation", "manga_translation", "text_generation",
         "image_generation", "video_generation", "audio_generation", "runtime"}
DEPLOYMENTS = {"local", "hosted", "hybrid", "unknown"}
EVIDENCE = {"imported_unverified", "documentation_reviewed"}
FACETS = {
    "modality": [
        ("text", "文字"), ("image", "图像"), ("video", "视频"), ("audio", "语音"),
    ],
    "task": [
        ("roleplay", "角色互动"), ("novel_translation", "小说翻译"),
        ("manga_translation", "漫画翻译"), ("text_generation", "文本生成"),
        ("image_generation", "插画/图片"), ("video_generation", "视频生成"),
        ("audio_generation", "配音/语音"), ("runtime", "推理/基础工具"),
    ],
    "deployment": [
        ("local", "目录标注本地"), ("hosted", "目录标注在线"),
        ("hybrid", "混合模式"), ("unknown", "运行方式未知"),
    ],
    "type": [
        ("tool", "创作工具"), ("service", "在线平台"),
        ("model", "模型/权重"), ("runtime", "推理后端"),
        ("extension", "扩展"), ("workflow", "专用工作流"),
        ("component", "组件"), ("utility", "辅助工具"),
    ],
    "evidence": [
        ("documentation_reviewed", "已核查项目文档"),
        ("imported_unverified", "仅外部目录收录"),
    ],
}


class CatalogError(ValueError):
    pass


def safe_url(value: object) -> bool:
    if not isinstance(value, str) or len(value) > 1800:
        return False
    try:
        p = urlsplit(value)
        if p.scheme != "https" or not p.hostname or p.username or p.password:
            return False
        hostname = p.hostname.lower().rstrip(".")
        if hostname == "localhost" or hostname.endswith(".localhost"):
            return False
        return not (hostname.startswith("127.") or hostname.startswith("192.168.")
                    or hostname.startswith("10.") or hostname in {"0.0.0.0", "::1"})
    except ValueError:
        return False


def normalized_name(name: str) -> str:
    name = unicodedata.normalize("NFKC", name).casefold()
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", name)


def canonical_url(value: str) -> str:
    p = urlsplit(value)
    host = (p.hostname or "").lower().removeprefix("www.")
    path = p.path.rstrip("/")
    return host + path.casefold()


def _string_list(value: object, choices: set[str], context: str) -> list[str]:
    if not isinstance(value, list) or not value or not all(isinstance(x, str) and x in choices for x in value):
        raise CatalogError("Invalid " + context)
    return list(dict.fromkeys(value))


def load_snapshots(root: Path = ROOT) -> list[dict]:
    if not root.is_dir():
        raise CatalogError("Missing catalog/imports directory")
    snapshots = []
    for path in sorted(root.glob("*.json")):
        if path.is_symlink() or path.stat().st_size > MAX_SNAPSHOT_BYTES:
            raise CatalogError("Oversized or symlinked snapshot: " + path.name)
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise CatalogError("Bad snapshot JSON: " + path.name) from exc
        if not isinstance(doc, dict) or doc.get("schema_version") != 1:
            raise CatalogError("Bad snapshot version: " + path.name)
        source = doc.get("source")
        entries = doc.get("entries")
        if not isinstance(source, dict) or not isinstance(entries, list):
            raise CatalogError("Missing source or entries: " + path.name)
        if (not safe_url(source.get("url")) or not safe_url(source.get("license_url"))
                or not isinstance(source.get("readme_sha"), str)
                or not re.fullmatch(r"[0-9a-f]{40}", source["readme_sha"])):
            raise CatalogError("Missing reproducible source attribution: " + path.name)
        if not isinstance(source.get("id"), str) or not source["id"]:
            raise CatalogError("Source ID required")
        seen = set()
        for row in entries:
            if not isinstance(row, dict):
                raise CatalogError("Invalid imported entry")
            rid = row.get("id")
            if not isinstance(rid, str) or rid in seen:
                raise CatalogError("Missing or duplicate imported ID")
            seen.add(rid)
            if not isinstance(row.get("name"), str) or not row["name"].strip() or not safe_url(row.get("url")):
                raise CatalogError("Entry must have a name and HTTPS source link")
            if row.get("type") not in KINDS or row.get("deployment") not in DEPLOYMENTS:
                raise CatalogError("Invalid item type or deployment")
            _string_list(row.get("modalities", [row.get("modality")]), MODALITIES, "modality")
            _string_list(row.get("tasks", [row.get("task")]), TASKS, "task")
            if row.get("adult_compatibility") != "not_tested" or row.get("evidence") != "third_party_directory_only":
                raise CatalogError("Imported entry must remain unverified")
        snapshots.append(doc)
    if not snapshots:
        raise CatalogError("No imported source snapshots")
    return snapshots


def _curated_type(row: dict) -> str:
    slug = row["id"]
    if slug in {"solution-ollama", "solution-koboldcpp"}:
        return "runtime"
    if any(x in slug for x in ("presence", "memories-manager")):
        return "extension"
    if "calibre" in slug:
        return "utility"
    return "tool"


def _curated_tags(row: dict) -> tuple[list[str], list[str], str]:
    tags = set(row["tags"])
    m = set()
    t = set()
    if "roleplay" in tags or "character" in tags:
        m.add("text")
        t.add("roleplay")
    if "novel" in tags or "epub" in tags:
        m.add("text")
        t.add("novel_translation")
    if "manga" in tags or "ocr" in tags:
        m.add("image")
        t.add("manga_translation")
    if "image" in tags or "image-editing" in tags:
        m.add("image")
    if "local-inference" in tags:
        t.add("runtime")
        if not m:
            m.add("text")
    if not m:
        m.add("text")
    if not t:
        t.add("runtime")
    # Documentation-reviewed metadata is not a measured privacy/data boundary.
    deployment = "hybrid" if "local-inference" in tags and "roleplay" in tags else "unknown"
    if row["id"] in {"solution-ollama", "solution-koboldcpp"}:
        deployment = "local"
    return sorted(m), sorted(t), deployment


def catalogue(imports_root: Path = ROOT, registry_root: Path = REGISTRY_ROOT) -> dict:
    records, errors = read_registry(registry_root)
    if errors:
        raise CatalogError("Invalid underlying registry: " + errors[0])
    items = []
    for sol in records["solutions"]:
        modalities, tasks, deployment = _curated_tags(sol)
        items.append({
            "id": "reviewed-" + sol["id"], "name": sol["title"], "url": sol["url"],
            "type": _curated_type(sol), "modalities": modalities, "tasks": tasks,
            "deployment": deployment, "evidence": "documentation_reviewed" if sol["verification"] == "documentation_reviewed" else "imported_unverified",
            "adult_compatibility": "not_tested", "model_quality": "not_tested",
            "hardware_fit": "not_tested", "privacy_audit": "not_run",
            "sources": [{"name": "NaughtyBoddy detailed profile",
                         "url": sol["url"], "source_license": "not_inferred",
                         "status": sol["verification"]}],
            "note": "NaughtyBoddy 仅核查了项目文档；真实兼容性、隐私和效果未实测。",
        })
    used = {x["id"] for x in items}
    for snapshot in load_snapshots(imports_root):
        source = snapshot["source"]
        for row in snapshot["entries"]:
            item = {
                "id": "import-" + row["id"], "name": row["name"], "url": row["url"],
                "type": row["type"],
                "modalities": row.get("modalities", [row["modality"]]),
                "tasks": row.get("tasks", [row["task"]]),
                "deployment": row["deployment"],
                "evidence": "imported_unverified",
                "adult_compatibility": "not_tested", "model_quality": "not_tested",
                "hardware_fit": "not_tested", "privacy_audit": "not_run",
                "sources": [{
                    "name": source["repo"], "url": source["url"],
                    "readme_sha": source["readme_sha"], "source_license": source["license"],
                    "source_license_url": source["license_url"],
                    "status": "third_party_directory_only",
                    "disclosure": source.get("disclosure", "unknown"),
                }],
                "note": "仅外部目录收录，标签来自原目录；本站未独立核实内容政策、可用性或效果。",
            }
            # Only merge when both name AND target URL match. Do not conflate
            # a locally installed model with a hosted product of similar name.
            match = next((x for x in items if normalized_name(x["name"]) == normalized_name(item["name"])
                          and canonical_url(x["url"]) == canonical_url(item["url"])), None)
            if match:
                match["modalities"] = sorted(set(match["modalities"] + item["modalities"]))
                match["tasks"] = sorted(set(match["tasks"] + item["tasks"]))
                match["sources"].extend(item["sources"])
                continue
            if item["id"] in used:
                raise CatalogError("ID collision: " + item["id"])
            used.add(item["id"])
            items.append(item)
    items.sort(key=lambda x: (x["name"].casefold(), x["id"]))
    return {
        "schema_version": 1, "items": items, "facets": {
            name: [{"id": key, "label": label} for key, label in entries]
            for name, entries in FACETS.items()
        },
        "sources": [
            {"name": s["source"]["repo"], "url": s["source"]["url"],
             "license": s["source"]["license"], "commit": s["source"]["readme_sha"],
             "count": len(s["entries"]), "disclosure": s["source"]["disclosure"]}
            for s in load_snapshots(imports_root)
        ],
        "disclaimer": "导入目录信息不等于审核认证；标签仅供筛选，不提供成人内容兼容性、隐私或硬件适配保证。",
        "model_invocations": 0, "network_requests": 0,
    }


def select(items: list[dict], selected: dict[str, list[str]]) -> list[dict]:
    if not isinstance(selected, dict) or any(k not in FACETS for k in selected):
        raise CatalogError("Unknown facet")
    for facet, values in selected.items():
        allowed = {k for k, _ in FACETS[facet]}
        if not isinstance(values, list) or len(values) > 12 or any(not isinstance(v, str) or v not in allowed for v in values):
            raise CatalogError("Invalid facet value")
    key = {
        "modality": "modalities", "task": "tasks", "deployment": "deployment",
        "type": "type", "evidence": "evidence",
    }
    def matches(item):
        for facet, values in selected.items():
            if not values:
                continue
            current = item[key[facet]]
            matches = set(current) if isinstance(current, list) else {current}
            if not matches.intersection(values):
                return False
        return True
    return [x for x in items if matches(x)]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Read-only imported catalogue: no model/no network")
    ap.add_argument("action", choices=["validate", "list", "sources"])
    args = ap.parse_args(argv)
    try:
        result = catalogue()
        if args.action == "validate":
            data = {"valid": True, "items": len(result["items"]),
                    "source_count": len(result["sources"]),
                    "raw_imports": sum(s["count"] for s in result["sources"])}
        elif args.action == "sources":
            data = result["sources"]
        else:
            data = result["items"]
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    except (CatalogError, OSError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
