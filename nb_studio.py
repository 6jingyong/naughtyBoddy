"""NaughtyBoddy P3: local-only creative studio HTTP API, standard library only.

The browser talks exclusively to a loopback server. Local documents are never
sent to model providers during import, browsing, editing or discovery.
"""
from __future__ import annotations

import base64
import binascii
from contextlib import closing
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import tempfile
import threading
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from nb_common import ProviderError
from nb_local import is_loopback
from nb_model_manager import ModelManager
from nb_novel import _db, _load_glossary, init_project, project_status, audit_project, export_project, run_translation, now

MAX_UPLOAD = 12 * 1024 * 1024
MAX_JSON = 17 * 1024 * 1024
PROJECT_ID = re.compile(r"[0-9a-f]{32}\Z")
SEGMENT_ID = re.compile(r"c\d{4}-p\d{5}-s\d{3}-[a-f0-9]{8}\Z")
WEB_ROOT = Path(__file__).resolve().parent / "web"


class StudioService:
    def __init__(self, workspace: Path):
        self.workspace = workspace.expanduser().resolve()
        self.projects = self.workspace / "projects"
        self.projects.mkdir(parents=True, exist_ok=True)
        if os.name != "nt":
            self.workspace.chmod(0o700)
            self.projects.chmod(0o700)
        self.csrf_token = secrets.token_urlsafe(32)
        self.models = ModelManager(self.workspace)
        self._jobs: dict[str, dict] = {}
        self._jobs_lock = threading.Lock()

    def path(self, project_id: str) -> Path:
        if not PROJECT_ID.fullmatch(project_id):
            raise ProviderError("Invalid project ID")
        project = self.projects / project_id
        if project.is_symlink() or not project.is_dir() or not (project / "manifest.json").is_file():
            raise ProviderError("Project not found")
        return project

    def list_projects(self) -> list[dict]:
        result = []
        for child in self.projects.iterdir():
            if not PROJECT_ID.fullmatch(child.name) or child.is_symlink() or not child.is_dir():
                continue
            try:
                status = project_status(child)
                result.append({"id": child.name, **status})
            except (OSError, ValueError, KeyError, sqlite3.DatabaseError, ProviderError):
                continue
        return sorted(result, key=lambda x: x["id"], reverse=True)

    def import_book(self, data: dict) -> dict:
        if data.get("rights_confirmed") is not True:
            raise ProviderError("Confirm you have permission to process this book")
        filename = data.get("filename")
        if not isinstance(filename, str) or not (1 <= len(filename) <= 180) or any(c in filename for c in "/\\\0"):
            raise ProviderError("Invalid filename")
        suffix = Path(filename).suffix.lower()
        if suffix not in (".txt", ".epub"):
            raise ProviderError("Only TXT and EPUB are supported")
        encoded = data.get("base64")
        if not isinstance(encoded, str) or len(encoded) > (MAX_UPLOAD * 4 // 3 + 8):
            raise ProviderError("Upload exceeds size limit")
        try:
            raw = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ProviderError("Invalid base64 upload") from exc
        if not raw or len(raw) > MAX_UPLOAD:
            raise ProviderError("Upload must be between 1 byte and 12 MiB")
        language = data.get("target_language", "zh-CN")
        project_id = uuid.uuid4().hex
        temp = None
        try:
            with tempfile.NamedTemporaryFile(dir=self.workspace, prefix="upload-", suffix=suffix, delete=False) as f:
                f.write(raw)
                temp = Path(f.name)
            result = init_project(temp, self.projects / project_id, target_language=language)
            # Restore user-visible original filename. The temporary basename must not
            # become the source attribution of the imported work.
            manifest_path = self.projects / project_id / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["source_filename"] = filename
            manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
            return {"id": project_id, **result}
        finally:
            if temp:
                temp.unlink(missing_ok=True)

    def summary(self, project_id: str) -> dict:
        project = self.path(project_id)
        with _db(project) as db:
            chapters = [dict(row) for row in db.execute(
                "SELECT c.chapter_no,c.title,c.translated_title,COUNT(s.id) AS total,"
                "SUM(CASE WHEN s.target IS NOT NULL THEN 1 ELSE 0 END) AS done "
                "FROM chapters c LEFT JOIN segments s ON c.chapter_no=s.chapter_no "
                "GROUP BY c.chapter_no ORDER BY c.chapter_no")]
        return {"id": project_id, **project_status(project), "chapter_list": chapters}

    def segments(self, project_id: str, chapter_no: int, offset: int = 0, limit: int = 80) -> dict:
        if not (1 <= chapter_no <= 100000 and 0 <= offset <= 250000 and 1 <= limit <= 200):
            raise ProviderError("Invalid segment pagination")
        with _db(self.path(project_id)) as db:
            total = db.execute("SELECT COUNT(*) FROM segments WHERE chapter_no=?", (chapter_no,)).fetchone()[0]
            rows = [dict(row) for row in db.execute(
                "SELECT id,chapter_no,paragraph_no,chunk_no,source,target,provider,model,simulated,flags,updated_at "
                "FROM segments WHERE chapter_no=? ORDER BY paragraph_no,chunk_no LIMIT ? OFFSET ?",
                (chapter_no, limit, offset))]
        for row in rows:
            row["flags"] = json.loads(row["flags"])
        return {"chapter": chapter_no, "offset": offset, "total": total, "rows": rows,
                "has_more": offset + len(rows) < total}

    def edit_segment(self, project_id: str, segment_id: str, target: str) -> dict:
        if not SEGMENT_ID.fullmatch(segment_id):
            raise ProviderError("Invalid segment ID")
        if not isinstance(target, str) or len(target) > 20000:
            raise ProviderError("Translation must be text up to 20000 characters")
        project = self.path(project_id)
        if (project / ".translate.lock").exists():
            raise ProviderError("Wait until the current translation batch finishes before editing")
        new_target = target if target.strip() else None
        with _db(project) as db:
            db.execute("CREATE TABLE IF NOT EXISTS studio_edits ("
                       "id INTEGER PRIMARY KEY AUTOINCREMENT, segment_id TEXT NOT NULL,"
                       "old_target TEXT, new_target TEXT, edited_at TEXT NOT NULL)")
            row = db.execute("SELECT id, chapter_no, paragraph_no, target FROM segments WHERE id=?", (segment_id,)).fetchone()
            if not row:
                raise ProviderError("Segment not found")
            if row["target"] == new_target:
                return {"id": segment_id, "target": new_target, "changed": False}
            # Hold a write transaction across edit and title synchronization.
            with db:
                db.execute("INSERT INTO studio_edits (segment_id,old_target,new_target,edited_at) VALUES (?,?,?,?)",
                           (segment_id, row["target"], new_target, now()))
                db.execute("UPDATE segments SET target=?, provider=?, model=?, simulated=0, flags='[]',updated_at=? WHERE id=?",
                           (new_target, "manual" if new_target else None, "user" if new_target else None, now(), segment_id))
                if row["paragraph_no"] == 0:
                    db.execute("UPDATE chapters SET translated_title=? WHERE chapter_no=?", (new_target, row["chapter_no"]))
        return {"id": segment_id, "target": new_target, "changed": True}

    def get_glossary(self, project_id: str) -> dict:
        return {"terms": _load_glossary(self.path(project_id) / "glossary.json")}

    def save_glossary(self, project_id: str, terms: dict) -> dict:
        if (not isinstance(terms, dict) or len(terms) > 500 or
            not all(isinstance(k, str) and isinstance(v, str) and 0 < len(k) <= 200
                    and 0 < len(v) <= 200 for k, v in terms.items())):
            raise ProviderError("Glossary must contain up to 500 nonempty term pairs (max 200 characters each)")
        project = self.path(project_id)
        if (project / ".translate.lock").exists():
            raise ProviderError("Cannot change glossary while translation is running")
        encoded = json.dumps(terms, indent=2, ensure_ascii=False)
        fd, name = tempfile.mkstemp(prefix=".glossary-", suffix=".json", dir=project)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(encoded)
            if os.name != "nt":
                os.chmod(name, 0o600)
            os.replace(name, project / "glossary.json")
        finally:
            Path(name).unlink(missing_ok=True)
        return {"terms": terms, "count": len(terms)}

    def discover_models(self, source: str, query: str, limit: int) -> dict:
        import naughtyboddy as cli
        if source not in ("ollama", "huggingface", "openrouter"):
            raise ProviderError("Invalid discovery source")
        if not (1 <= limit <= 30) or len(query) > 120:
            raise ProviderError("Invalid model search")
        if source == "ollama":
            rows = cli.discover_ollama()
        elif source == "huggingface":
            rows = cli.discover_huggingface(query or "abliterated", limit)
        else:
            rows = cli.discover_openrouter()
        if query:
            rows = [row for row in rows if query.lower() in str(row.get("id", "")).lower()]
        return {"models": rows[:limit], "note": "Model names and tags are hints, not verified low-refusal scores."}

    def job_status(self, job_id: str) -> dict:
        with self._jobs_lock:
            job = self._jobs.get(job_id)
            if not job:
                raise ProviderError("Job not found")
            return dict(job)

    def start_translation(self, project_id: str, options: dict) -> dict:
        project = self.path(project_id)
        provider = options.get("provider")
        model = options.get("model", "")
        if provider not in ("mock", "ollama", "compatible", "openrouter"):
            raise ProviderError("Choose a valid model provider")
        if provider != "mock" and (not isinstance(model, str) or not model.strip() or len(model) > 220):
            raise ProviderError("Model ID is required")
        base_url = options.get("base_url", "")
        if provider == "compatible" and (not isinstance(base_url, str) or not base_url.startswith(("http://", "https://"))):
            raise ProviderError("Compatible provider needs an HTTP(S) base URL")
        ollama_url = options.get("ollama_url", "http://127.0.0.1:11434")
        if not isinstance(ollama_url, str) or not ollama_url.startswith(("http://", "https://")):
            raise ProviderError("Invalid Ollama endpoint")
        remote = provider == "openrouter" or (provider == "compatible" and not is_loopback(base_url)) or (provider == "ollama" and not is_loopback(ollama_url))
        if remote and options.get("accept_remote") is not True:
            raise ProviderError("Explicitly approve sending excerpts to a remote API; charges may apply")
        try:
            max_segments = int(options.get("max_segments", 3))
        except (TypeError, ValueError) as exc:
            raise ProviderError("Invalid batch size") from exc
        if not 1 <= max_segments <= 20:
            raise ProviderError("GUI batches are limited to 1..20 segments")
        if (project / ".translate.lock").exists():
            raise ProviderError("Translation already running; check existing batch")
        with self._jobs_lock:
            if any(j["project_id"] == project_id and j["state"] in ("queued", "running") for j in self._jobs.values()):
                raise ProviderError("Translation already queued for this project")
            job_id = uuid.uuid4().hex
            self._jobs[job_id] = {"id": job_id, "project_id": project_id, "state": "queued", "error": None, "result": None}

        def worker():
            with self._jobs_lock:
                self._jobs[job_id]["state"] = "running"
            try:
                from naughtyboddy import infer_text
                if provider == "mock":
                    inference = None
                else:
                    inference = lambda prompt: infer_text(
                        provider, model, prompt, base_url=base_url or None, ollama_url=ollama_url,
                        temperature=0.2, max_tokens=2500, timeout=180)
                result = run_translation(project, provider=provider, model=model or "demo",
                                         max_segments=max_segments, inference=inference)
                with self._jobs_lock:
                    self._jobs[job_id]["state"] = "failed" if result.get("errors") else "done"
                    self._jobs[job_id]["result"] = result
            except Exception as exc:
                with self._jobs_lock:
                    self._jobs[job_id]["state"] = "failed"
                    self._jobs[job_id]["error"] = f"{type(exc).__name__}: {exc}"

        threading.Thread(target=worker, name="nb-translation-" + job_id[:8], daemon=True).start()
        return {"job_id": job_id, "state": "queued"}

    def export(self, project_id: str, fmt: str, allow_demo: bool = False) -> dict:
        if fmt not in ("epub", "txt"):
            raise ProviderError("Choose EPUB or TXT")
        project = self.path(project_id)
        directory = project / "exports"
        directory.mkdir(exist_ok=True)
        basename = f"translated-{uuid.uuid4().hex[:8]}.{fmt}"
        info = export_project(project, directory / basename, allow_demo=allow_demo)
        return {"filename": basename, "download_url": f"/api/projects/{project_id}/exports/{basename}", **info}


class StudioHTTP(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], service: StudioService):
        # Do not allow LAN exposure, even when caller passes an external host.
        if address[0] not in ("127.0.0.1", "::1"):
            raise ValueError("NaughtyBoddy Studio only binds to loopback")
        super().__init__(address, StudioHandler)
        self.service = service


