# P5.5 — Choice-only discovery wizard

NaughtyBoddy's first public-facing solution finder is intentionally **not a chatbot**.

**User chooses:** creative task → privacy requirement → rough hardware category → principal preference. The four questions are fully enumerated and reversible. There is **no free-text field**, prompt interpretation, autonomous tool calling, model API request, account requirement or data upload.

Run the existing Studio command:

    python naughtyboddy.py studio

Open http://127.0.0.1:8765/discover or select “按需求寻找工具” in the Studio sidebar. No model/backend needs to be installed.

## What the result means

The engine reads the existing local P5 needs/solutions/assessments/frictions registry plus the manually curated, reviewable registry/chooser-profiles.json. It returns project links, documented local options, tool role (full workbench / extension / backend / utility), source documents, and relevant recorded friction reports. It does **not** pick the most powerful model or rank adult-content quality.

Strict-local choices place tools whose local mode has not been documented in a separate **unconfirmed** section rather than pretending they are impossible or proven safe. A documented local option is **not** a real-world network privacy audit. Hardware categories are retained to understand the user's constraint, but **no GPU or model-fit claim is made** without measurements.

Priorities for installation ease, editing or narrative continuity are not assigned invented numerical scores. Documented editability can affect display order; unmeasured qualities only generate cautions and suggested checks.

No uploads, paid APIs, background provider queries, usage telemetry, inference jobs, software downloads or executable plugins are triggered by this page. It is read-only and bound to the existing Studio localhost security checks.

## Offline checks

    python -m unittest discover -s tests -v
    python nb_registry.py validate
    node --check web/chooser.js

Selection examples: manga + local-only + 8GB + editable; roleplay + local-only + CPU + continuity. For each, the next step remains reading relevant project documentation and running the tests that are still marked not_run.

## Non-goals / next improvement

A large-scale LLM semantic search, open question box, speculative model benchmarks, crowd-sourced free-text submissions, and automatic installation are deliberately out of scope. When the evidence library expands, add **more precisely-defined choices** instead of treating free-text-to-LLM interpretation as necessary.
