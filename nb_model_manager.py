"""Local-first model lifecycle for Studio P3.1.

Only vetted, fixed operations: model metadata, confirmed downloads, managed GGUF
launch, and a small explicit test suite. No arbitrary shell or client file paths.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import threading
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from nb_common import ProviderError
from nb_hardware import hardware_inventory, gguf_fit
from nb_local import (MODEL_RE, valid_gguf_name, gguf_catalog, download_gguf,
                      ollama_pull, is_loopback)
from nb_evaluation import read_cases, run_evaluation, write_private_report

MAX_JOBS = 50
MAX_GGUF_GIB = 32
MANAGED_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*--[A-Za-z0-9][A-Za-z0-9_.-]*\Z")


def managed_models(root: Path, inventory: dict | None = None) -> list[dict]:
    """List only ordinary GGUF files contained under this workspace's model directory."""
    if not root.is_dir() or root.is_symlink():
        return []
    inventory = inventory if inventory is not None else hardware_inventory()
    result = []
    for repo_dir in sorted(root.iterdir()):
        if repo_dir.is_symlink() or not repo_dir.is_dir() or not MANAGED_NAME.fullmatch(repo_dir.name):
            continue
        # Never follow symlinked folders or files provided by untrusted content.
        for path in repo_dir.rglob("*.gguf"):
            if path.is_symlink() or not path.is_file() or any(p.is_symlink() for p in path.parents if p != root.parent):
                continue
            try:
                name = path.relative_to(root).as_posix()
                size = path.stat().st_size
                if size <= 0:
                    continue
                result.append({"name": name, "size_bytes": size, "fit": gguf_fit(size, inventory)})
            except (OSError, ValueError):
                continue
            if len(result) >= 200:
                return result
    return result


