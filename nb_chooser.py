"""Evidence-first, multi-choice solution finder. No LLM, network or user text."""
from __future__ import annotations

import json
from pathlib import Path
from nb_registry import DEFAULT_ROOT, read_registry, RegistryError

PROFILES = Path(__file__).resolve().parent / "registry" / "chooser-profiles.json"
OPTIONS = {
    "task": [
        {"id": "need-long-fiction-translation", "label": "小说 / EPUB 翻译"},
        {"id": "need-manga-localization", "label": "漫画翻译与嵌字"},
        {"id": "need-private-roleplay", "label": "私人角色互动"},
    ],
    "privacy": [
        {"id": "local_only", "label": "尽可能全程本地，不主动上传素材"},
        {"id": "local_preferred", "label": "优先本地，也接受明确告知的云端步骤"},
        {"id": "remote_ok", "label": "可使用在线服务，但须说明资料去向"},
    ],
    "hardware": [
        {"id": "cpu", "label": "没有独立显卡"},
        {"id": "vram8", "label": "约 8GB 显存"},
        {"id": "vram12", "label": "12GB 或以上显存"},
        {"id": "unknown", "label": "不确定设备配置"},
    ],
    "priority": [
        {"id": "editable", "label": "成果可以逐项修改"},
        {"id": "privacy", "label": "尽量不上传原始素材"},
        {"id": "low_setup", "label": "尽可能容易安装使用"},
        {"id": "continuity", "label": "长期内容一致性与可迁移"},
    ],
}
ALLOWED = {key: {x["id"] for x in items} for key, items in OPTIONS.items()}
ROLES = {"workflow": 0, "extension": 1, "component": 2, "utility": 3}
LOCAL_OPTIONS = {"documented_option", "requires_local_host"}


def chooser_questions() -> dict:
    return {
        "questions": [
            {"id": "task", "title": "你想完成什么任务？", "options": OPTIONS["task"]},
            {"id": "privacy", "title": "你对隐私有什么要求？", "options": OPTIONS["privacy"]},
            {"id": "hardware", "title": "你的设备大概是什么情况？", "options": OPTIONS["hardware"]},
            {"id": "priority", "title": "你最在意什么？", "options": OPTIONS["priority"]},
        ],
        "note": "仅多项选择，没有自由文本、模型推理、远程请求或自动下载安装。",
    }


def _profiles(path: Path) -> list[dict]:
    if path.stat().st_size > 160_000:
        raise RegistryError("Chooser profile file is oversized")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(data.get("profiles"), list):
        raise RegistryError("Chooser profiles must be a versioned list")
    seen = set()
    for row in data["profiles"]:
        key = (row.get("need_id"), row.get("solution_id"))
        if key in seen:
            raise RegistryError("Duplicate chooser mapping")
        seen.add(key)
        if row.get("role") not in ROLES or row.get("local_mode") not in {
            "documented_option", "requires_local_host", "unknown"
        } or row.get("editable") not in {"documented", "unknown", "not_applicable"}:
            raise RegistryError("Invalid chooser profile status")
        if not isinstance(row.get("documentation_url"), str) or not row["documentation_url"].startswith("https://"):
            raise RegistryError("Chooser profile requires a public documentation URL")
    return data["profiles"]


def choose(answers: dict, root: Path = DEFAULT_ROOT, profiles_path: Path = PROFILES) -> dict:
    """Find documented possibilities, NEVER infer actual adult-content quality or compatibility."""
    if not isinstance(answers, dict) or set(answers) != set(ALLOWED):
        raise RegistryError("Expected exactly four multiple-choice answers")
    for key, value in answers.items():
        if not isinstance(value, str) or value not in ALLOWED[key]:
            raise RegistryError("Invalid choice for " + key)
    registry, errors = read_registry(root)
    if errors:
        raise RegistryError("Registry has invalid source records: " + errors[0])
    solutions = {x["id"]: x for x in registry["solutions"]}
    frictions = registry["frictions"]
    rows = []
    for profile in _profiles(profiles_path):
        if profile["need_id"] != answers["task"]:
            continue
        sol = solutions.get(profile["solution_id"])
        if sol is None:
            raise RegistryError("Missing referenced solution: " + profile["solution_id"])
        linked = [f for f in frictions if f["need_id"] == answers["task"] and
                  sol["id"] in f["solution_ids"]]
        candidate = {
            "id": sol["id"], "name": sol["title"], "url": sol["url"],
            "role": profile["role"], "documentation_url": profile["documentation_url"],
            "review_status": sol["verification"], "local_mode": profile["local_mode"],
            "editable": profile["editable"], "summary": sol["summary"],
            "note": profile["note"],
            "frictions": [
                {"title": x["title"], "source": x["sources"][0],
                 "mitigation_status": x["existing_mitigation"]["status"]}
                for x in linked[:3]
            ],
            "claimed_quality": "not_evaluated",
            "hardware_fit": "not_evaluated",
            "privacy_audit": "not_run",
        }
        rows.append(candidate)
    if not rows:
        raise RegistryError("No editorial chooser mapping for this need")
    possible, unconfirmed = [], []
    for c in rows:
        if answers["privacy"] == "local_only" and c["local_mode"] not in LOCAL_OPTIONS:
            unconfirmed.append(c)
        else:
            possible.append(c)
    def order(c):
        local = 0 if c["local_mode"] in LOCAL_OPTIONS else 1
        edit = 0 if c["editable"] == "documented" else 1
        return (ROLES[c["role"]],
                local if answers["privacy"] != "remote_ok" else 0,
                edit if answers["priority"] == "editable" else 0,
                c["name"].lower())
    possible.sort(key=order)
    unconfirmed.sort(key=order)
    warnings = [
        "官方文档中的本地运行选项，不等于已经审计了网络隐私。",
        "展示顺序仅由类型与文档能力决定；不是质量、破甲程度或易用性排名。",
        "显卡适配与模型内存占用尚未实测；本次选择不会据此排除方案。",
    ]
    if answers["priority"] == "low_setup":
        warnings.append("目前没有安装时间/失败率的实测，因此不会自动评定哪个最容易上手。")
    if answers["priority"] == "continuity":
        warnings.append("长期人物一致性、术语一致性等仍缺实际对照测试。")
    if answers["hardware"] == "cpu":
        warnings.append("无独显设备是否可用，取决于具体模型和推理后端；需另行验证。")
    if answers["privacy"] == "local_only" and not possible:
        warnings.append("尚无文档支持本地模式的对应候选；不能强行推荐云端方案。")
    return {
        "answers": answers, "candidates": possible, "unconfirmed_local": unconfirmed,
        "warnings": warnings, "real_world_tests": "not_run",
        "data_source": "local_repository_registry", "model_invocations": 0,
        "next_step": "阅读对应上游教程并逐项确认安装、硬件、许可和数据流向。",
    }
