"""NaughtyBoddy discovery and inference smoke-test CLI (standard library only)."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

OPENROUTER = "https://openrouter.ai/api/v1"
HUGGINGFACE = "https://huggingface.co/api/models"
OLLAMA = "http://127.0.0.1:11434"
SEARCH_HINTS = ("uncensored", "abliterated", "heretic", "dolphin", "unfiltered")
MAX_RESPONSE_BYTES = 16 * 1024 * 1024


class ProviderError(Exception):
    pass


def request_json(url: str, *, payload: dict | None = None, key: str | None = None, timeout: int = 15) -> dict | list:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if key:
        headers["Authorization"] = f"Bearer {key}"
    req = Request(url, data=data, headers=headers, method="POST" if data is not None else "GET")
    try:
        with urlopen(req, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ProviderError("Response exceeds the size limit")
        return json.loads(raw)
    except HTTPError as exc:
        raise ProviderError(f"HTTP {exc.code} from {urlparse(url).netloc}") from exc
    except (URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        raise ProviderError(f"Could not request {urlparse(url).netloc}: {exc}") from exc


def hints_for(*values: object) -> list[str]:
    haystack = " ".join(str(v).lower() for v in values if v is not None)
    return [word for word in SEARCH_HINTS if word in haystack]


def discover_ollama(url: str = OLLAMA) -> list[dict]:
    data = request_json(url.rstrip("/") + "/api/tags")
    return [
        {"source": "ollama", "id": row.get("name") or row.get("model"),
         "local": True, "parameter_size": row.get("details", {}).get("parameter_size"),
         "quantization": row.get("details", {}).get("quantization_level"),
         "size_bytes": row.get("size"),
         "low_refusal_hints": hints_for(row.get("name"), row.get("model")),
         "adult_compatibility": "untested"}
        for row in data.get("models", []) if row.get("name") or row.get("model")
    ]


def discover_openrouter() -> list[dict]:
    data = request_json(OPENROUTER + "/models")
    result = []
    for row in data.get("data", []):
        pricing = row.get("pricing") or {}
        result.append({"source": "openrouter", "id": row.get("id"), "local": False,
                       "context_length": row.get("context_length"),
                       "modalities": (row.get("architecture") or {}).get("input_modalities", []),
                       "supported_parameters": row.get("supported_parameters") or [],
                       "pricing_usd_per_token": {k: pricing.get(k) for k in ("prompt", "completion")},
                       "low_refusal_hints": hints_for(row.get("id"), row.get("name"), row.get("description")),
                       "adult_compatibility": "untested"})
    return result


def discover_huggingface(query: str = "abliterated", limit: int = 30) -> list[dict]:
    qs = urlencode({"search": query, "limit": limit, "sort": "lastModified", "direction": -1})
    data = request_json(HUGGINGFACE + "?" + qs)
    return [{"source": "huggingface", "id": row.get("id"), "local": None,
             "downloads": row.get("downloads"), "likes": row.get("likes"),
             "last_modified": row.get("lastModified"),
             "low_refusal_hints": hints_for(row.get("id"), row.get("tags")),
             "adult_compatibility": "untested"}
            for row in data if row.get("id")]


def discover(args: argparse.Namespace) -> int:
    providers = ["ollama", "openrouter", "huggingface"] if args.source == "all" else [args.source]
    output = {"models": [], "errors": {}}
    for provider in providers:
        try:
            if provider == "ollama":
                models = discover_ollama(args.ollama_url)
            elif provider == "openrouter":
                models = discover_openrouter()
            else:
                models = discover_huggingface(args.query or "abliterated", args.limit)
            if args.query:
                models = [x for x in models if args.query.lower() in x["id"].lower()]
            output["models"].extend(models[:args.limit])
        except ProviderError as exc:
            output["errors"][provider] = str(exc)
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 1 if not output["models"] and output["errors"] else 0


def probe(args: argparse.Namespace) -> int:
    with open(args.prompt_file, encoding="utf-8") as f:
        prompt = f.read().strip()
    if not prompt:
        raise ProviderError("Prompt file is empty")
    if args.provider == "ollama":
        url = args.ollama_url.rstrip("/") + "/api/chat"
        payload = {"model": args.model, "messages": [{"role": "user", "content": prompt}],
                   "stream": False, "options": {"temperature": args.temperature}}
        key = None
    else:
        base = OPENROUTER if args.provider == "openrouter" else args.base_url
        if not base:
            raise ProviderError("--base-url required for compatible provider")
        parsed = urlparse(base)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ProviderError("--base-url must be an absolute HTTP(S) URL")
        if args.provider == "openrouter" and not os.getenv("OPENROUTER_API_KEY"):
            raise ProviderError("Set OPENROUTER_API_KEY for an explicit cloud probe")
        url = base.rstrip("/") + "/chat/completions"
        key = os.getenv("OPENROUTER_API_KEY") if args.provider == "openrouter" else os.getenv("NAUGHTYBODDY_API_KEY")
        payload = {"model": args.model, "messages": [{"role": "user", "content": prompt}],
                   "stream": False, "temperature": args.temperature, "max_tokens": args.max_tokens}
    start = time.monotonic()
    data = request_json(url, payload=payload, key=key, timeout=args.timeout)
    if args.provider == "ollama":
        answer = (data.get("message") or {}).get("content", "")
    else:
        choices = data.get("choices") or []
        answer = (choices[0].get("message") or {}).get("content", "") if choices else ""
    record = {"provider": args.provider, "model": args.model,
              "tested_at": datetime.now(timezone.utc).isoformat(),
              "elapsed_ms": round((time.monotonic() - start) * 1000),
              "response": answer, "adult_compatibility": "needs_human_review"}
    formatted = json.dumps(record, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(formatted + "\n")
    else:
        print(formatted)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NaughtyBoddy: discover and test models")
    sub = parser.add_subparsers(dest="command", required=True)
    d = sub.add_parser("discover", help="Read public model metadata and local Ollama inventory")
    d.add_argument("--source", choices=["all", "ollama", "openrouter", "huggingface"], default="all")
    d.add_argument("--query", default="", help="Filter by model ID (HF also searches remotely)")
    d.add_argument("--limit", type=int, default=20)
    d.add_argument("--ollama-url", default=OLLAMA)
    d.set_defaults(func=discover)
    p = sub.add_parser("probe", help="Send YOUR prompt to the specified model")
    p.add_argument("--provider", choices=["ollama", "openrouter", "compatible"], required=True)
    p.add_argument("--model", required=True)
    p.add_argument("--prompt-file", required=True)
    p.add_argument("--ollama-url", default=OLLAMA)
    p.add_argument("--base-url", help="OpenAI-compatible API root, e.g. http://127.0.0.1:8080/v1")
    p.add_argument("--timeout", type=int, default=120)
    p.add_argument("--max-tokens", type=int, default=500)
    p.add_argument("--temperature", type=float, default=0.2)
    p.add_argument("--output", help="Optional private local JSON file for the probe result")
    p.set_defaults(func=probe)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ProviderError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
