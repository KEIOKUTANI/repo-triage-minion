# Building Blocks Tested — OpenMinion 0.1.23

- **Environment**: macOS (Apple Silicon), Python `3.14.6`, `openminion==0.1.23` (editable install from `github.com/openminion/openminion`)
- **Project**: `repo-triage-minion`
- **Verification commands**:
  ```bash
  PYTHONPATH=src python -m unittest discover -s tests -v
  PYTHONPATH=src python -m repo_triage_minion.cli verify-blocks sample_target_repo \
    --config agents.example.json --agent triage-echo
  ```

> **Scope of this note:** verified both offline (`echo` provider) and with a **real local model** (**Ollama `qwen2.5:3b`** on Apple M4 Metal, ~40 tokens/sec) using `openminion==0.1.23`.

---

## Real Model-Backed Run Summary (Ollama `qwen2.5:3b`)

- **Command**:
  ```bash
  OPENMINION_HOME=/tmp/om_ollama4 OPENMINION_DATA_ROOT=/tmp/om_ollama4/.openminion \
  PYTHONPATH=src python -m repo_triage_minion.cli triage sample_target_repo \
    --config agents.example.json --agent triage-ollama --model-choice --stream \
    --followup "Which single issue should we fix first before release?"
  ```
- **Observed Result**:
  - `openminion 0.1.23`, `session=repo-triage-session`, **`stream_events=32`**.
  - The model invoked `run_full_repo_audit` via native tool calling (`tool_call_strategy: "native"`), accurately surfaced all 3 code markers (`app.py` lines 3, 10, 15), the redacted hardcoded-secret warning (`app.py` line 4), and missing release hygiene (`LICENSE`, packaging, tests), then produced a prioritized action plan.
  - On the follow-up turn in the same session, OpenMinion triggered its safe fallback (`answer-only budget finalization did not produce final text, so preserved tool evidence is returned`), preserving tool evidence instead of failing silently.

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

### Finding 3: Local small-model tool loops under Ollama default `tool_call_strategy: "fallback"`
- **Reproduction**: Run a multi-tool triage prompt against local Ollama (`qwen2.5:3b`, 4096-token context) using the default `tool_call_strategy: "fallback"`.
- **Actual**: The turn repeatedly re-invoked tools until hitting `TurnTimeoutError: Turn execution timed out after 90.00 seconds` (which our runner caught cleanly).
- **Mitigation & What Worked**: Switching `providers.ollama.tool_call_strategy` to `"native"` and consolidating read-only checks into a single `run_full_repo_audit` tool reduced context pressure and produced a complete, accurate triage summary with 32 stream events.
- **Additional Observation**: Setting `runtime.agent_loop_max_steps: 6` still emitted `budget.allocated` with `soft_cap: 24, effective_max_iterations: 24, source: "adaptive_budget"` in stream events, suggesting `adaptive_budget` can override a lower explicit step cap.
