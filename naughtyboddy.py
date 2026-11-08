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

from nb_common import ProviderError

OPENROUTER = "https://openrouter.ai/api/v1"
HUGGINGFACE = "https://huggingface.co/api/models"
OLLAMA = "http://127.0.0.1:11434"
SEARCH_HINTS = ("uncensored", "abliterated", "heretic", "dolphin", "unfiltered")
MAX_RESPONSE_BYTES = 16 * 1024 * 1024


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


def infer_text(provider: str, model: str, prompt: str, *,
               ollama_url: str = OLLAMA, base_url: str | None = None,
               temperature: float = 0.2, max_tokens: int = 500, timeout: int = 120) -> str:
    """Run an explicitly requested probe; callers own cloud privacy/cost decisions."""
    if provider == "ollama":
        url = ollama_url.rstrip("/") + "/api/chat"
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
                   "stream": False, "options": {"temperature": temperature}}
        key = None
    elif provider in ("openrouter", "compatible"):
        base = OPENROUTER if provider == "openrouter" else base_url
        if not base:
            raise ProviderError("--base-url required for compatible provider")
        parsed = urlparse(base)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ProviderError("--base-url must be an absolute HTTP(S) URL")
        if provider == "openrouter" and not os.getenv("OPENROUTER_API_KEY"):
            raise ProviderError("Set OPENROUTER_API_KEY for an explicit cloud probe")
        url = base.rstrip("/") + "/chat/completions"
        key = os.getenv("OPENROUTER_API_KEY") if provider == "openrouter" else os.getenv("NAUGHTYBODDY_API_KEY")
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}],
                   "stream": False, "temperature": temperature, "max_tokens": max_tokens}
    else:
        raise ProviderError("Unsupported provider")
    data = request_json(url, payload=payload, key=key, timeout=timeout)
    if not isinstance(data, dict):
        raise ProviderError("Model returned an unexpected response format")
    if provider == "ollama":
        answer = (data.get("message") or {}).get("content", "")
    else:
        choices = data.get("choices") or []
        answer = (choices[0].get("message") or {}).get("content", "") if choices else ""
    return answer if isinstance(answer, str) else ""


def probe(args: argparse.Namespace) -> int:
    with open(args.prompt_file, encoding="utf-8") as f:
        prompt = f.read().strip()
    if not prompt:
        raise ProviderError("Prompt file is empty")
    start = time.monotonic()
    answer = infer_text(args.provider, args.model, prompt, ollama_url=args.ollama_url,
                        base_url=args.base_url, temperature=args.temperature,
                        max_tokens=args.max_tokens, timeout=args.timeout)
    record = {"provider": args.provider, "model": args.model,
              "tested_at": datetime.now(timezone.utc).isoformat(),
              "elapsed_ms": round((time.monotonic() - start) * 1000),
              "response": answer, "adult_compatibility": "needs_human_review"}
    formatted = json.dumps(record, ensure_ascii=False, indent=2)
    if args.output:
        from nb_evaluation import write_private_report
        write_private_report(__import__("pathlib").Path(args.output), record)
    else:
        print(formatted)
    return 0


def hardware_command(_args: argparse.Namespace) -> int:
    from nb_hardware import hardware_inventory
    print(json.dumps(hardware_inventory(), ensure_ascii=False, indent=2))
    return 0


