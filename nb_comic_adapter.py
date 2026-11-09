"""NaughtyBoddy P5.4: read-only comic translation region contract adapters.

Supports the open NB native-v1 JSON contract and the documented local project
JSON shape from hgmzhn/manga-translator-ui. No model calls or source writeback.
This is an interchange/structural fixture checker, not a language quality test.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

from nb_evalkit import check_comic, read_json as read_fixture, KitError

MAX_INPUT_BYTES = 12 * 1024 * 1024
MAX_REGIONS = 3000
MAX_TEXT_CHARS = 100_000
MAX_PAGE_DIMENSION = 100_000
CONTRACT = "nb-comic-regions-v1"


class AdapterError(ValueError):
    pass


def read_input(path: Path) -> dict:
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise AdapterError("JSON file too large")
    def unique_pairs(pairs: list[tuple[str, Any]]) -> dict:
        out = {}
        for key, value in pairs:
            if key in out:
                raise AdapterError("Duplicate JSON field: " + key)
            out[key] = value
        return out
    try:
        obj = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_pairs)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AdapterError("Malformed JSON file") from exc
    if not isinstance(obj, dict):
        raise AdapterError("Expected top-level JSON object")
    return obj


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) > MAX_TEXT_CHARS:
        raise AdapterError(f"{name} must be bounded text")
    return value


def _positive(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 < value <= MAX_PAGE_DIMENSION:
        raise AdapterError(f"Invalid {name}")
    return float(value)


def _bbox(box: Any) -> list[float]:
    if not isinstance(box, list) or len(box) != 4 or any(
        isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in box
    ):
        raise AdapterError("bbox must contain four finite coordinates")
    coords = [float(v) for v in box]
    if not (0 <= coords[0] < coords[2] <= 1 and 0 <= coords[1] < coords[3] <= 1):
        raise AdapterError("bbox must be normalized [x0,y0,x1,y1]")
    return [round(v, 6) for v in coords]


def _from_lines(lines: Any, width: float, height: float) -> list[float]:
    if not isinstance(lines, list) or not lines or len(lines) > 50:
        raise AdapterError("Expected one or more quadrilateral OCR lines")
    xs, ys = [], []
    for line in lines:
        if not isinstance(line, list) or len(line) != 4:
            raise AdapterError("OCR line must be a 4-point polygon")
        for point in line:
            if (not isinstance(point, list) or len(point) != 2 or any(
                isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x)
                for x in point)):
                raise AdapterError("Bad OCR point")
            x, y = point
            if not (0 <= x <= width and 0 <= y <= height):
                raise AdapterError("OCR point outside page")
            xs.append(float(x)); ys.append(float(y))
    if min(xs) == max(xs) or min(ys) == max(ys):
        raise AdapterError("Degenerate OCR quadrilateral")
    return _bbox([min(xs)/width, min(ys)/height, max(xs)/width, max(ys)/height])


def _validate_records(records: list[dict], page_id: str, source_format: str, stability: str) -> dict:
    if not 0 < len(page_id) <= 120 or not page_id.replace("-", "").replace("_", "").isalnum():
        raise AdapterError("page_id must be an opaque alphanumeric alias")
    if not isinstance(records, list) or len(records) > MAX_REGIONS:
        raise AdapterError("Too many regions")
    ids = set()
    out = []
    for i, row in enumerate(records):
        if not isinstance(row, dict):
            raise AdapterError("Each region must be an object")
        ident = row.get("id")
        if not isinstance(ident, str) or not ident or len(ident) > 128 or ident in ids:
            raise AdapterError("Region ID missing, duplicate, or too long")
        ids.add(ident)
        source = _text(row.get("source"), "source")
        target = _text(row.get("translation"), "translation")
        box = _bbox(row.get("bbox")) if row.get("bbox") is not None else None
        out.append({"id": ident, "source": source, "translation": target,
                    "bbox": box, "reading_order": i})
    return {"schema_version": 1, "contract": CONTRACT,
            "page_id": page_id, "source_format": source_format,
            "id_stability": stability, "regions": out,
            "warning": "Interop only; no natural-language fidelity, privacy, OCR or NSFW compatibility assessment."}


def from_native(data: dict) -> dict:
    if data.get("schema_version") != 1 or data.get("contract") != CONTRACT:
        raise AdapterError("Expected nb-comic-regions-v1")
    page_id = data.get("page_id")
    if not isinstance(page_id, str):
        raise AdapterError("Missing page_id")
    stability = data.get("id_stability", "explicit_ids")
    if stability not in {"explicit_ids", "positional_unstable", "mapped_source_guard"}:
        raise AdapterError("Unknown ID stability")
    return _validate_records(data.get("regions"), page_id, "nb-native-v1", stability)


def _mapping_table(mapping: dict | None, count: int) -> list[dict] | None:
    if mapping is None:
        return None
    if mapping.get("schema_version") != 1 or not isinstance(mapping.get("regions"), list):
        raise AdapterError("Mapping must include schema_version=1 and regions")
    rows = mapping["regions"]
    if len(rows) != count or len(rows) > MAX_REGIONS:
        raise AdapterError("Mapping must cover exactly every detected region")
    by_index = {}
    ids = set()
    for row in rows:
        if not isinstance(row, dict):
            raise AdapterError("Bad region map entry")
        index, rid = row.get("index"), row.get("id")
        if isinstance(index, bool) or not isinstance(index, int) or index < 0 or index >= count or index in by_index:
            raise AdapterError("Duplicate or invalid region map index")
        if not isinstance(rid, str) or not rid or rid in ids:
            raise AdapterError("Duplicate or invalid stable mapped ID")
        _text(row.get("source"), "mapped source")
        if row.get("bbox") is not None:
            _bbox(row["bbox"])
        by_index[index] = row
        ids.add(rid)
    if len(by_index) != count:
        raise AdapterError("Incomplete mapping")
    # Repeated dialogue is common: require a spatial anchor if source alone is ambiguous.
    counts = {}
    for row in rows:
        counts[row["source"]] = counts.get(row["source"], 0) + 1
    for row in rows:
        if counts[row["source"]] > 1 and "bbox" not in row:
            raise AdapterError("Repeated source needs a bbox mapping anchor")
    return [by_index[i] for i in range(count)]


def from_manga_translator_ui(data: dict, page_id: str, mapping: dict | None) -> dict:
    """Read documented per-image project JSON; never rewrite original masks/styles.

    Official data shape: {absolute_image_path: {regions:[{text,translation,lines}],...}}
    with legacy region list allowed. A separate explicit index+OCR text map is
    required to associate the result with P5.3 stable IDs.
    """
    if len(data) != 1:
        raise AdapterError("Upstream project JSON must contain exactly one image")
    # Do not include real original path in contract/report; user-provided safe alias only.
    content = next(iter(data.values()))
    if isinstance(content, dict):
        regions = content.get("regions")
        width = content.get("original_width")
        height = content.get("original_height")
    elif isinstance(content, list):
        regions = content
        width = height = None
    else:
        raise AdapterError("Unsupported manga-translator-ui document structure")
    if not isinstance(regions, list) or len(regions) > MAX_REGIONS:
        raise AdapterError("Missing or oversized upstream regions list")
    pairs = _mapping_table(mapping, len(regions))
    extracted = []
    for index, item in enumerate(regions):
        if not isinstance(item, dict):
            raise AdapterError("Malformed OCR region")
        original = _text(item.get("text"), "OCR text")
        target = _text(item.get("translation", ""), "translation")
        if item.get("lines") is not None:
            if width is None or height is None:
                raise AdapterError("Page dimensions needed for OCR quadrilateral coordinates")
            box = _from_lines(item["lines"], _positive(width, "width"), _positive(height, "height"))
        else:
            box = None
        if pairs is None:
            rid = f"pos-{index+1:04d}"
        else:
            pair = pairs[index]
            if pair["source"] != original:
                raise AdapterError(f"OCR source mismatch at region {index}: refresh mapping")
            rid = pair["id"]
            if pair.get("bbox") is not None:
                if box is None or any(abs(a-b)>0.01 for a,b in zip(pair["bbox"], box)):
                    raise AdapterError(f"Bounding box mismatch at region {index}: refresh mapping")
        extracted.append({"id": rid, "source": original, "translation": target, "bbox": box})
    return _validate_records(extracted, page_id, "manga-translator-ui-project-json",
                             "mapped_source_guard" if pairs else "positional_unstable")


def to_evalkit_candidate(contract: dict) -> dict:
    if contract.get("contract") != CONTRACT or contract.get("id_stability") not in {"mapped_source_guard", "explicit_ids"}:
        raise AdapterError("Reliable stable IDs or an explicit map are required for P5.3 audit")
    return {"outputs": [{"id": row["id"], "text": row["translation"]} for row in contract["regions"]]}


def audit(case: dict, contract: dict) -> dict:
    """Only compare synthetic targets. Reject unknown IDs and non-demo material by default."""
    target = [b.get("target_token") for b in case.get("bubbles", [])]
    if not target or not all(isinstance(t, str) and t.startswith("TGT_B") for t in target):
        raise AdapterError("P5.3 audit only accepts synthetic sentinel cases")
    result = check_comic(case, to_evalkit_candidate(contract))
    # Neither original image paths nor private source/translation text in report.
    return result


def atomic_output(path: Path, value: dict, overwrite: bool = False) -> None:
    path = path.resolve()
    if path.exists() and not overwrite:
        raise AdapterError("Output exists; use --overwrite to replace explicitly")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".nbcomic-", dir=path.parent, suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def main(argv: list[str] | None = None) -> int:
    cli = argparse.ArgumentParser(description="Read-only comic JSON interchange; standard library only")
    sub = cli.add_subparsers(dest="action", required=True)
    imp = sub.add_parser("import", help="Convert JSON; never changes upstream project")
    imp.add_argument("--format", choices=["nb-native", "manga-translator-ui"], required=True)
    imp.add_argument("--input", type=Path, required=True)
    imp.add_argument("--page-id", default="page-1", help="Opaque alias, not a file path")
    imp.add_argument("--mapping", type=Path, help="Explicit stable ID to OCR source mapping")
    imp.add_argument("--output", type=Path, help="Optional local JSON destination")
    imp.add_argument("--overwrite", action="store_true")
    imp.add_argument("--audit-case", type=Path, help="Optional P5.3 synthetic sentinel case")
    val = sub.add_parser("audit", help="Audit existing NB contract with P5.3 synthetic fixture")
    val.add_argument("--input", type=Path, required=True)
    val.add_argument("--case", type=Path, default=Path(__file__).parent / "benchmarks/p53/comic_case.json")
    args = cli.parse_args(argv)
    try:
        if args.action == "audit":
            data = from_native(read_input(args.input))
            result = audit(read_fixture(args.case), data)
        else:
            raw = read_input(args.input)
            if args.format == "nb-native":
                result = from_native(raw)
            else:
                mapping = read_input(args.mapping) if args.mapping else None
                result = from_manga_translator_ui(raw, args.page_id, mapping)
            audit_result = audit(read_fixture(args.audit_case), result) if args.audit_case else None
            region_count = len(result["regions"])
            stability = result["id_stability"]
            if args.output:
                atomic_output(args.output, result, args.overwrite)
            # Always output a sanitized summary, even when --output saves local private text.
            result = {"saved": bool(args.output), "regions": region_count,
                      "id_stability": stability,
                      "message": "Private normalized contract is only written via --output; original is unchanged."}
            if audit_result is not None:
                result["audit"] = audit_result
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("passed", True) and result.get("audit", {}).get("passed", True) else 1
    except (AdapterError, KitError, OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
