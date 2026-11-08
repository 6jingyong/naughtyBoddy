"""P3.2: explicit, local model evidence and conservative task-specific routing.

Names, tags and keyword checks are NEVER a verified adult-content capability.
Profiles are private user-entered observations, not community/public benchmarks.
No inference, downloads or paid API calls occur during routing.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import threading
import uuid

from nb_common import ProviderError

TASKS = {
    "novel_translation": {"label": "长篇小说翻译", "modality": "text"},
    "creative_writing": {"label": "故事与剧本创作", "modality": "text"},
    "roleplay": {"label": "虚构人物互动", "modality": "text"},
    "comic_translation": {"label": "漫画翻译", "modality": "image"},
    "subtitles": {"label": "视频字幕翻译", "modality": "text"},
}
PROVIDERS = ("ollama", "compatible", "openrouter")
COMPAT = ("unknown", "compatible", "incompatible")
QUALITY = ("unknown", "good", "mixed", "poor")
MODEL_ID = re.compile(r"[\w./:@+\-]{1,220}\Z", re.UNICODE)
MAX_PROFILES = 500
MAX_MODELS = 150


def validate_identity(provider: str, model: str, task: str) -> None:
    if provider not in PROVIDERS:
        raise ProviderError("Unsupported provider")
    if not isinstance(model, str) or not MODEL_ID.fullmatch(model):
        raise ProviderError("Invalid model ID")
    if task not in TASKS:
        raise ProviderError("Unsupported task")


def normalize_review(data: dict) -> dict:
    provider, model, task = data.get("provider"), data.get("model"), data.get("task")
    validate_identity(provider, model, task)
    compatibility = data.get("adult_compatibility", "unknown")
    quality = data.get("task_quality", "unknown")
    note = data.get("note", "")
    if compatibility not in COMPAT or quality not in QUALITY:
        raise ProviderError("Invalid review rating")
    if not isinstance(note, str) or len(note) > 1200:
        raise ProviderError("Review note must be at most 1200 characters")
    if data.get("confirm_review") is not True:
        raise ProviderError("Manual review requires explicit confirmation")
    return {"provider": provider, "model": model, "task": task,
            "adult_compatibility": compatibility, "task_quality": quality,
            "note": note.strip(), "evidence_type": "user_review",
            "updated_at": datetime.now(timezone.utc).isoformat()}


def route_models(candidates: list[dict], reviews: list[dict], reports: list[dict],
                 *, task: str, allow_remote: bool = False) -> dict:
    """Produce conservative suggestions. Never silently invoke or auto-switch."""
    if task not in TASKS:
        raise ProviderError("Unsupported task")
    if len(candidates) > MAX_MODELS:
        raise ProviderError("Too many model candidates")
    index = {(r.get("provider"), r.get("model"), r.get("task")): r for r in reviews
             if isinstance(r, dict)}
    observations = {(r.get("provider"), r.get("model")): r for r in reports if isinstance(r, dict)}
    rows = []
    for c in candidates:
        provider, model = c.get("provider"), c.get("model")
        try:
            validate_identity(provider, model, task)
        except ProviderError:
            continue
        local = c.get("local") is True
        if not local and not allow_remote:
            continue
        if c.get("available") is not True:
            continue
        modalities = c.get("modalities") or []
        required = TASKS[task]["modality"]
        if required == "image" and "image" not in modalities:
            # Unknown modalities cannot be advertised as vision-capable.
            continue
        if modalities and required not in modalities:
            continue
        review = index.get((provider, model, task))
        compatibility = review.get("adult_compatibility", "unknown") if review else "unknown"
        quality = review.get("task_quality", "unknown") if review else "unknown"
        if compatibility == "incompatible":
            continue
        report = observations.get((provider, model))
        # Direct review of the relevant task dominates non-validated keyword signals.
        proof_rank = 2 if compatibility == "compatible" else 1 if review else 0
        quality_rank = {"good": 3, "mixed": 2, "unknown": 1, "poor": 0}[quality]
        # All else equal, local avoids provider latency/privacy cost. Not a quality claim.
        order = (proof_rank, quality_rank, int(local))
        reasons = ["用户曾人工复核此任务的兼容性" if proof_rank == 2 else
                   "仅有用户备注，兼容性仍不确定" if review else "尚无人工复核的任务能力记录"]
        if report:
            reasons.append("存在自动启发式测试；不能替代人工复核")
        if c.get("hints"):
            reasons.append("名称或标签包含低拒答关键词，但没有由此推断能力")
        if not local:
            reasons.append("云端调用需单独确认数据传输和费用")
        rows.append({"provider": provider, "model": model, "local": local,
                     "base_url": c.get("base_url") if local else None,
                     "task": task, "adult_compatibility": compatibility, "task_quality": quality,
                     "evidence_type": "user_review" if review else "none",
                     "has_heuristic_report": bool(report), "reasons": reasons,
                     "remote_consent_required": not local, "_order": order})
    rows.sort(key=lambda x: (tuple(-v for v in x["_order"]), x["provider"], x["model"]))
    for row in rows:
        row.pop("_order")
    return {"task": task, "candidates": rows,
            "recommendation": rows[0] if rows else None,
            "status": "suggestions_only_no_auto_execution",
            "note": "This is a heuristic ordering of user-reviewed availability, not a validated low-refusal leaderboard. No external calls made."}


class ModelProfileStore:
    def __init__(self, workspace: Path):
        self.path = workspace / "private" / "model-profiles.json"
        self.lock = threading.RLock()

    def list(self) -> list[dict]:
        with self.lock:
            if not self.path.exists():
                return []
            if self.path.is_symlink():
                raise ProviderError("Profile store symlink rejected")
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or not isinstance(data.get("profiles"), list):
                raise ProviderError("Malformed model profiles store")
            return data["profiles"][:MAX_PROFILES]

    def upsert(self, payload: dict) -> dict:
        review = normalize_review(payload)
        with self.lock:
            previous = [r for r in self.list() if (r.get("provider"), r.get("model"), r.get("task")) !=
                        (review["provider"], review["model"], review["task"])]
            if len(previous) >= MAX_PROFILES:
                raise ProviderError("Profile store is full")
            previous.append(review)
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if self.path.is_symlink() or self.path.parent.is_symlink():
                raise ProviderError("Profile store symlink rejected")
            temp = self.path.with_name(self.path.name + "." + uuid.uuid4().hex + ".tmp")
            try:
                fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump({"schema_version": 1, "profiles": previous}, f, ensure_ascii=False, indent=2)
                os.replace(temp, self.path)
            finally:
                temp.unlink(missing_ok=True)
        return review
