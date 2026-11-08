"""Novel workflow command handlers; no network calls without explicit translate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from nb_common import ProviderError
from nb_local import is_loopback
from nb_novel import init_project, project_status, run_translation, audit_project, export_project


def novel_command(args: argparse.Namespace) -> int:
    from naughtyboddy import infer_text
    project = Path(args.project)
    if args.action == "init":
        result = init_project(Path(args.input), project, chunk_chars=args.chunk_chars,
                              target_language=args.target_language,
                              glossary_path=Path(args.glossary) if args.glossary else None)
    elif args.action == "status":
        result = project_status(project)
    elif args.action == "audit":
        result = audit_project(project)
    elif args.action == "export":
        result = export_project(project, Path(args.output), allow_demo=args.allow_demo)
    elif args.action == "translate":
        if args.provider != "mock" and not args.model:
            raise ProviderError("--model is required for a real inference provider")
        if args.provider == "compatible" and not args.base_url:
            raise ProviderError("--base-url is required for a compatible provider")
        remote = (args.provider == "openrouter" or
                  (args.provider == "compatible" and not is_loopback(args.base_url)) or
                  (args.provider == "ollama" and not is_loopback(args.ollama_url)))
        if remote and not args.accept_remote:
            raise ProviderError("Add --accept-remote to send book excerpts to a remote provider; charges may apply")
        if args.provider == "mock":
            inference = None
        else:
            inference = lambda prompt: infer_text(
                args.provider, args.model, prompt, ollama_url=args.ollama_url,
                base_url=args.base_url, temperature=args.temperature,
                max_tokens=args.max_tokens, timeout=args.timeout)
        result = run_translation(project, provider=args.provider, model=args.model or "demo",
                                 max_segments=args.max_segments, inference=inference)
    else:
        raise ProviderError("Unsupported novel action")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.action == "translate" and result["errors"]:
        return 1
    return 0


def add_novel_parser(sub: argparse._SubParsersAction, *, ollama_url: str) -> None:
    root = sub.add_parser("novel", help="Checkpointed local-first TXT/EPUB novel translation")
    actions = root.add_subparsers(dest="action", required=True)
    init = actions.add_parser("init", help="Parse a book into a private local project; no model calls")
    init.add_argument("--input", required=True, help="UTF-8 TXT or DRM-free EPUB you may process")
    init.add_argument("--project", required=True, help="New project folder (must not exist)")
    init.add_argument("--target-language", default="zh-CN")
    init.add_argument("--glossary", help="Optional JSON source-term -> target-term dictionary")
    init.add_argument("--chunk-chars", type=int, default=1500)
    init.set_defaults(func=novel_command)

    status = actions.add_parser("status", help="Show project progress without calling a model")
    status.add_argument("--project", required=True)
    status.set_defaults(func=novel_command)

    tr = actions.add_parser("translate", help="Translate a bounded number of pending segments")
    tr.add_argument("--project", required=True)
    tr.add_argument("--provider", choices=["mock", "ollama", "compatible", "openrouter"], required=True)
    tr.add_argument("--model", help="Model ID (required except for mock)")
    tr.add_argument("--ollama-url", default=ollama_url)
    tr.add_argument("--base-url", help="For llama.cpp, KoboldCpp, or compatible API, include /v1")
    tr.add_argument("--max-segments", type=int, default=20,
                    help="Maximum inference calls this run, default 20; no automatic retries")
    tr.add_argument("--temperature", type=float, default=0.2)
    tr.add_argument("--max-tokens", type=int, default=2500)
    tr.add_argument("--timeout", type=int, default=180)
    tr.add_argument("--accept-remote", action="store_true",
                    help="Explicit consent to send book excerpts off-device; costs may apply")
    tr.set_defaults(func=novel_command)

    audit = actions.add_parser("audit", help="Detect incomplete and heuristic translation issues")
    audit.add_argument("--project", required=True)
    audit.set_defaults(func=novel_command)

    exp = actions.add_parser("export", help="Export completed book to UTF-8 TXT or text-layout EPUB")
    exp.add_argument("--project", required=True)
    exp.add_argument("--output", required=True)
    exp.add_argument("--allow-demo", action="store_true",
                     help="Explicitly export a prominently marked mock untranslated demonstration")
    exp.set_defaults(func=novel_command)
