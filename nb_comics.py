"""Local-first comic page/region editor, independent of language-model tool calling.

P4 scope: import PNG/JPEG pages, manual editable text boxes (or externally supplied OCR
boxes), translate isolated regions through a caller-provided function, save revisions,
and export self-contained SVG overlays. OCR/erasure/production raster export are later
pipeline adapters; no cloud calls happen in this module.
"""
from __future__ import annotations

import base64
import html
import json
import os
from pathlib import Path
import re
import struct
import threading
import uuid
from datetime import datetime, timezone

from nb_common import ProviderError

ID = re.compile(r"[0-9a-f]{32}\Z")
MAX_PAGE_BYTES = 12 * 1024 * 1024
MAX_PIXELS = 42_000_000
MAX_PAGES = 80
MAX_REGIONS = 6000


def _now():
    return datetime.now(timezone.utc).isoformat()


def image_size(data: bytes) -> tuple[str, int, int]:
    """Read image dimensions without decoding untrusted pixels."""
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 33:
        if data[12:16] != b"IHDR":
            raise ProviderError("Invalid PNG IHDR")
        w, h = struct.unpack(">II", data[16:24])
        fmt = "png"
    elif data[:3] == b"\xff\xd8\xff":
        fmt = "jpg"
        w = h = 0
        i = 2
        while i < len(data)-3:
            if data[i] != 0xff:
                raise ProviderError("Malformed JPEG marker")
            while i < len(data) and data[i] == 0xff:
                i += 1
            if i >= len(data):
                break
            marker = data[i]; i += 1
            if marker == 0xd9 or marker == 0xda:
                break
            if marker in (0x01, *range(0xd0, 0xd8)):
                continue
            if i + 2 > len(data):
                break
            length = int.from_bytes(data[i:i+2], "big")
            if length < 2 or i + length > len(data):
                break
            if marker in (0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf):
                if length >= 7:
                    h = int.from_bytes(data[i+3:i+5], "big")
                    w = int.from_bytes(data[i+5:i+7], "big")
                break
            i += length
    else:
        raise ProviderError("Only PNG and JPEG images are supported in P4")
    if not (1 <= w <= 15000 and 1 <= h <= 15000 and w*h <= MAX_PIXELS):
        raise ProviderError("Invalid or oversized image dimensions")
    return fmt, w, h


def _validate_box(box):
    if not isinstance(box, list) or len(box) != 4 or not all(type(x) in (int, float) for x in box):
        raise ProviderError("Region box must be normalized [x,y,width,height]")
    x, y, w, h = box
    if not (0 <= x < 1 and 0 <= y < 1 and 0.005 <= w <= 1 and 0.005 <= h <= 1
            and x+w <= 1.0000001 and y+h <= 1.0000001):
        raise ProviderError("Region box outside image")
    return [round(float(v), 6) for v in box]


def _validate_text(value, field, max_length=8000):
    if not isinstance(value, str) or len(value) > max_length:
        raise ProviderError(f"{field} must be text shorter than {max_length} characters")
    return value


