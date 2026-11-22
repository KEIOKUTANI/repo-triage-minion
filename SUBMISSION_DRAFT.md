# Cortensor Hackathon #5 — Submission Form & PR Draft

Use this ready-to-paste copy for both the **DoraHacks Build Submission** and the **Hackathon #5 Pull Request**.

---

## Project Title
**RepoTriage Minion — Local-First QA & Issue Triage Agent (OpenMinion 0.1 SDK)**

## One-Line Tagline
A reproducible local-first repository QA, secret/marker scanner, and release-readiness triage agent built on the OpenMinion 0.1 Python SDK.

## Links
- **Public Source Repository**: https://github.com/KEIOKUTANI/repo-triage-minion
- **Forked OpenMinion Repository**: https://github.com/KEIOKUTANI/openminion
- **Demo Video (1–5 min)**: https://github.com/KEIOKUTANI/repo-triage-minion/releases/download/v0.1.0/repo_triage_minion_demo.mp4

---

## Description / PR Body

### Overview
**RepoTriage Minion** is a lightweight, repeatable developer QA and release-readiness agent built on **OpenMinion 0.1 (`openminion==0.1.23`)**. It helps builders and maintainers scan a local repository before opening a PR or cutting a release—identifying `TODO`/`FIXME`/`BUG` markers, potential hardcoded secrets, missing release hygiene (`LICENSE`, tests, packaging, `.gitignore`), and prioritized next actions.

### OpenMinion 0.1 SDK Workflow
- **Structured Read-Only Tools (`@tool(min_scope="READ_ONLY", idempotent=True)`)**: `scan_repository_structure`, `find_code_markers`, `check_release_hygiene`, and `inspect_file_excerpt` run cleanly without confirmation under the default action policy, while `save_triage_markdown` remains confirmation-gated (`WRITE_SAFE`).
- **Durable Sessions & Isolation**: Multi-turn follow-up questions reuse `session_id`, while per-turn `session_id` overrides isolate independent runs.
- **Streaming Progress & Typed Output**: Exercises `Agent.run_stream(..., on_delta=...)`, Pydantic v2 `output_type=TriageReport`, and explicit `ProviderError` / `TurnTimeoutError` / `AgentOutputValidationError` handling.
- **Provider Flexibility**: Ships with `agents.example.json` supporting `echo` (offline CI smoke test), `openai`, `gemini`, `cortensor-portal`, and local `ollama`.

### Reproducibility
Includes a bundled `sample_target_repo` with intentional QA defects, an automated `unittest` suite (4/4 passing), and a `verify-blocks` command that exercises core OpenMinion building blocks in under 2 minutes.

### Building Blocks Tested & Actionable Feedback
Full evidence and minimal reproductions are documented in:
- `BUILDING_BLOCKS_TESTED.md`:
  1. Minimal per-agent `agents.json` without `default_channel` raises `RuntimeError: inbound authenticity denied (reason=invalid_channel, mode=warn)`.
  2. `with Agent(...)` leaves 4 unclosed `sqlite3.Connection` `ResourceWarning`s under Python 3.14 `unittest`.
- `WHAT_WE_LEARNED.md`:
  4 concrete DX recommendations (defaulting `default_channel="console"`, deterministic SQLite cleanup in `Agent.__exit__`, documenting tool-call inspection on `AgentRunResult`, and adding a `--minimal` config init template for Cortensor Portal + echo).