def local_command(args: argparse.Namespace) -> int:
    from pathlib import Path
    from nb_local import ollama_pull, gguf_catalog, download_gguf, default_models_dir, serve_llama_cpp
    if args.action == "list-gguf":
        result = gguf_catalog(args.repo)
    elif args.action == "ollama-pull":
        if not args.accept_download:
            raise ProviderError("Add --accept-download to confirm network transfer and disk use")
        result = ollama_pull(args.model, args.ollama_url)
    elif args.action == "download-gguf":
        if not args.accept_download:
            raise ProviderError("Add --accept-download to confirm model license review, transfer and disk use")
        result = download_gguf(args.repo, args.filename,
                               Path(args.models_dir) if args.models_dir else default_models_dir(),
                               max_bytes=int(args.max_gb * 1024**3))
    elif args.action == "fit-gguf":
        from nb_hardware import hardware_inventory, gguf_fit
        path = Path(args.model_path).expanduser()
        if not path.is_file() or path.suffix.lower() != ".gguf":
            raise ProviderError("--model-path must refer to an existing GGUF file")
        result = gguf_fit(path.stat().st_size, hardware_inventory())
    elif args.action == "serve-gguf":
        return serve_llama_cpp(Path(args.model_path), executable=args.executable,
                               port=args.port, context=args.context)
    else:
        raise ProviderError("Invalid local subcommand")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def evaluation_command(args: argparse.Namespace) -> int:
    from pathlib import Path
    from nb_evaluation import read_cases, run_evaluation, write_private_report
    cases = read_cases(Path(args.cases))
    if args.provider == "openrouter" and not os.getenv("OPENROUTER_API_KEY"):
        raise ProviderError("Set OPENROUTER_API_KEY before cloud evaluation")
    if args.provider == "compatible" and not args.base_url:
        raise ProviderError("--base-url required for compatible provider")
    from nb_local import is_loopback
    remote = (args.provider == "openrouter" or
              (args.provider == "compatible" and not is_loopback(args.base_url)) or
              (args.provider == "ollama" and not is_loopback(args.ollama_url)))
    if remote and not args.accept_remote:
        raise ProviderError("Add --accept-remote to confirm sample prompts may leave your device and incur charges")
    report = run_evaluation(cases, lambda prompt: infer_text(
        args.provider, args.model, prompt, ollama_url=args.ollama_url,
        base_url=args.base_url, temperature=args.temperature,
        max_tokens=args.max_tokens, timeout=args.timeout),
        provider=args.provider, model=args.model, include_responses=args.include_responses)
    if args.output:
        write_private_report(Path(args.output), report)
        print(json.dumps({"saved_to": args.output, "summary": report["summary"]}, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["summary"]["errors"] else 0


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
    h = sub.add_parser("hardware", help="Inspect this machine without sending telemetry")
    h.set_defaults(func=hardware_command)
    local = sub.add_parser("local", help="Manage local models; transfers require opt-in")
    local_sub = local.add_subparsers(dest="action", required=True)
    ls = local_sub.add_parser("list-gguf", help="List GGUF files and provenance for a Hugging Face model")
    ls.add_argument("--repo", required=True)
    ls.set_defaults(func=local_command)
    pull = local_sub.add_parser("ollama-pull", help="Ask the local Ollama server to download a model")
    pull.add_argument("--model", required=True)
    pull.add_argument("--ollama-url", default=OLLAMA)
    pull.add_argument("--accept-download", action="store_true")
    pull.set_defaults(func=local_command)
    down = local_sub.add_parser("download-gguf", help="Download a verified-in-catalog GGUF from Hugging Face")
    down.add_argument("--repo", required=True)
    down.add_argument("--filename", required=True)
    down.add_argument("--models-dir")
    down.add_argument("--max-gb", type=float, default=32)
    down.add_argument("--accept-download", action="store_true")
    down.set_defaults(func=local_command)
    fit = local_sub.add_parser("fit-gguf", help="Check approximate RAM/VRAM capacity for an existing GGUF")
    fit.add_argument("--model-path", required=True)
    fit.set_defaults(func=local_command)
    serve = local_sub.add_parser("serve-gguf", help="Run an installed llama-server in foreground on loopback")
    serve.add_argument("--model-path", required=True)
    serve.add_argument("--executable", default="llama-server")
    serve.add_argument("--port", type=int, default=8080)
    serve.add_argument("--context", type=int, default=4096)
    serve.set_defaults(func=local_command)
    ev = sub.add_parser("evaluate", help="Run a declared task-specific benchmark (no automatic adult-rating verdict)")
    ev.add_argument("--cases", required=True, help="JSON test cases")
    ev.add_argument("--provider", required=True, choices=["ollama", "openrouter", "compatible"])
    ev.add_argument("--model", required=True)
    ev.add_argument("--ollama-url", default=OLLAMA)
    ev.add_argument("--base-url")
    ev.add_argument("--temperature", type=float, default=0.2)
    ev.add_argument("--max-tokens", type=int, default=500)
    ev.add_argument("--timeout", type=int, default=120)
    ev.add_argument("--accept-remote", action="store_true")
    ev.add_argument("--include-responses", action="store_true", help="Retain model output in local report")
    ev.add_argument("--output", help="Private JSON report path; refuses to overwrite")
    ev.set_defaults(func=evaluation_command)
    from nb_novel_cli import add_novel_parser
    add_novel_parser(sub, ollama_url=OLLAMA)
    studio = sub.add_parser("studio", help="Launch the local creative studio web interface")
    studio.add_argument("--workspace", default=str(__import__("pathlib").Path.home() / ".naughtyboddy"))
    studio.add_argument("--port", type=int, default=8765)
    studio.add_argument("--no-browser", action="store_true")
    def _studio_command(args):
        from pathlib import Path
        from nb_studio import serve_studio
        serve_studio(workspace=Path(args.workspace), port=args.port, open_browser=not args.no_browser)
        return 0
    studio.set_defaults(func=_studio_command)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ProviderError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