class ModelManager:
    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()
        self.root = self.workspace / "models"
        self.root.mkdir(parents=True, exist_ok=True)
        self.evaluations = self.workspace / "private" / "evaluations"
        self._lock = threading.RLock()
        self._jobs: dict[str, dict] = {}
        self._process: subprocess.Popen | None = None
        self._managed_name: str | None = None
        self._port: int | None = None
        if os.name != "nt":
            self.root.chmod(0o700)

    def status(self) -> dict:
        from naughtyboddy import discover_ollama
        hardware = hardware_inventory()
        try:
            ollama = {"available": True, "models": discover_ollama()}
        except (ProviderError, OSError) as exc:
            ollama = {"available": False, "models": [], "error": type(exc).__name__}
        return {"hardware": hardware, "ollama": ollama,
                "gguf": managed_models(self.root, hardware), "engine": self.engine_status()}

    def catalog(self, repo: str) -> dict:
        if not isinstance(repo, str) or not MODEL_RE.fullmatch(repo):
            raise ProviderError("Hugging Face model must be owner/repository")
        result = gguf_catalog(repo)
        hardware = hardware_inventory()
        for row in result["files"]:
            size = row.get("size_bytes")
            row["fit"] = gguf_fit(size, hardware) if isinstance(size, int) and size > 0 else None
        return result

    def _create_job(self, kind: str, description: str, worker):
        with self._lock:
            if any(j["state"] in ("queued", "running") for j in self._jobs.values()):
                raise ProviderError("Wait for the current model operation to finish")
            if len(self._jobs) >= MAX_JOBS:
                for key in list(self._jobs):
                    if self._jobs[key]["state"] in ("done", "failed"):
                        del self._jobs[key]
                        break
                if len(self._jobs) >= MAX_JOBS:
                    raise ProviderError("Too many queued model operations")
            jid = uuid.uuid4().hex
            self._jobs[jid] = {"id": jid, "kind": kind, "label": description,
                               "state": "queued", "progress_bytes": 0,
                               "result": None, "error": None}

        def task():
            with self._lock:
                self._jobs[jid]["state"] = "running"
            try:
                result = worker(jid)
                with self._lock:
                    self._jobs[jid].update(state="done", result=result)
            except Exception as exc:
                with self._lock:
                    # Do not leak third-party request contents or credentials in errors.
                    self._jobs[jid].update(state="failed", error=f"{type(exc).__name__}: {str(exc)[:300]}")
        threading.Thread(target=task, daemon=True, name=f"nb-model-{jid[:8]}").start()
        return {"job_id": jid, "state": "queued"}

    def job(self, jid: str) -> dict:
        with self._lock:
            if jid not in self._jobs:
                raise ProviderError("Model job not found")
            return dict(self._jobs[jid])

    def install(self, data: dict) -> dict:
        if data.get("confirm_download") is not True:
            raise ProviderError("Explicitly confirm the model download and disk usage")
        kind = data.get("kind")
        if kind == "ollama":
            model = data.get("model")
            if not isinstance(model, str) or not re.fullmatch(r"[A-Za-z0-9_./:-]{1,180}", model):
                raise ProviderError("Invalid Ollama model name")
            return self._create_job("ollama_pull", model,
                                    lambda jid: ollama_pull(model))
        if kind == "gguf":
            if data.get("license_reviewed") is not True:
                raise ProviderError("Review the model card/license before download")
            repo, filename = data.get("repo"), data.get("filename")
            if not isinstance(repo, str) or not MODEL_RE.fullmatch(repo) or not valid_gguf_name(filename):
                raise ProviderError("Choose a valid Hugging Face repo and GGUF file")
            revision = data.get("revision")
            if revision is not None and (not isinstance(revision, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", revision)):
                raise ProviderError("Revision must be a 40-character commit hash")
            try:
                max_gb = int(data.get("max_gb", 8))
            except (ValueError, TypeError) as exc:
                raise ProviderError("Invalid download size limit") from exc
            if not 1 <= max_gb <= MAX_GGUF_GIB:
                raise ProviderError("Download limit must be between 1 and 32 GiB")
            def task(jid):
                def progress(n: int):
                    with self._lock:
                        self._jobs[jid]["progress_bytes"] = n
                return download_gguf(repo, filename, self.root, revision=revision,
                                     max_bytes=max_gb * 1024**3, on_progress=progress)
            return self._create_job("gguf_download", f"{repo}/{filename}", task)
        raise ProviderError("Unknown model installation kind")

    def _managed_path(self, name: str) -> Path:
        if not isinstance(name, str) or len(name) > 250 or not valid_gguf_name(name):
            raise ProviderError("Select a managed GGUF model")
        if name not in {row["name"] for row in managed_models(self.root, {"gpus": [], "system_ram_bytes": None})}:
            raise ProviderError("Model not found in managed GGUF inventory")
        path = self.root.joinpath(*name.split("/"))
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(self.root.resolve()):
            raise ProviderError("Model path is not a managed file")
        return path

    def engine_status(self) -> dict:
        with self._lock:
            if self._process is None:
                return {"state": "stopped", "llama_server_available": bool(shutil.which("llama-server"))}
            exitcode = self._process.poll()
            if exitcode is not None:
                self._process = None
                self._managed_name = None
                self._port = None
                return {"state": "stopped", "last_exit_code": exitcode,
                        "llama_server_available": bool(shutil.which("llama-server"))}
            ready = False
            try:
                with urlopen(f"http://127.0.0.1:{self._port}/health", timeout=0.5) as response:
                    ready = response.status == 200
            except (HTTPError, URLError, TimeoutError, OSError):
                pass
            return {"state": "ready" if ready else "starting", "name": self._managed_name, "port": self._port,
                    "base_url": f"http://127.0.0.1:{self._port}/v1", "health_checked": True,
                    "llama_server_available": True,
                    "note": "Health endpoint only; actual generation quality is not verified."}

    def launch(self, data: dict) -> dict:
        if data.get("confirm_launch") is not True:
            raise ProviderError("Confirm launching the selected local model")
        path = self._managed_path(data.get("name"))
        try:
            port = int(data.get("port", 8080))
            context = int(data.get("context", 4096))
        except (ValueError, TypeError) as exc:
            raise ProviderError("Invalid port or context") from exc
        if not 1024 <= port <= 65535 or not 512 <= context <= 131072:
            raise ProviderError("Port/context out of allowed range")
        binary = shutil.which("llama-server")
        if not binary:
            raise ProviderError("llama-server not installed or not on PATH")
        with self._lock:
            if self._process is not None and self._process.poll() is None:
                raise ProviderError("Stop the existing managed server first")
            with socket.socket() as sock:
                try:
                    sock.bind(("127.0.0.1", port))
                except OSError as exc:
                    raise ProviderError("Chosen local port is already in use") from exc
            logs = self.workspace / "private"
            logs.mkdir(parents=True, exist_ok=True)
            log_path = logs / "llama-server.log"
            with log_path.open("ab") as out:
                # Fixed executable + fixed flags; no shell, no caller-defined executable.
                proc = subprocess.Popen([binary, "--model", str(path), "--host", "127.0.0.1",
                                         "--port", str(port), "--ctx-size", str(context)],
                                        stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT)
            self._process, self._managed_name, self._port = proc, data["name"], port
        return self.engine_status()

    def stop(self) -> dict:
        with self._lock:
            proc = self._process
            self._process = None
            self._managed_name = None
            self._port = None
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        return {"state": "stopped"}

    def evaluate(self, data: dict) -> dict:
        provider, model = data.get("provider"), data.get("model")
        if provider not in ("ollama", "compatible", "openrouter"):
            raise ProviderError("Choose an inference provider")
        if not isinstance(model, str) or not 1 <= len(model) <= 220:
            raise ProviderError("Choose a valid model ID")
        base = data.get("base_url", "")
        if provider == "compatible" and (not isinstance(base, str) or not base.startswith(("http://", "https://"))):
            raise ProviderError("Valid compatible API URL is required")
        if provider == "openrouter" and not os.getenv("OPENROUTER_API_KEY"):
            raise ProviderError("OPENROUTER_API_KEY is required")
        if provider == "compatible" and not is_loopback(base) and data.get("accept_remote") is not True:
            raise ProviderError("Explicitly approve remote API evaluation")
        if provider == "openrouter" and data.get("accept_remote") is not True:
            raise ProviderError("Explicitly approve paid or remote evaluation")
        cases_path = Path(__file__).resolve().parent / "examples" / "translation_eval.json"
        cases = read_cases(cases_path)
        def task(jid):
            from naughtyboddy import infer_text
            report = run_evaluation(cases, lambda prompt: infer_text(
                provider, model, prompt, base_url=base or None, timeout=90,
                max_tokens=512), provider=provider, model=model, include_responses=False)
            self.evaluations.mkdir(parents=True, exist_ok=True)
            path = self.evaluations / f"{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex}.json"
            write_private_report(path, report)
            return {"report_id": path.name, "summary": report["summary"],
                    "interpretation": report["interpretation"]}
        return self._create_job("evaluation", f"{provider} · {model}", task)

    def reports(self) -> list[dict]:
        if not self.evaluations.is_dir():
            return []
        records = []
        for path in sorted(self.evaluations.glob("*.json"), reverse=True)[:30]:
            if path.is_symlink():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                records.append({"id": path.name, "timestamp": data.get("timestamp"),
                                "provider": data.get("provider"), "model": data.get("model"),
                                "summary": data.get("summary"),
                                "assessment": "heuristic_only_manual_review_pending"})
            except (OSError, ValueError):
                continue
        return records
