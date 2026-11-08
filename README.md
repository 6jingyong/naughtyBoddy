# NaughtyBoddy

**A free, open-source, local-first creative studio for adult-oriented fiction and multimedia.**

Early experimental repository. This is a **standalone creative product**, not an extension of Human Harness, Codex, or a chat-agent framework.

## Product idea

- **Library**: manage your own or licensed stories, documents, comics, image/video assets and revisions.
- **Studio**: translate, edit, adapt and create across formats via repeatable, inspectable workflows.
- **Discovery**: discover local and hosted models, investigate claimed low-refusal variants, and record actual task-specific performance.
- **Runtime**: use existing inference engines (Ollama / llama.cpp-compatible endpoints now; other backends later), rather than shipping a new inference engine.

**Low-refusal model names are search hints, not verified safety or quality scores.** The software will support lawful adult fiction, with guardrails for minors, non-consensual intimate imagery, provenance and permissions. Rights and permission restrictions apply to third-party sources.

## First executable spike — Model Discovery

Requires **Python 3.11+**; uses only Python's standard library. No account or API key is needed to list public model metadata or inspect a running local Ollama server.

```bash
python naughtyboddy.py discover --source ollama
python naughtyboddy.py discover --source huggingface --query abliterated --limit 10
python naughtyboddy.py discover --source openrouter --query uncensored --limit 10
python -m unittest discover -s tests -v
```

Model probes only run when explicitly requested. They send the contents of the supplied local prompt file to the selected model. Local probing example:

```bash
printf 'Translate this dialogue faithfully into Chinese: Two adults discuss their relationship.\n' > prompt.txt
python naughtyboddy.py probe --provider ollama --model YOUR_LOCAL_MODEL --prompt-file prompt.txt
```

For a local llama.cpp / KoboldCpp / other OpenAI-compatible server:

```bash
python naughtyboddy.py probe --provider compatible --base-url http://127.0.0.1:8080/v1 --model YOUR_MODEL --prompt-file prompt.txt
```

For OpenRouter, set `OPENROUTER_API_KEY` in your **local environment**, then:

```bash
python naughtyboddy.py probe --provider openrouter --model PROVIDER/MODEL --prompt-file prompt.txt
```

No prompts or secrets are uploaded for discovery; probing a remote API **does** send the supplied prompt to that provider. API keys are not saved. Probe results print locally, unless `--output` is explicitly provided. Do not upload private probe outputs to a public repository.

This is a **metadata + smoke-test prototype**, not a verified model ranking, working GUI, automatic model downloader, or full novel translation engine.

## Next milestones

1. **P0** (this commit): local/cloud discovery, explicit model probe, offline tests.
2. **P1**: local model install/run integration, model capability evaluation and provenance, private results storage.
3. **P2**: EPUB/TXT novel translation workflow with chapter checkpoints, glossary and complete export.
4. **P3**: creative desktop GUI, media-specific editors, plugin connectors and authorized external sources.

See [docs/architecture.md](docs/architecture.md).

## License

License selection is **pending**. The intention is a free/open-source release; no license has yet been granted by this repository. Contributors should not assume that an absent license is permissive.
