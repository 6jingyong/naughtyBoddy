"""Opt-in local inference model operations (Ollama and GGUF/llama-server)."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from typing import Callable
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from nb_common import ProviderError
from naughtyboddy import request_json, OLLAMA

MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$")
MAX_MODEL_BYTES_DEFAULT = 32 * 1024**3


def is_loopback(url: str) -> bool:
    p = urlparse(url)
    return p.scheme == "http" and p.hostname in ("localhost", "127.0.0.1", "::1") and not p.username


def ollama_pull(model: str, base_url: str = OLLAMA) -> dict:
    if not is_loopback(base_url):
        raise ProviderError("Model installation requires a loopback Ollama URL")
    if not model.strip() or any(c.isspace() for c in model):
        raise ProviderError("Provide a valid Ollama model name")
    result = request_json(base_url.rstrip("/") + "/api/pull", payload={"model": model, "stream": False}, timeout=3600)
    if not isinstance(result, dict) or result.get("status") != "success":
        raise ProviderError(f"Ollama did not confirm download completion: {result}")
    return {"provider": "ollama", "model": model, "status": "installed"}


def hf_model_info(repo: str) -> dict:
    if not MODEL_RE.fullmatch(repo):
        raise ProviderError("Hugging Face repository must be owner/model")
    key = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    url = "https://huggingface.co/api/models/" + quote(repo, safe="/")
    info = request_json(url, key=key)
    if not isinstance(info, dict) or not info.get("id"):
        raise ProviderError("Invalid model metadata from Hugging Face")
    return info


def gguf_catalog(repo: str) -> dict:
    info = hf_model_info(repo)
    siblings = info.get("siblings") or []
    files = []
    for entry in siblings:
        name = entry.get("rfilename", "")
        if valid_gguf_name(name):
            files.append({"filename": name, "size_bytes": entry.get("size")})
    card = info.get("cardData") or {}
    return {"repo": info["id"], "revision": info.get("sha"), "license": card.get("license"),
            "gated": info.get("gated", False), "private": info.get("private", False),
            "files": files, "license_note": "Review the model card and upstream license before download/use."}


def valid_gguf_name(name: str) -> bool:
    if not isinstance(name, str) or not name.lower().endswith(".gguf"):
        return False
    parts = name.split("/")
    return all(part not in ("", ".", "..") and "\\" not in part and ":" not in part for part in parts)


def default_models_dir() -> Path:
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
    elif sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support"
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))
    return root / "NaughtyBoddy" / "models"


def download_gguf(repo: str, filename: str, destination: Path, *,
                  revision: str | None = None, max_bytes: int = MAX_MODEL_BYTES_DEFAULT,
                  on_progress: Callable[[int], None] | None = None) -> dict:
    """Download a selected GGUF from a validated HF repo, with resumable .part files.

    Caller must explicitly opt into transfer. Do not auto-install model dependencies or execute downloaded files.
    """
    if not MODEL_RE.fullmatch(repo) or not valid_gguf_name(filename):
        raise ProviderError("Invalid Hugging Face repo or GGUF filename")
    catalog = gguf_catalog(repo)
    if catalog["gated"] or catalog["private"]:
        raise ProviderError("Gated/private model requires separate access handling; download declined")
    available = {file["filename"] for file in catalog["files"]}
    if filename not in available:
        raise ProviderError("Requested GGUF was not found in model repository metadata")
    if max_bytes <= 0:
        raise ProviderError("--max-gb must be positive")
    # Pin to the current repository revision for reproducibility; user may explicitly provide a commit hash.
    pinned = revision or catalog["revision"]
    if not pinned or not re.fullmatch(r"[0-9a-fA-F]{40}", pinned):
        raise ProviderError("Repository lacks a stable revision; refusing unpinned download")
    target_dir = destination.expanduser().resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    # Nested model filenames flatten safely to basename; separate repo subdirectory prevents collisions.
    target = target_dir / repo.replace("/", "--") / Path(*filename.split("/"))
    target.parent.mkdir(parents=True, exist_ok=True)
    part = target.with_name(target.name + ".part")
    if any(parent.is_symlink() for parent in target.parents if parent != target_dir.parent):
        raise ProviderError("Refusing to write through symlinked model directories")
    if target.is_symlink():
        raise ProviderError("Refusing symlinked model destination")
    if target.exists():
        raise ProviderError(f"Destination already exists: {target}")
    downloaded = part.stat().st_size if part.exists() else 0
    part_meta = part.with_name(part.name + ".json")
    if part.is_symlink() or part_meta.is_symlink():
        raise ProviderError("Refusing symlinked partial download files")
    expected_meta = {"repo": repo, "revision": pinned, "filename": filename}
    if part.exists():
        try:
            previous_meta = json.loads(part_meta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise ProviderError("Partial file has no valid revision metadata; remove .part before retrying")
        if previous_meta != expected_meta:
            raise ProviderError("Partial file belongs to another model revision; remove .part before retrying")
    else:
        part_meta.write_text(json.dumps(expected_meta), encoding="utf-8")
    if downloaded > max_bytes:
        raise ProviderError("Existing partial file exceeds the allowed size")
    if on_progress:
        on_progress(downloaded)
    hf_path = "/".join(quote(segment, safe="") for segment in filename.split("/"))
    url = f"https://huggingface.co/{quote(repo, safe='/')}/resolve/{pinned}/{hf_path}"
    headers = {"User-Agent": "NaughtyBoddy/0.1"}
    # Public files do not require a token. Do not forward HF credentials to redirect/CDN hosts.
    if downloaded:
        headers["Range"] = f"bytes={downloaded}-"
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=60) as response:
            status = getattr(response, "status", None)
            if status is None:
                status = response.getcode()
            if downloaded and status != 206:
                # Server ignored Range; avoid appending a duplicate file.
                downloaded = 0
            if status == 206:
                content_range = response.headers.get("Content-Range", "")
                if not content_range.startswith(f"bytes {downloaded}-"):
                    raise ProviderError("Unexpected resume range from download server")
            content_length = response.headers.get("Content-Length")
            if content_length and downloaded + int(content_length) > max_bytes:
                raise ProviderError("Download exceeds maximum allowed size")
            mode = "ab" if downloaded else "wb"
            count = downloaded
            with part.open(mode) as f:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    count += len(chunk)
                    if count > max_bytes:
                        raise ProviderError("Download exceeds maximum allowed size")
                    f.write(chunk)
                    if on_progress:
                        on_progress(count)
            if content_length and count - downloaded != int(content_length):
                raise ProviderError("Incomplete download; .part retained for retry")
    except HTTPError as exc:
        raise ProviderError(f"Hugging Face download HTTP {exc.code}; partial data retained") from exc
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        raise ProviderError(f"GGUF download failed; partial data retained: {exc}") from exc
    if part.stat().st_size == 0:
        raise ProviderError("Downloaded file was empty")
    part.replace(target)
    part_meta.unlink(missing_ok=True)
    return {"repo": repo, "filename": filename, "revision": pinned,
            "path": str(target), "size_bytes": target.stat().st_size, "status": "downloaded",
            "note": "Model not executed; review license and provenance before inference."}


def serve_llama_cpp(model_path: Path, *, executable: str = "llama-server", port: int = 8080,
                    context: int = 4096, extra_args: list[str] | None = None) -> int:
    path = model_path.expanduser().resolve(strict=True)
    if not path.is_file() or path.suffix.lower() != ".gguf":
        raise ProviderError("--model-path must be an existing GGUF file")
    if not 1024 <= port <= 65535 or not 512 <= context <= 131072:
        raise ProviderError("Invalid port or context size")
    args = [executable, "--model", str(path), "--host", "127.0.0.1", "--port", str(port),
            "--ctx-size", str(context)]
    if extra_args:
        args.extend(extra_args)
    try:
        # Foreground process, no shell or automatic privileges; Ctrl+C stops it.
        return subprocess.call(args)
    except FileNotFoundError as exc:
        raise ProviderError(f"Inference backend not found: {executable}") from exc
    except KeyboardInterrupt:
        return 130
