# What We Learned — Actionable Product Feedback for OpenMinion & Cortensor

Working end-to-end with `openminion==0.1.23` on Python 3.14 was genuinely productive: the top-level `from openminion import Agent, tool, ProviderError` ergonomics, Pydantic v2 `output_type` validation, and `openminion setup --list-providers --json` catalog make local-first agent prototyping fast.

Below are **4 concrete, actionable improvements** that would significantly reduce friction for new Cortensor / OpenMinion builders:

---

### 1. Default `default_channel` to `"console"` in SDK-loaded configs (and align `mode=warn` semantics)
- **Problem**: Builders who hand-write a minimal `agents.json` (similar to the compact JSON snippet in the root README) omit `"default_channel": "console"` and immediately hit `RuntimeError: inbound authenticity denied (reason=invalid_channel, mode=warn)`. Seeing `denied` when `mode=warn` is also confusing.
- **Recommendation**:
  1. Default `AgentConfig.default_channel` to `"console"` when unspecified in `agents.json`.
  2. Emit a clear config-validation message (e.g., `"Agent 'triage-echo' is missing default_channel; set default_channel='console' for local SDK runs"`) instead of a generic inbound authenticity denial.

---

### 2. Close SQLite connections deterministically inside `Agent.__exit__` / `APIRuntime.close()`
- **Problem**: Running `unittest` under Python 3.14 triggers multiple `ResourceWarning: unclosed database in <sqlite3.Connection>` warnings even when `Agent` is properly wrapped in a `with` block.
- **Recommendation**: Ensure every SQLite connection opened by storage/session/memory stores is tracked and explicitly closed during `APIRuntime.close()` (and `Agent.__exit__`). Adding a `pytest -W error::ResourceWarning` check on one SDK smoke test in CI would prevent regressions.

---

### 3. Document how to assert tool execution from `AgentRunResult`
- **Problem**: `AgentRunResult` exposes `raw`, `metadata`, and `stats`, but the SDK examples do not show where tool-call records live. When writing CI assertions (especially with `provider="echo"` plus `forced_tools`), it is unclear how to confirm whether tools actually ran.
- **Recommendation**: Add a short example in `examples/sdk/tool_agent.py` showing which `raw` / `metadata` keys contain tool calls, or expose a typed `result.tool_calls` helper.

---

### 4. Provide a one-command starter template for Cortensor Portal + local fallback
- **Problem**: `openminion setup --list-providers --json` cleanly lists `cortensor-portal` and `cortensor-router`, while `openminion config init --provider echo` generates a large (~270-line) config file that can intimidate first-time SDK users.
- **Recommendation**: Add a compact `openminion config init --minimal --provider cortensor-portal` flag (or a minimal SDK example in `examples/sdk/`) showing the smallest valid `agents.json` needed for `Agent(config_path=...)` with both a hosted model and an offline `echo` test profile.
