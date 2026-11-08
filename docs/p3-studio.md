# P3 — Local creative Studio GUI

## Goal

Make the existing P2 novel workflow accessible without a terminal, and exercise Library / Studio / Discovery as independently testable product surfaces. **Not** a general coding Agent or a separate chatbot.

## Implementation

- `nb_studio.py` launches a `ThreadingHTTPServer` on `127.0.0.1` only. Uses Python standard library; browser receives three static assets under `web/`.
- Local workspaces default to `~/.naughtyboddy/projects/{uuid}`; no arbitrary filesystem browse APIs. Imports accept base64 JSON, limited to 12 MiB and `.txt` / `.epub`, with affirmative rights confirmation.
- `GET /api/projects` lists GUI-created projects; `GET /api/projects/{id}` returns chapter/progress data. Segments paginated at 80 records per request.
- `PATCH /api/projects/{id}/segments/{stable-id}` performs a persistent manual edit, and records previous and new target values in a private SQLite `studio_edits` table. Saving an empty field returns the segment to pending.
- `GET/PATCH /api/projects/{id}/glossary` reads/validates/persists terminology in project-local JSON. New terms apply to future translation batches; past results are not automatically altered.
- `POST /api/projects/{id}/translate` explicitly runs 1..20 segments, with one active job per project, and returns a pollable job ID. No automatic retry or cloud fallback. Remote model use requires `accept_remote: true`; actual service-side provider credentials remain in environment variables.
- `GET /api/models` calls only catalog endpoints or local inventory; it never sends book contents. Candidate model names and tags do not imply proven compatibility.
- `POST /api/projects/{id}/export` creates a separate output under project `exports/`, and returns a local, non-guessable project-scoped download URL. P2's incomplete/demo guards remain enforced.
- Static UI uses text nodes for user-controlled content, rather than injecting HTML. The HTTP server checks Host, requires a session token for writes and rejects cross-origin mutations. Security headers include CSP, frame protection and nosniff.

## Tests

`python -m unittest discover -s tests -v` tests the full P0/P1/P2/P3 offline suite. P3 tests include the API over a genuine loopback HTTP socket, rights confirmation, URL-scoped access, explicit cloud opt-in, glossary CRUD, edit history, batch persistence, export guards, CSRF, and refusal to bind to LAN interfaces. `node --check web/app.js` verifies the frontend syntax.

**Not verified**: live GPU/model behaviour; browser screenshot in environments that block loopback browser navigation; cross-platform installers; actual provider billing; security under hostile local OS users.

## Known limitations and next direction

- Studio is a local web application, not yet a packaged Windows/macOS/Linux desktop application.
- The UI Library currently lists only projects created by the GUI; CLI project import/migration is future work.
- No UI for GGUF download/launch (P1 CLI exists); no model-quality scoring or automatic routing.
- Translation jobs have no cancel action, durable job queue or stale-lock cleanup; if a process crashes, progress is preserved but the next run may need manual lock recovery.
- No source EPUB image/style preservation or PDF/OCR input; it is intentionally a text-only first vertical.
- One active translation batch per project, no automatic API spend estimation; manual cloud consent is mandatory.
- Usability/accessibility review on actual Windows and mobile browsers is pending.

Next: P3.1 strengthen local-model configuration, estimates, failure handling, GUI polish, packaging; P4 introduces manga/PDF/website connectors after permission model and source rules are explicit.
