"""OpenMinion 0.1 Python SDK agent orchestration for RepoTriage Minion."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from openminion import (
    Agent,
    AgentOutputValidationError,
    ProviderError,
    TurnTimeoutError,
    __version__ as openminion_version,
)

from .schemas import TriageReport
from .tools import READ_ONLY_TOOLS, check_release_hygiene, find_code_markers, scan_repository_structure

SYSTEM_INSTRUCTIONS = """\
You are RepoTriage Minion, a concise, evidence-based QA and release-readiness assistant.
Use the provided read-only repository tools to inspect the target directory before making claims.
Prioritize concrete bugs, potential secret leaks, missing release hygiene, and missing test coverage.
Never fabricate file paths or line numbers that were not observed in tool output.
"""


@dataclass
class TriageExecutionResult:
    """Normalized result returned by RepoTriageRunner."""

    openminion_version: str
    session_id: str
    text: str
    structured: TriageReport | None = None
    validation_error: str | None = None
    provider_error: str | None = None
    stream_event_count: int = 0
    local_snapshot: dict[str, Any] = field(default_factory=dict)


class RepoTriageRunner:
    """Runs repeatable repository QA workflows on top of OpenMinion's Agent SDK."""

    def __init__(
        self,
        *,
        config_path: str | None = None,
        agent_id: str | None = None,
        model: str | None = None,
        session_id: str = "repo-triage-session",
    ) -> None:
        self.config_path = config_path
        self.agent_id = agent_id
        self.model = model
        self.session_id = session_id

    def _build_prompt(self, repo_path: str, structured: bool) -> str:
        target = str(Path(repo_path).expanduser().resolve())
        base = (
            f"Call `run_full_repo_audit` once on `{target}`. "
            "Then immediately produce a concise QA & release-readiness summary listing "
            "the concrete bugs, hardcoded-secret warnings, missing release hygiene items, "
            "and prioritized next actions. Do not call additional tools unless needed."
        )
        if structured:
            base += (
                " Return valid JSON matching the TriageReport schema with fields: "
                "repo_name, readiness (ready|needs_fixes|blocked), summary, findings, next_actions."
            )
        return base

    def run_triage(
        self,
        repo_path: str,
        *,
        structured: bool = False,
        force_initial_tools: bool = True,
        stream: bool = False,
        on_delta: Callable[[dict[str, Any]], None] | None = None,
    ) -> TriageExecutionResult:
        """Execute a repository triage turn with explicit SDK error handling."""

        target = str(Path(repo_path).expanduser().resolve())
        forced = ["run_full_repo_audit"] if force_initial_tools else []
        prompt = self._build_prompt(target, structured=structured)
        event_count = 0

        def _track_delta(event: dict[str, Any]) -> None:
            nonlocal event_count
            event_count += 1
            if on_delta is not None:
                on_delta(event)

        try:
            with Agent(
                instructions=SYSTEM_INSTRUCTIONS,
                output_type=TriageReport if structured else None,
                config_path=self.config_path,
                agent_id=self.agent_id,
                model=self.model,
                tools=READ_ONLY_TOOLS,
                forced_tools=forced,
                session_id=self.session_id,
            ) as agent:
                if stream:
                    result = agent.run_stream(prompt, on_delta=_track_delta)
                else:
                    result = agent.run(prompt)
        except AgentOutputValidationError as exc:
            return TriageExecutionResult(
                openminion_version=openminion_version,
                session_id=self.session_id,
                text=exc.raw_text or "",
                validation_error=str(exc),
                stream_event_count=event_count,
            )
        except ProviderError as exc:
            return TriageExecutionResult(
                openminion_version=openminion_version,
                session_id=self.session_id,
                text="",
                provider_error=f"{exc.code}: {exc.message}",
                stream_event_count=event_count,
            )
        except TurnTimeoutError as exc:
            return TriageExecutionResult(
                openminion_version=openminion_version,
                session_id=self.session_id,
                text="",
                provider_error=f"timeout: {exc}",
                stream_event_count=event_count,
            )

        return TriageExecutionResult(
            openminion_version=openminion_version,
            session_id=result.session_id,
            text=result.text,
            structured=result.output if structured else None,
            stream_event_count=event_count,
        )

    def run_followup(
        self,
        question: str,
        *,
        isolated_session_id: str | None = None,
    ) -> TriageExecutionResult:
        """Run a follow-up turn in the same session or an explicitly isolated session."""

        active_session = isolated_session_id or self.session_id
        try:
            with Agent(
                instructions=SYSTEM_INSTRUCTIONS,
                config_path=self.config_path,
                agent_id=self.agent_id,
                model=self.model,
                tools=READ_ONLY_TOOLS,
                session_id=self.session_id,
            ) as agent:
                result = agent.run(question, session_id=active_session)
        except ProviderError as exc:
            return TriageExecutionResult(
                openminion_version=openminion_version,
                session_id=active_session,
                text="",
                provider_error=f"{exc.code}: {exc.message}",
            )

        return TriageExecutionResult(
            openminion_version=openminion_version,
            session_id=result.session_id,
            text=result.text,
        )


def collect_local_snapshot(repo_path: str) -> dict[str, Any]:
    """Run deterministic local tool checks directly for offline comparison/verification."""

    import json

    target = str(Path(repo_path).expanduser().resolve())
    return {
        "structure": json.loads(scan_repository_structure(target)),
        "markers": json.loads(find_code_markers(target)),
        "hygiene": json.loads(check_release_hygiene(target)),
    }
