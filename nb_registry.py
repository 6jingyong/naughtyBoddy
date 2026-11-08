"""NaughtyBoddy P5: offline, evidence-conscious needs/solutions/gaps registry.

The registry is editorial metadata, not an AI benchmark, installer, network crawler,
or executable plugin host. It never reads personal creative assets or makes requests.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

DEFAULT_ROOT = Path(__file__).resolve().parent / "registry"
MAX_RECORD_BYTES = 256_000
ID_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
STATES = {"hypothesis", "reported", "documentation_reviewed", "hands_on_verified"}
FIT = {"unknown", "partial", "meets", "does_not_meet"}
CHECK_RESULTS = {"not_run", "pass", "fail", "inconclusive"}
KINDS = ("needs", "solutions", "assessments", "gaps", "frictions")
FRICTION_STATES = {"documented_behavior", "reported_unreproduced"}
FRICTION_SOURCE_TYPES = {"upstream_docs", "upstream_issue", "community_report"}
MITIGATION_STATES = {"documented", "proposed", "unknown"}


class RegistryError(ValueError):
    """Malformed or inconsistent records; unsuitable for published recommendations."""


def _require(ok: bool, path: str, message: str, errors: list[str]) -> None:
    if not ok:
        errors.append(f"{path}: {message}")


def _str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _strings(value: Any) -> bool:
    return isinstance(value, list) and all(_str(item) for item in value)


def _safe_url(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("https://") and len(value) > 9


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict:
    output = {}
    for key, val in pairs:
        if key in output:
            raise RegistryError(f"duplicate JSON field: {key}")
        output[key] = val
    return output


def _load_directory(root: Path, kind: str, errors: list[str]) -> list[dict]:
    folder = root / kind
    if not folder.is_dir():
        errors.append(f"{kind}/: missing directory")
        return []
    records: list[dict] = []
    for path in sorted(folder.glob("*.json")):
        try:
            if path.is_symlink():
                raise RegistryError("symlink record is not allowed")
            if path.stat().st_size > MAX_RECORD_BYTES:
                raise RegistryError("record exceeds size limit")
            entry = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicate_keys)
            if not isinstance(entry, dict):
                raise RegistryError("expected a JSON object")
            entry["_file"] = f"{kind}/{path.name}"
            records.append(entry)
        except (OSError, UnicodeError, json.JSONDecodeError, RegistryError) as exc:
            errors.append(f"{kind}/{path.name}: {exc}")
    return records


def read_registry(root: Path = DEFAULT_ROOT) -> tuple[dict[str, list[dict]], list[str]]:
    """Read all records, validate cross references; never follow external links."""
    root = Path(root)
    errors: list[str] = []
    data = {kind: _load_directory(root, kind, errors) for kind in KINDS}
    ids: dict[str, set[str]] = {}
    all_ids: set[str] = set()
    for kind, rows in data.items():
        ids[kind] = set()
        for row in rows:
            place = row["_file"]
            identifier = row.get("id")
            _require(row.get("schema_version") == 1, place, "schema_version must be 1", errors)
            _require(isinstance(identifier, str) and ID_RE.fullmatch(identifier) is not None,
                     place, "id must be kebab-case", errors)
            if isinstance(identifier, str):
                _require(identifier not in ids[kind], place, f"duplicate id {identifier}", errors)
                _require(identifier not in all_ids, place, f"id collides across kinds: {identifier}", errors)
                ids[kind].add(identifier)
                all_ids.add(identifier)
                _require(Path(place).stem == identifier, place, "filename must match id", errors)
            _require(_str(row.get("title")), place, "title required", errors)
            state = row.get("evidence_status", "hypothesis")
            _require(state in STATES, place, "invalid evidence_status", errors)
            if kind in ("needs", "solutions"):
                _require(_strings(row.get("tags")), place, "tags must be string array", errors)
                _require(_str(row.get("summary")), place, "summary required", errors)
            if kind == "needs":
                checks = row.get("acceptance_checks")
                _require(isinstance(checks, list) and len(checks) > 0 and
                         all(isinstance(v, dict) and _str(v.get("id")) and _str(v.get("method"))
                             and _str(v.get("criterion")) for v in checks),
                         place, "nonempty acceptance_checks with id, criterion and method required", errors)
                if isinstance(checks, list):
                    keys = [v.get("id") for v in checks if isinstance(v, dict)]
                    _require(len(keys) == len(set(keys)), place, "acceptance check IDs must be unique", errors)
                _require(row.get("status") in ("proposed", "interviewed", "observed"),
                         place, "invalid demand validation status", errors)
            elif kind == "solutions":
                _require(_safe_url(row.get("url")), place, "public HTTPS project URL required", errors)
                _require(row.get("license") is None or _str(row.get("license")),
                         place, "license must be a string or null (unknown)", errors)
                if row.get("license") is not None:
                    _require(_safe_url(row.get("license_source")),
                             place, "confirmed license requires source URL", errors)
                _require(row.get("verification") in ("unreviewed", "documentation_reviewed", "hands_on_verified"),
                         place, "verification must be explicit", errors)
                sources = row.get("sources")
                _require(isinstance(sources, list) and all(_safe_url(s) for s in sources),
                         place, "sources must contain HTTPS URLs", errors)
                if row.get("verification") != "unreviewed":
                    _require(bool(sources), place, "verified solution requires source URLs", errors)
            elif kind == "assessments":
                _require(_str(row.get("need_id")) and _str(row.get("solution_id")),
                         place, "need_id and solution_id required", errors)
                _require(row.get("fit") in FIT, place, "invalid fit", errors)
                check_results = row.get("check_results")
                _require(isinstance(check_results, list) and all(isinstance(v, dict) and
                         _str(v.get("check_id")) and v.get("result") in CHECK_RESULTS for v in check_results),
                         place, "check_results must be list of check_id/result records", errors)
                observations = row.get("observations")
                _require(_strings(observations), place, "observations must be string array", errors)
                if row.get("fit") in ("meets", "partial", "does_not_meet"):
                    _require(row.get("evidence_status") in ("documentation_reviewed", "hands_on_verified") and
                             bool(observations), place, "a fit verdict needs reviewed evidence and observations", errors)
                if row.get("fit") == "meets":
                    _require(state == "hands_on_verified" and bool(check_results) and
                             all(x.get("result") == "pass" for x in check_results or [] if isinstance(x, dict)),
                             place, "meets requires hands-on passed checks", errors)
                if state == "hands_on_verified":
                    _require(_str(row.get("environment")) and
                             any(x.get("result") != "not_run" for x in check_results or [] if isinstance(x, dict)),
                             place, "hands_on_verified needs environment and executed checks", errors)
            elif kind == "frictions":
                _require(_str(row.get("need_id")), place, "need_id required", errors)
                _require(_strings(row.get("solution_ids")) and bool(row.get("solution_ids")),
                         place, "solution_ids must be nonempty string array", errors)
                _require(_str(row.get("symptom")) and _str(row.get("user_impact")) and
                         _str(row.get("remaining_question")) and _str(row.get("verification_plan")),
                         place, "symptom, impact, question and verification plan required", errors)
                _require(row.get("status") in FRICTION_STATES, place, "invalid friction status", errors)
                _require(row.get("source_type") in FRICTION_SOURCE_TYPES, place, "invalid friction source type", errors)
                sources = row.get("sources")
                _require(isinstance(sources, list) and bool(sources) and all(_safe_url(u) for u in sources),
                         place, "friction requires HTTPS evidence URLs", errors)
                _require(_str(row.get("reviewed_on")), place, "reviewed_on required", errors)
                if row.get("source_type") == "upstream_docs":
                    _require(state == "documentation_reviewed" and row.get("status") == "documented_behavior",
                             place, "upstream docs must describe a documented behavior", errors)
                else:
                    _require(state == "reported" and row.get("status") == "reported_unreproduced",
                             place, "community or issue reports are not hands-on verification", errors)
                mitigation = row.get("existing_mitigation")
                _require(isinstance(mitigation, dict) and mitigation.get("status") in MITIGATION_STATES and
                         _strings(mitigation.get("steps")) and
                         isinstance(mitigation.get("sources"), list) and
                         all(_safe_url(u) for u in mitigation.get("sources", [])),
                         place, "mitigation status/steps/sources invalid", errors)
                if isinstance(mitigation, dict) and mitigation.get("status") == "documented":
                    _require(bool(mitigation.get("steps")) and bool(mitigation.get("sources")),
                             place, "documented mitigation requires steps and sources", errors)
                _require(_strings(row.get("gap_ids", [])), place, "gap_ids must be string array", errors)
            elif kind == "gaps":
                _require(_str(row.get("need_id")), place, "need_id required", errors)
                _require(row.get("status") in ("unverified", "reported", "reproduced", "resolved"),
                         place, "invalid gap status", errors)
                _require(_str(row.get("verification_plan")), place, "verification_plan required", errors)
    needs = {x.get("id"): x for x in data["needs"]}
    for row in data["assessments"]:
        place = row["_file"]
        _require(row.get("need_id") in ids["needs"], place, "unknown need_id", errors)
        _require(row.get("solution_id") in ids["solutions"], place, "unknown solution_id", errors)
        for check in row.get("check_results", []):
            if isinstance(check, dict) and row.get("need_id") in needs:
                known = {c["id"] for c in needs[row["need_id"]].get("acceptance_checks", []) if isinstance(c, dict) and "id" in c}
                _require(check.get("check_id") in known, place, "unknown acceptance check", errors)
    for row in data["assessments"]:
        if row.get("fit") == "meets" and row.get("need_id") in needs:
            required = {c["id"] for c in needs[row["need_id"]].get("acceptance_checks", []) if isinstance(c, dict) and "id" in c}
            passed = {c.get("check_id") for c in row.get("check_results", []) if isinstance(c, dict) and c.get("result") == "pass"}
            _require(required.issubset(passed), row["_file"], "meets requires every acceptance check to pass", errors)
    for row in data["gaps"]:
        _require(row.get("need_id") in ids["needs"], row["_file"], "unknown need_id", errors)
    for row in data["frictions"]:
        place = row["_file"]
        _require(row.get("need_id") in ids["needs"], place, "unknown need_id", errors)
        for target in row.get("solution_ids", []):
            _require(target in ids["solutions"], place, f"unknown solution_id: {target}", errors)
        for target in row.get("gap_ids", []):
            _require(target in ids["gaps"], place, f"unknown gap_id: {target}", errors)
    return data, errors


def friction_for_need(data: dict[str, list[dict]], need_id: str) -> list[dict]:
    if not any(x["id"] == need_id for x in data["needs"]):
        raise RegistryError(f"Unknown need: {need_id}")
    return sorted((x for x in data["frictions"] if x["need_id"] == need_id),
                  key=lambda x: x["id"])


def match_need(data: dict[str, list[dict]], need_id: str) -> dict:
    needs = {row["id"]: row for row in data["needs"]}
    if need_id not in needs:
        raise RegistryError(f"Unknown need: {need_id}")
    need = needs[need_id]
    tags = set(need["tags"])
    by_pair = {(x["need_id"], x["solution_id"]): x for x in data["assessments"]}
    candidates = []
    frictions = data.get("frictions", [])
    for tool in data["solutions"]:
        shared = sorted(tags.intersection(tool["tags"]))
        assessment = by_pair.get((need_id, tool["id"]))
        if shared or assessment:
            candidates.append({"solution_id": tool["id"], "name": tool["title"],
                               "url": tool["url"], "matching_tags": shared,
                               "verification": tool["verification"],
                               "fit": assessment["fit"] if assessment else "unknown",
                               "assessment_id": assessment["id"] if assessment else None,
                               "related_friction_ids": sorted(x["id"] for x in frictions
                                                              if x["need_id"] == need_id and tool["id"] in x["solution_ids"]),
                               "caution": "Tag overlap is discovery only, not a quality or compatibility verdict."})
    candidates.sort(key=lambda c: (-len(c["matching_tags"]), c["solution_id"]))
    return {"need": need, "candidates": candidates,
            "gaps": [g for g in data["gaps"] if g["need_id"] == need_id],
            "frictions": friction_for_need(data, need_id)}


def main(argv: list[str] | None = None) -> int:
    cli = argparse.ArgumentParser(description="NaughtyBoddy P5: needs → solutions → gaps (offline)")
    cli.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Registry directory")
    sub = cli.add_subparsers(dest="action", required=True)
    sub.add_parser("validate", help="Check schema, evidence discipline and references")
    sub.add_parser("needs", help="Show needs and their research status")
    sub.add_parser("solutions", help="Show existing solutions and verification state")
    m = sub.add_parser("match", help="Discover candidate solutions, NOT validated recommendations")
    m.add_argument("need_id")
    sub.add_parser("gaps", help="Show unmet-need hypotheses and validation status")
    f = sub.add_parser("frictions", help="Show sourced friction reports and mitigations")
    f.add_argument("--need", help="Optional need ID filter")
    args = cli.parse_args(argv)
    db, errors = read_registry(args.root)
    if errors:
        print(json.dumps({"valid": False, "errors": errors}, ensure_ascii=False, indent=2))
        return 1
    if args.action == "validate":
        result: Any = {"valid": True, "counts": {k: len(v) for k, v in db.items()}}
    elif args.action == "match":
        try:
            result = match_need(db, args.need_id)
        except RegistryError as e:
            print(str(e), file=sys.stderr)
            return 2
    elif args.action == "gaps":
        result = db["gaps"]
    elif args.action == "frictions":
        try:
            result = friction_for_need(db, args.need) if args.need else db["frictions"]
        except RegistryError as exc:
            print(str(exc), file=sys.stderr)
            return 2
    else:
        result = db[args.action]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