class StudioHandler(BaseHTTPRequestHandler):
    server: StudioHTTP
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args):
        pass  # avoids logging private paths / book text in request URLs

    def _headers(self, code: int, content_type: str, size: int, *, attachment: str | None = None):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(size))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        if attachment:
            self.send_header("Content-Disposition", f'attachment; filename="{attachment}"')
        self.end_headers()

    def _json(self, code: int, obj: dict | list):
        payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self._headers(code, "application/json; charset=utf-8", len(payload))
        self.wfile.write(payload)

    def _error(self, code: int, message: str):
        self._json(code, {"error": message})

    def _host_ok(self) -> bool:
        host = self.headers.get("Host", "")
        actual_port = self.server.server_address[1]
        return host in (f"127.0.0.1:{actual_port}", f"localhost:{actual_port}", f"[::1]:{actual_port}")

    def _check(self, changing: bool = False) -> bool:
        if not self._host_ok():
            self._error(403, "Only localhost access is permitted")
            return False
        if changing:
            origin = self.headers.get("Origin", "")
            if origin and origin not in (f"http://127.0.0.1:{self.server.server_address[1]}",
                                         f"http://localhost:{self.server.server_address[1]}"):
                self._error(403, "Cross-origin writes are disabled")
                return False
            if not secrets.compare_digest(self.headers.get("X-NB-Token", ""), self.server.service.csrf_token):
                self._error(403, "Missing session token")
                return False
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                self._error(415, "Expected application/json")
                return False
        return True

    def _body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "-1"))
        except ValueError as exc:
            raise ProviderError("Invalid Content-Length") from exc
        if length < 0 or length > MAX_JSON:
            raise ProviderError("Invalid or oversized request body")
        data = json.loads(self.rfile.read(length))
        if not isinstance(data, dict):
            raise ProviderError("Expected JSON object")
        return data

    def _send_static(self, name: str):
        if name not in ("index.html", "style.css", "app.js"):
            self._error(404, "Not found")
            return
        data = (WEB_ROOT / name).read_bytes()
        mime = {"index.html": "text/html", "style.css": "text/css", "app.js": "text/javascript"}[name]
        self._headers(200, f"{mime}; charset=utf-8", len(data))
        self.wfile.write(data)

    def _parts(self) -> list[str]:
        return [x for x in urlsplit(self.path).path.split("/") if x]

    def do_GET(self):
        if not self._check():
            return
        try:
            path = self._parts()
            query = parse_qs(urlsplit(self.path).query)
            srv = self.server.service
            if path in ([], ["index.html"]):
                return self._send_static("index.html")
            if path in (["style.css"], ["app.js"]):
                return self._send_static(path[0])
            if path == ["api", "bootstrap"]:
                return self._json(200, {"csrf_token": srv.csrf_token, "version": "P3.1", "workspace": str(srv.workspace)})
            if path == ["api", "local", "status"]:
                return self._json(200, srv.models.status())
            if path == ["api", "local", "catalog"]:
                return self._json(200, srv.models.catalog(query.get("repo", [""])[0]))
            if path == ["api", "local", "engine"]:
                return self._json(200, srv.models.engine_status())
            if path == ["api", "local", "reports"]:
                return self._json(200, {"reports": srv.models.reports()})
            if len(path) == 4 and path[:3] == ["api", "local", "jobs"]:
                return self._json(200, srv.models.job(path[3]))
            if path == ["api", "projects"]:
                return self._json(200, {"projects": srv.list_projects()})
            if path == ["api", "models"]:
                return self._json(200, srv.discover_models(query.get("source", ["ollama"])[0],
                                                         query.get("query", [""])[0], int(query.get("limit", ["12"])[0])))
            if len(path) == 3 and path[:2] == ["api", "jobs"]:
                return self._json(200, srv.job_status(path[2]))
            if len(path) >= 3 and path[:2] == ["api", "projects"]:
                project_id = path[2]
                if len(path) == 3:
                    return self._json(200, srv.summary(project_id))
                if path[3:] == ["segments"]:
                    return self._json(200, srv.segments(project_id, int(query.get("chapter", ["1"])[0]),
                                                        int(query.get("offset", ["0"])[0])))
                if path[3:] == ["glossary"]:
                    return self._json(200, srv.get_glossary(project_id))
                if path[3:] == ["audit"]:
                    return self._json(200, audit_project(srv.path(project_id)))
                if len(path) == 5 and path[3] == "exports" and re.fullmatch(r"translated-[0-9a-f]{8}\.(?:txt|epub)", path[4]):
                    export = srv.path(project_id) / "exports" / path[4]
                    if not export.is_file() or export.is_symlink():
                        raise ProviderError("Export not found")
                    data = export.read_bytes()
                    self._headers(200, "application/epub+zip" if export.suffix == ".epub" else "text/plain; charset=utf-8", len(data), attachment=path[4])
                    self.wfile.write(data)
                    return
            return self._error(404, "Not found")
        except (ProviderError, ValueError, KeyError, TypeError, OSError, sqlite3.DatabaseError) as exc:
            self._error(400, str(exc))

    def do_POST(self):
        if not self._check(changing=True):
            return
        try:
            path = self._parts()
            data = self._body()
            srv = self.server.service
            if path == ["api", "projects"]:
                return self._json(201, srv.import_book(data))
            if path == ["api", "local", "install"]:
                return self._json(202, srv.models.install(data))
            if path == ["api", "local", "launch"]:
                return self._json(200, srv.models.launch(data))
            if path == ["api", "local", "stop"]:
                return self._json(200, srv.models.stop())
            if path == ["api", "local", "evaluate"]:
                return self._json(202, srv.models.evaluate(data))
            if len(path) >= 4 and path[:2] == ["api", "projects"]:
                project_id = path[2]
                if path[3:] == ["translate"]:
                    return self._json(202, srv.start_translation(project_id, data))
                if path[3:] == ["export"]:
                    return self._json(201, srv.export(project_id, data.get("format", "epub"),
                                                       data.get("allow_demo") is True))
            return self._error(404, "Not found")
        except (ProviderError, ValueError, KeyError, TypeError, OSError, sqlite3.DatabaseError) as exc:
            self._error(400, str(exc))

    def do_PATCH(self):
        if not self._check(changing=True):
            return
        try:
            path = self._parts()
            data = self._body()
            if len(path) == 4 and path[:2] == ["api", "projects"] and path[3] == "glossary":
                return self._json(200, self.server.service.save_glossary(path[2], data.get("terms")))
            if len(path) == 5 and path[:2] == ["api", "projects"] and path[3] == "segments":
                return self._json(200, self.server.service.edit_segment(path[2], path[4], data.get("target")))
            return self._error(404, "Not found")
        except (ProviderError, ValueError, KeyError, TypeError, OSError, sqlite3.DatabaseError) as exc:
            self._error(400, str(exc))


def serve_studio(*, workspace: Path, port: int = 8765, open_browser: bool = True):
    if not 0 <= port <= 65535:
        raise ProviderError("Port must be 0..65535")
    service = StudioService(workspace)
    server = StudioHTTP(("127.0.0.1", port), service)
    url = f"http://127.0.0.1:{server.server_address[1]}"
    print(f"NaughtyBoddy Studio: {url}\nLocal projects: {service.projects}\nPress Ctrl+C to stop.", flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever(poll_interval=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        service.models.stop()
        server.server_close()
