"""P5.8 partial, provenance-based catalogue maintenance.

This module is intentionally OFFLINE. It consumes a dated spot-check snapshot
rather than resolving user-submitted URLs or scraping third-party websites.
Repository metadata availability is not a download/quality/NSFW compatibility test.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent / "catalog" / "link-health.json"
MAX_HEALTH_BYTES = 250_000
RESULTS = {"repository_metadata_found", "conflicting_evidence"}
LINK_STATES = {"repository_metadata_found", "conflicting_evidence", "not_checked"}


class HealthError(ValueError):
    pass


def _url(value: object, host: str | None = None) -> bool:
    if not isinstance(value, str) or len(value) > 1500:
        return False
    try:
        u = urlsplit(value)
        if u.scheme != "https" or not u.hostname or u.username or u.password:
            return False
        if host is not None and u.hostname.lower() != host:
            return False
        return True
    except ValueError:
        return False


def url_key(raw: str) -> str:
    """Use for review candidates, NEVER as automatic proof of identity."""
    u = urlsplit(raw)
    host = (u.hostname or "").lower().removeprefix("www.")
    return host + u.path.rstrip("/").casefold()


def name_key(raw: str) -> str:
    return re.sub(r"[^a-z0-9\u4e00-\u9fff]", "", raw.casefold())


def load_link_health(path: Path = ROOT) -> dict:
    if path.is_symlink() or path.stat().st_size > MAX_HEALTH_BYTES:
        raise HealthError("Link-health snapshot is oversized or a symlink")
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise HealthError("Invalid link-health JSON") from exc
    if not isinstance(doc, dict) or doc.get("schema_version") != 1:
        raise HealthError("Unsupported link-health version")
    rows = doc.get("observations")
    migrations = doc.get("migrations")
    if not isinstance(rows, list) or not isinstance(migrations, list):
        raise HealthError("Observations and migrations must be lists")
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise HealthError("Invalid health observation")
        rid = row.get("item_id")
        if not isinstance(rid, str) or rid in seen or not rid:
            raise HealthError("Repeated or missing item ID in health snapshot")
        seen.add(rid)
        if (row.get("result") not in RESULTS or row.get("method") != "github_public_repository_api"
                or not _url(row.get("item_url"), "github.com")
                or not _url(row.get("evidence_url"), "api.github.com")):
            raise HealthError("Health observation lacks a legitimate GitHub evidence source")
        try:
            date.fromisoformat(row["checked_on"])
        except (KeyError, TypeError, ValueError) as exc:
            raise HealthError("Health check needs ISO calendar date") from exc
        if row["result"] == "repository_metadata_found":
            if (row.get("archived") not in (True, False) or
                    row.get("disabled") not in (True, False) or
                    not isinstance(row.get("canonical_repo"), str)):
                raise HealthError("Repository metadata observation incomplete")
            try:
                from datetime import datetime
                datetime.fromisoformat(row["pushed_at"].replace("Z", "+00:00"))
            except (KeyError, ValueError, AttributeError) as exc:
                raise HealthError("Metadata check needs valid last-push timestamp") from exc
            if (url_key(row["item_url"]) !=
                    url_key("https://github.com/" + row["canonical_repo"])):
                raise HealthError("Repository canonical path conflicts with observed URL")
        else:
            if not _url(row.get("secondary_evidence_url")) or not isinstance(row.get("observation"), str):
                raise HealthError("Conflicting link status needs independent context")
        if not isinstance(row.get("caution"), str) or not row["caution"]:
            raise HealthError("Evidence limits must be stated")
    for row in migrations:
        if not isinstance(row, dict) or not all(_url(row.get(k), h) for k, h in (
            ("former_url", "github.com"), ("canonical_url", "github.com"),
            ("evidence_url", "api.github.com"))):
            raise HealthError("Migration needs both URLs and primary GitHub evidence")
        if row.get("observed_response") != "Moved Permanently":
            raise HealthError("Migration must be based on an observed redirect")
    return doc


def identity_review(items: list[dict]) -> dict:
    """Identify ambiguous clusters without merging model variants."""
    urls: dict[str, list[dict]] = defaultdict(list)
    names: dict[str, list[dict]] = defaultdict(list)
    for row in items:
        urls[url_key(row["url"])].append(row)
        names[name_key(row["name"])].append(row)
    shared = []
    for key, rows in sorted(urls.items()):
        if len(rows) < 2 or len({name_key(row["name"]) for row in rows}) < 2:
            continue
        shared.append({
            "destination_key": key,
            "items": [{"id": row["id"], "name": row["name"]} for row in rows],
            "interpretation": "shared_destination_not_proof_of_duplicate",
        })
    aliases = []
    for key, rows in sorted(names.items()):
        if len({url_key(row["url"]) for row in rows}) < 2 or not key:
            continue
        aliases.append({
            "name_key": key,
            "items": [{"id": row["id"], "name": row["name"], "url": row["url"]} for row in rows],
            "interpretation": "same_name_different_destination_not_automatically_equivalent",
        })
    return {
        "shared_destinations": shared, "same_name_different_destinations": aliases,
        "policy": "No automatic merge based on destination URL or display name alone.",
    }


def annotate_health(items: list[dict], health: dict) -> dict:
    by_id = {row["id"]: row for row in items}
    status_counts = {key: 0 for key in LINK_STATES}
    for row in items:
        row["link_health"] = "not_checked"
        row["link_check"] = {"state": "not_checked", "checked_on": None,
                             "note": "尚未检查该项目的当前链接与维护状态。"}
    for obs in health["observations"]:
        rid = obs["item_id"]
        if rid not in by_id:
            raise HealthError("Audited item no longer present in catalogue: " + rid)
        target = by_id[rid]
        if url_key(target["url"]) != url_key(obs["item_url"]):
            raise HealthError("Audited destination changed; please recheck: " + rid)
        target["link_health"] = obs["result"]
        if obs["result"] == "repository_metadata_found":
            target["link_check"] = {
                "state": "repository_metadata_found",
                "checked_on": obs["checked_on"], "last_code_push": obs["pushed_at"],
                "repo_archived": obs["archived"], "repo_disabled": obs["disabled"],
                "evidence_url": obs["evidence_url"],
                "note": "GitHub 仓库元数据可读取；不代表软件已安装、模型可运行或项目持续维护。",
            }
        else:
            target["link_check"] = {
                "state": "conflicting_evidence",
                "checked_on": obs["checked_on"], "evidence_url": obs["evidence_url"],
                "secondary_evidence_url": obs["secondary_evidence_url"],
                "note": "API 响应与其他来源不一致；人工复核前不删除、不判定失效。",
            }
    for row in items:
        status_counts[row["link_health"]] += 1
    return {
        "checked_on": health.get("reviewed_on"),
        "counts": status_counts,
        "scope": health["scope"],
        "migrations": health["migrations"],
        "limitations": health["known_limits"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline catalogue health and ambiguous identity audit")
    parser.add_argument("action", choices=["validate", "summary", "duplicates", "needs-review"])
    args = parser.parse_args(argv)
    try:
        from nb_catalog import catalogue
        data = catalogue()
        health = data["health_summary"]
        review = data["identity_review"]
        if args.action == "validate":
            output = {
                "valid": True, "total_items": len(data["items"]),
                "link_health": health["counts"],
                "shared_destination_groups": len(review["shared_destinations"]),
                "name_alias_groups": len(review["same_name_different_destinations"]),
                "verified_migrations": len(health["migrations"]),
            }
        elif args.action == "summary":
            output = health
        elif args.action == "duplicates":
            output = review
        else:
            output = [{"id": r["id"], "name": r["name"],
                       "url": r["url"], "link_check": r["link_check"]}
                      for r in data["items"] if r["link_health"] == "conflicting_evidence"]
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except (HealthError, OSError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