class ComicLibrary:
    def __init__(self, workspace: Path):
        self.root = Path(workspace).expanduser().resolve() / "comics"
        self.root.mkdir(parents=True, exist_ok=True)
        if os.name != "nt": self.root.chmod(0o700)
        self._lock = threading.RLock()

    def _project_path(self, id: str):
        if not isinstance(id, str) or not ID.fullmatch(id):
            raise ProviderError("Invalid comic project ID")
        path = self.root / id
        if path.is_symlink() or not path.is_dir() or not (path / "comic.json").is_file():
            raise ProviderError("Comic project not found")
        return path

    def _read(self, id):
        path = self._project_path(id)
        data = json.loads((path / "comic.json").read_text(encoding="utf-8"))
        return path, data

    def _write(self, path, data):
        staged = path / ("." + uuid.uuid4().hex + ".tmp")
        try:
            staged.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            if os.name != "nt": staged.chmod(0o600)
            os.replace(staged, path / "comic.json")
        finally:
            staged.unlink(missing_ok=True)

    def list(self):
        result = []
        for p in self.root.iterdir():
            if not ID.fullmatch(p.name) or p.is_symlink() or not p.is_dir():
                continue
            try:
                _, doc = self._read(p.name)
                result.append({"id": p.name, "title": doc["title"], "pages": len(doc["pages"]),
                               "regions": len(doc["regions"]),
                               "translated": sum(bool(r["target"].strip()) for r in doc["regions"])})
            except (OSError, ValueError, KeyError):
                continue
        return sorted(result, key=lambda r:r["id"], reverse=True)

    def create(self, *, filename, image, rights_confirmed, title=""):
        if rights_confirmed is not True:
            raise ProviderError("You must confirm permission to process the page")
        title = _validate_text(title, "title", 160)
        id = uuid.uuid4().hex
        with self._lock:
            path = self.root / id
            path.mkdir(mode=0o700)
            try:
                record = {"id": id, "title": title.strip() or Path(filename).stem[:160],
                          "created_at": _now(), "pages": [], "regions": []}
                self._write(path, record)
                self._add_page_locked(path, record, filename, image)
                return self.get(id)
            except Exception:
                import shutil
                shutil.rmtree(path)
                raise

    def _add_page_locked(self, path, doc, filename, image):
        if not isinstance(filename, str) or not (1 <= len(filename) <= 180) or any(c in filename for c in "/\\\x00"):
            raise ProviderError("Invalid image filename")
        if not isinstance(image, bytes) or not (32 <= len(image) <= MAX_PAGE_BYTES):
            raise ProviderError("Image exceeds the size limit")
        fmt, width, height = image_size(image)
        if Path(filename).suffix.lower() not in ({"png": (".png",), "jpg": (".jpg", ".jpeg")}[fmt]):
            raise ProviderError("Filename extension disagrees with image format")
        if len(doc["pages"]) >= MAX_PAGES:
            raise ProviderError("Comic project page limit reached")
        id = uuid.uuid4().hex
        pages = path / "pages"; pages.mkdir(exist_ok=True)
        name = f"{id}.{fmt}"
        file = pages / name
        file.write_bytes(image)
        if os.name != "nt": file.chmod(0o600)
        doc["pages"].append({"id": id, "filename": filename, "image": name,
                             "width": width, "height": height})
        self._write(path, doc)
        return doc["pages"][-1]

    def add_page(self, comic_id, *, filename, image):
        with self._lock:
            path, doc = self._read(comic_id)
            return self._add_page_locked(path, doc, filename, image)

    def get(self, id):
        with self._lock:
            _, doc = self._read(id)
            return json.loads(json.dumps(doc))

    def _page(self, doc, page_id):
        return next((x for x in doc["pages"] if x["id"] == page_id), None)

    def page_bytes(self, id, page_id):
        with self._lock:
            path, doc = self._read(id)
            page = self._page(doc, page_id)
            if not page: raise ProviderError("Page not found")
            file = path / "pages" / page["image"]
            if file.is_symlink() or not file.is_file():
                raise ProviderError("Image not found")
            return file.read_bytes(), "image/png" if file.suffix == ".png" else "image/jpeg"

    def add_region(self, id, *, page_id, box, source="", target=""):
        with self._lock:
            path, doc = self._read(id)
            if not self._page(doc, page_id): raise ProviderError("Page not found")
            if len(doc["regions"]) >= MAX_REGIONS: raise ProviderError("Too many regions")
            region = {"id": uuid.uuid4().hex, "page_id": page_id, "box": _validate_box(box),
                      "source": _validate_text(source, "source"),
                      "target": _validate_text(target, "target"), "revision": 1,
                      "method": "manual" if target.strip() else None,
                      "updated_at": _now()}
            doc["regions"].append(region)
            self._write(path, doc)
            return region

    def edit_region(self, id, region_id, *, source=None, target=None, box=None, expected_revision=None):
        with self._lock:
            path, doc = self._read(id)
            region = next((r for r in doc["regions"] if r["id"] == region_id), None)
            if not region: raise ProviderError("Region not found")
            if expected_revision is not None and region["revision"] != expected_revision:
                raise ProviderError("Region changed in another edit, refresh before saving")
            if source is not None: region["source"] = _validate_text(source, "source")
            if target is not None:
                region["target"] = _validate_text(target, "target")
                region["method"] = "manual" if target.strip() else None
            if box is not None: region["box"] = _validate_box(box)
            region["revision"] += 1
            region["updated_at"] = _now()
            self._write(path, doc)
            return dict(region)

    def translate_region(self, id, region_id, inference, *, provider, model):
        """No tool calling: infer a single region, then compare-and-swap to preserve user edits."""
        with self._lock:
            _, doc = self._read(id)
            region = next((r for r in doc["regions"] if r["id"] == region_id), None)
            if region is None: raise ProviderError("Region not found")
            source = region["source"].strip(); revision = region["revision"]
            if not source: raise ProviderError("Transcribe or OCR the region before translation")
        prompt = ("Translate the following comic dialogue into Simplified Chinese. Preserve character names, "
                  "meaning, and tone. Return ONLY the translated dialogue, not an explanation.\n\n" + source)
        output = inference(prompt)
        if not isinstance(output, str) or not output.strip():
            raise ProviderError("Model returned empty translation")
        output = _validate_text(output.strip(), "target")
        # Avoid overwriting human edits that arrived while inference was running.
        with self._lock:
            self.edit_region(id, region_id, target=output, expected_revision=revision)
            path, doc = self._read(id)
            current = next(r for r in doc["regions"] if r["id"] == region_id)
            current["method"] = "demo" if provider == "mock" else f"{provider}/{model}"[:220]
            self._write(path, doc)
            return dict(current)

    def export_svg(self, id, page_id, *, allow_demo=False):
        with self._lock:
            path, doc = self._read(id)
            page = self._page(doc, page_id)
            if not page: raise ProviderError("Page not found")
            regions = [r for r in doc["regions"] if r["page_id"] == page_id]
            pending = [r for r in regions if r["source"].strip() and not r["target"].strip()]
            if pending and not allow_demo:
                raise ProviderError("Untranslated regions: finish or explicitly allow an incomplete demo export")
            if not allow_demo and any(r["method"] == "demo" for r in regions):
                raise ProviderError("Demo translations cannot be exported as finished work")
            raw = (path / "pages" / page["image"]).read_bytes()
        w, h = page["width"], page["height"]
        mime = "image/png" if page["image"].endswith("png") else "image/jpeg"
        embedded = f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"
        parts = [f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
                 f'<image width="{w}" height="{h}" href="{embedded}"/>']
        for r in regions:
            if not r["target"].strip(): continue
            x, y, rw, rh = r["box"]
            x *= w; y *= h; rw *= w; rh *= h
            font = max(9, min(36, int(min(rh / 2.8, rw / max(2, len(r["target"])) * 1.65))))
            max_chars = max(1, int(rw / (font * .85)))
            text_lines = []
            # Preserve manual newlines and wrap by Unicode codepoint; no language
            # model is asked to position text and no generated SVG markup is trusted.
            for line in r["target"].splitlines() or [r["target"]]:
                while len(line) > max_chars:
                    text_lines.append(line[:max_chars]); line = line[max_chars:]
                text_lines.append(line)
            available = max(1, int(rh // (font * 1.2)))
            if len(text_lines) > available:
                raise ProviderError("Text does not fit region; adjust bounding box or text")
            parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{rw:.1f}" height="{rh:.1f}" rx="3" fill="white"/>')
            for index, line in enumerate(text_lines):
                yy = y + (rh - len(text_lines) * font * 1.2) / 2 + font * (index * 1.2 + 1)
                parts.append(f'<text x="{x+rw/2:.1f}" y="{yy:.1f}" font-family="sans-serif" font-size="{font}" text-anchor="middle" fill="#171717">{html.escape(line, quote=True)}</text>')
        parts.append("</svg>")
        return "\n".join(parts).encode("utf-8")
