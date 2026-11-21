# RepoTriage Minion

**Local-first repository QA, issue triage, and release-readiness agent built on the OpenMinion 0.1 Python SDK** (submitted for **Cortensor Hackathon #5**).

RepoTriage Minion demonstrates a clean, reproducible developer workflow powered by `openminion==0.1.23`: it inspects a local repository using read-only structured tools, detects `TODO`/`FIXME`/`BUG` markers and potential hardcoded secrets, checks release hygiene, supports multi-turn session continuity & isolation, streams execution progress events, and validates typed Pydantic triage reports.

---

## Why This Workflow

Maintainers and hackathon builders repeatedly run the same pre-release QA checklist before opening a PR or tagging a release:
1. Scan repository structure and test coverage.
2. Catch leftover `BUG` / `FIXME` / `TODO` markers and accidental hardcoded credentials.
3. Verify release hygiene (`README`, `LICENSE`, packaging metadata, tests, `.gitignore`).
4. Produce a concise, prioritized triage summary (free-form or structured JSON).

---

## OpenMinion 0.1 SDK Architecture

```
repo-triage-minion CLI
  └── RepoTriageRunner (src/repo_triage_minion/agent.py)
        └── openminion.Agent (0.1.23)
              ├── Tools (@tool, min_scope="READ_ONLY", idempotent=True)
              │     ├── scan_repository_structure
              │     ├── find_code_markers
              │     ├── check_release_hygiene
              │     └── inspect_file_excerpt
              ├── Optional Write Tool (@tool, default WRITE_SAFE → confirmation)
              │     └── save_triage_markdown (not in the default tool set)
              ├── Durable Local Sessions (shared + isolated session_id)
              ├── Streaming Progress (Agent.run_stream + on_delta)
              ├── Typed Output (output_type=TriageReport, Pydantic v2)
              └── Explicit Error Handling (ProviderError, TurnTimeoutError, AgentOutputValidationError)
```

---

## Quick Start (Reproducible in < 2 Minutes)

### 1. Create a virtual environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

*(Requires Python 3.11+. Verified on Python 3.14.6 with `openminion==0.1.23`.)*

### 2. Offline smoke test (no API key required)

Run the automated unit & OpenMinion integration test suite:

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

Run the multi-block verification harness against the bundled `sample_target_repo`:

```bash
OPENMINION_HOME="$PWD/.local-om" OPENMINION_DATA_ROOT="$PWD/.local-om/.openminion" \
PYTHONPATH=src python -m repo_triage_minion.cli verify-blocks sample_target_repo \
  --config agents.example.json --agent triage-echo
```

### 3. Real model-backed run (OpenAI, Gemini, Cortensor Portal, or Ollama)

Pick any configured profile in `agents.example.json` and export its corresponding API key:

```bash
# Example A: OpenAI (gpt-4.1-mini)
export OPENAI_API_KEY="your-key"
PYTHONPATH=src python -m repo_triage_minion.cli triage sample_target_repo \
  --config agents.example.json --agent triage-openai --stream

# Example B: Gemini (gemini-3.6-flash)
export GEMINI_API_KEY="your-key"
PYTHONPATH=src python -m repo_triage_minion.cli triage sample_target_repo \
  --config agents.example.json --agent triage-gemini --structured

# Example C: Cortensor Portal (if you have Portal access)
export CORTENSOR_API_KEY="your-key"
PYTHONPATH=src python -m repo_triage_minion.cli triage sample_target_repo \
  --config agents.example.json --agent triage-cortensor --stream

# Example D: Local Ollama (no cloud API key)
PYTHONPATH=src python -m repo_triage_minion.cli triage sample_target_repo \
  --config agents.example.json --agent triage-ollama
```

Add `--followup "Which single issue should we fix first before release?"` to test multi-turn session continuity in the same local session.

---

## Submission Documents

- **[BUILDING_BLOCKS_TESTED.md](./BUILDING_BLOCKS_TESTED.md)** — Exact OpenMinion 0.1.23 building blocks exercised, what worked, and concrete issues encountered.
- **[WHAT_WE_LEARNED.md](./WHAT_WE_LEARNED.md)** — Actionable product & DX feedback for OpenMinion and Cortensor maintainers.
- **[DEMO_SCRIPT.md](./DEMO_SCRIPT.md)** — 1–5 minute demo walkthrough script.
