# Building Blocks Tested — OpenMinion 0.1.23

- **Environment**: macOS (Apple Silicon), Python `3.14.6`, `openminion==0.1.23` (editable install from `github.com/openminion/openminion`)
- **Project**: `repo-triage-minion`
- **Verification commands**:
  ```bash
  PYTHONPATH=src python -m unittest discover -s tests -v
  PYTHONPATH=src python -m repo_triage_minion.cli verify-blocks sample_target_repo \
    --config agents.example.json --agent triage-echo
  ```

> **Scope of this note:** the results below were verified with the offline `echo` provider. The echo provider exercises configuration, storage, sessions, streaming plumbing, and error paths, but it does not call a model. Model-backed results are recorded separately in the demo video section of the submission.

---

## Summary Matrix

| Building Block | API / Surface Tested | Status | Notes |
|---|---|---|---|
| **Agent runtime & context manager** | `with Agent(...) as agent: agent.run(...)` | Worked, with cleanup warning | `ResourceWarning: unclosed database` is emitted after the context manager exits (Finding 2). |
| **Read-only structured tools** | `@tool(min_scope="READ_ONLY", idempotent=True)` | Worked locally | Tool functions return deterministic JSON; verified directly by unit tests. Model-driven tool calls require a real provider. |
| **Durable sessions** | `session_id="..."` across turns | Worked | Repeated turns returned the same `session_id`. |
| **Session isolation** | Per-turn `agent.run(..., session_id="...")` override | Worked | Override returned a distinct `session_id`. |
| **Streaming progress** | `agent.run_stream(prompt, on_delta=...)` | Worked | 9 progress events delivered in one turn without errors. |
| **Typed structured output** | `output_type=TriageReport` + `AgentOutputValidationError` | Worked | Non-JSON output raised `AgentOutputValidationError` with Pydantic v2 diagnostics; `raw_text` was preserved. |
| **Minimal config & channel authenticity** | `Agent(config_path=..., agent_id=...)` | Rough edge | A per-agent profile without `default_channel` failed with `inbound authenticity denied ... mode=warn` (Finding 1). |
| **CLI provider discovery** | `openminion setup --list-providers --json` | Worked | Machine-readable catalog includes `cortensor-portal`, `cortensor-router`, `openai`, `gemini`, `ollama`, and others. |

---

## Findings

### Finding 1: A per-agent profile without `default_channel` fails in `mode=warn`
- **Location**: `openminion/services/gateway/security.py` (`enforce_inbound_authenticity`)
- **Reproduction**:
  1. Write an `agents.json` with `{"default_agent": "triage-echo", "agents": {"triage-echo": {"provider": "echo", "model": "echo-1"}}}`.
  2. Run `with Agent(config_path="agents.json", agent_id="triage-echo") as agent: agent.run("hello")`.
- **Expected**: Local SDK runs default to the trusted `console` channel, or `mode=warn` records a warning and continues.
- **Actual**: `RuntimeError: inbound authenticity denied (reason=invalid_channel, mode=warn)`.
- **Workaround**: Add `"name"` and `"default_channel": "console"` to each agent profile (as produced by `openminion config init`).
- **Note**: Before filing this upstream, it should be confirmed against the latest `main` and checked for an existing issue.

### Finding 2: `ResourceWarning: unclosed database` after `with Agent(...)` exits
- **Reproduction**: Run `PYTHONPATH=src python -m unittest discover -s tests -v` on Python 3.14.
- **Expected**: Exiting the `Agent` context manager closes the SQLite connections it opened.
- **Actual**: 4 `ResourceWarning: unclosed database in <sqlite3.Connection ...>` warnings during the integration test.
- **Impact**: Harmless for short CLI runs; may accumulate file descriptors in long-running processes or large test suites.
