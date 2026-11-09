"""P5.10: bounded, read-only text-ecosystem interoperability graph.

Nodes are stable P5 catalogue IDs or an explicitly permitted *format* node.
The graph states documented connections, model-file support and limited protocol
candidates; it never proves real-world model compatibility, privacy or quality.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

DATA_PATH = Path(__file__).resolve().parent / "catalog" / "text-compatibility.json"
MAX_BYTES = 140_000
RELATIONS = {
    "client_backend", "extension_for", "needs_extension_for_isolation",
    "runtime_format", "protocol_candidate",
}
API_PROFILES = {
    "koboldcpp_native", "ollama_native", "openai_subset",
    "extension_host", "presence_metadata", "gguf_model_file",
}
STATUS = {"documented", "protocol_inferred_not_tested"}
FORMATS = {"format:gguf": "GGUF 模型文件"}


class CompatibilityError(ValueError):
    pass


def _https(raw: object) -> bool:
    if not isinstance(raw, str) or len(raw) > 1800:
        return False
    try:
        p = urlsplit(raw)
        return p.scheme == "https" and bool(p.hostname) and not p.username and not p.password
    except ValueError:
        return False


def _string_list(raw: object, *, min_size: int = 1) -> bool:
    return isinstance(raw, list) and len(raw) >= min_size and all(
        isinstance(item, str) and 0 < len(item) <= 600 for item in raw)


def load_graph(path: Path = DATA_PATH, item_ids: set[str] | None = None) -> dict:
    if path.is_symlink() or path.stat().st_size > MAX_BYTES:
        raise CompatibilityError("Compatibility graph oversized or symlinked")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CompatibilityError("Invalid graph JSON") from exc
    if not isinstance(data, dict) or data.get("schema_version") != 1 or data.get("scope") != "text_only":
        raise CompatibilityError("Unsupported compatibility graph schema/scope")
    rows = data.get("edges")
    if not isinstance(rows, list) or not rows:
        raise CompatibilityError("No graph edges")
    if not isinstance(data.get("allowed_format_targets"), list):
        raise CompatibilityError("Format targets missing")
    allowed_formats = {x["id"] for x in data["allowed_format_targets"] if isinstance(x, dict) and "id" in x}
    if allowed_formats != set(FORMATS):
        raise CompatibilityError("Unknown or missing model-format targets")
    seen_ids = set()
    for edge in rows:
        if not isinstance(edge, dict):
            raise CompatibilityError("Malformed compatibility edge")
        rid = edge.get("id")
        if not isinstance(rid, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", rid) or rid in seen_ids:
            raise CompatibilityError("Duplicate/malformed edge id")
        seen_ids.add(rid)
        relation, status = edge.get("relation"), edge.get("evidence_status")
        if relation not in RELATIONS or status not in STATUS or edge.get("api_profile") not in API_PROFILES:
            raise CompatibilityError("Unsupported relation, API profile or evidence status")
        if (relation == "protocol_candidate") != (status == "protocol_inferred_not_tested"):
            raise CompatibilityError("Protocol candidates must not be presented as documented integrations")
        if relation == "runtime_format":
            if edge.get("to_id") not in allowed_formats or edge.get("api_profile") != "gguf_model_file":
                raise CompatibilityError("Runtime-format edge needs explicit format target")
        elif not isinstance(edge.get("to_id"), str) or edge["to_id"].startswith("format:"):
            raise CompatibilityError("Invalid tool-to-tool edge target")
        if not isinstance(edge.get("from_id"), str) or edge["from_id"] == edge["to_id"]:
            raise CompatibilityError("Invalid edge source or self-reference")
        if item_ids is not None:
            if edge["from_id"] not in item_ids:
                raise CompatibilityError("Unknown/out-of-scope frontend ID: " + edge["from_id"])
            if relation != "runtime_format" and edge["to_id"] not in item_ids:
                raise CompatibilityError("Unknown/out-of-scope backend ID: " + edge["to_id"])
        if not _string_list(edge.get("source_urls")) or not all(_https(x) for x in edge["source_urls"]):
            raise CompatibilityError("Every edge requires public HTTPS primary documentation")
        if not _string_list(edge.get("setup_steps")) or not isinstance(edge.get("limitations"), str) or not edge["limitations"].strip():
            raise CompatibilityError("Each edge requires setup steps and explicit limitations")
        if not isinstance(edge.get("verification_plan"), str) or not edge["verification_plan"].strip():
            raise CompatibilityError("Each edge requires a future hands-on verification plan")
        try:
            date.fromisoformat(edge["reviewed_on"])
        except (KeyError, TypeError, ValueError) as exc:
            raise CompatibilityError("Missing/invalid review date") from exc
        if edge.get("actual_connection_test") != "not_run":
            raise CompatibilityError("No hands-on connection tests were performed in P5.10")
        hint = edge.get("endpoint_hint")
        if hint is not None and (not isinstance(hint, str) or not re.fullmatch(
                r"http://(?:localhost|127\.0\.0\.1):[0-9]{2,5}(?:/v1)?", hint)):
            raise CompatibilityError("Only non-executable loopback example endpoints are permitted")
    return data


def annotate_connections(items: list[dict], graph: dict) -> dict:
    by_id = {item["id"]: item for item in items}
    if len(by_id) != len(items):
        raise CompatibilityError("Duplicate catalogue IDs")
    counts = Counter()
    for item in items:
        item["connections"] = []
        item["integration_tags"] = []
    for edge in graph["edges"]:
        src = edge["from_id"]
        target = edge["to_id"]
        if src not in by_id or (target not in by_id and target not in FORMATS):
            raise CompatibilityError("Graph references a missing item")
        counts[edge["relation"]] += 1
        for item_id, opposite, direction in (
            (src, target, "outgoing"),
            (target, src, "incoming"),
        ):
            if item_id not in by_id:
                continue
            opposite_name = by_id[opposite]["name"] if opposite in by_id else FORMATS[opposite]
            row = {
                "id": edge["id"], "relation": edge["relation"],
                "direction": direction, "other_id": opposite,
                "other_name": opposite_name, "api_profile": edge["api_profile"],
                "evidence_status": edge["evidence_status"],
                "source_urls": edge["source_urls"],
                "reviewed_on": edge["reviewed_on"],
                "setup_steps": edge["setup_steps"],
                "limitations": edge["limitations"],
                "verification_plan": edge["verification_plan"],
                "actual_connection_test": "not_run",
                "endpoint_hint": edge.get("endpoint_hint"),
            }
            by_id[item_id]["connections"].append(row)
            if (edge["evidence_status"] == "documented"
                    and edge["relation"] in {"client_backend", "extension_for", "needs_extension_for_isolation"}):
                by_id[item_id]["integration_tags"].append(edge["api_profile"])
    for item in items:
        item["connections"].sort(key=lambda r: (r["evidence_status"] != "documented", r["relation"], r["id"]))
        item["integration_tags"] = sorted(set(item["integration_tags"]))
    return {
        "edge_count": len(graph["edges"]),
        "documented_edges": sum(e["evidence_status"] == "documented" for e in graph["edges"]),
        "protocol_candidates": sum(e["evidence_status"] == "protocol_inferred_not_tested" for e in graph["edges"]),
        "types": dict(counts),
        "named_model_backend_compatibility_tests": 0,
        "actual_connection_tests": 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline text compatibility graph — no model or network")
    parser.add_argument("action", choices=["validate", "list", "candidates", "for-item"])
    parser.add_argument("--item", help="Exact text-catalogue item ID (only for for-item)")
    args = parser.parse_args(argv)
    try:
        from nb_text_catalog import text_catalogue
        current = text_catalogue()
        graph = load_graph(item_ids={row["id"] for row in current["items"]})
        if args.action == "validate":
            result = {"valid": True, **current["compatibility_summary"]}
        elif args.action == "list":
            result = graph["edges"]
        elif args.action == "candidates":
            result = [x for x in graph["edges"] if x["evidence_status"] == "protocol_inferred_not_tested"]
        else:
            if args.item is None:
                raise CompatibilityError("--item is required for for-item")
            item = next((x for x in current["items"] if x["id"] == args.item), None)
            if not item:
                raise CompatibilityError("Item is not in the text-first catalogue")
            result = {"item": item["name"], "connections": item["connections"]}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (CompatibilityError, OSError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
