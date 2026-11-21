"""Typed Pydantic output schemas for RepoTriage Minion."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TriageFinding(BaseModel):
    """Single actionable QA or issue-triage finding."""

    id: str = Field(..., description="Short identifier such as QA-001")
    severity: Literal["critical", "high", "medium", "low"]
    category: Literal["bug", "security", "tests", "docs", "hygiene"]
    file_path: str = Field(..., description="Relative file path inside the repository")
    summary: str = Field(..., description="Concise explanation of the issue")
    recommended_fix: str = Field(..., description="Concrete next action to resolve the issue")


class TriageReport(BaseModel):
    """Structured triage report returned by the OpenMinion Agent."""

    repo_name: str
    readiness: Literal["ready", "needs_fixes", "blocked"]
    summary: str
    findings: list[TriageFinding] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
