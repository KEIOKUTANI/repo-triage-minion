"""Structured OpenMinion @tool definitions for local repository QA & triage."""

from __future__ import annotations

import json
import re
from pathlib import Path

from openminion import tool

_IGNORED_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "node_modules", ".openminion"}
_MARKER_RE = re.compile(r"\b(TODO|FIXME|BUG|HACK|XXX)\b[:\s-]*(.*)", re.IGNORECASE)
_SECRET_HINT_RE = re.compile(
    r"(api[_-]?key|secret|token|password)\s*=\s*['\"][A-Za-z0-9_\-]{8,}['\"]",
    re.IGNORECASE,
)


def _safe_resolve(path_str: str) -> Path:
    path = Path(path_str).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {path}")
    return path


@tool(min_scope="READ_ONLY", idempotent=True, tags=("qa", "repo"))
def scan_repository_structure(repo_path: str) -> str:
    """List key files and basic language/test counts in a local repository."""

    root = _safe_resolve(repo_path)
    if not root.is_dir():
        return json.dumps({"error": f"Not a directory: {root}"})

    files: list[str] = []
    py_count = 0
    test_files: list[str] = []

    for item in sorted(root.rglob("*")):
        if any(part in _IGNORED_DIRS for part in item.parts):
            continue
        if item.is_file():
            rel = str(item.relative_to(root))
            files.append(rel)
            if item.suffix == ".py":
                py_count += 1
            if "test" in item.name.lower() or "tests" in item.parts:
                test_files.append(rel)

    payload = {
        "repo_name": root.name,
        "total_files": len(files),
        "python_files": py_count,
        "test_files": test_files[:30],
        "sample_files": files[:40],
    }
    return json.dumps(payload, indent=2)


@tool(min_scope="READ_ONLY", idempotent=True, tags=("qa", "security"))
def find_code_markers(repo_path: str) -> str:
    """Scan text/source files for TODO/FIXME/BUG markers and potential hardcoded secrets."""

    root = _safe_resolve(repo_path)
    markers: list[dict[str, object]] = []
    secret_hints: list[dict[str, object]] = []

    for item in sorted(root.rglob("*")):
        if any(part in _IGNORED_DIRS for part in item.parts) or not item.is_file():
            continue
        if item.suffix.lower() not in {".py", ".md", ".txt", ".json", ".toml", ".yaml", ".yml", ".js", ".ts"}:
            continue
        try:
            lines = item.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        rel = str(item.relative_to(root))
        for idx, line in enumerate(lines, start=1):
            m = _MARKER_RE.search(line)
            if m:
                markers.append(
                    {
                        "file": rel,
                        "line": idx,
                        "kind": m.group(1).upper(),
                        "detail": m.group(2).strip()[:160],
                    }
                )
            if _SECRET_HINT_RE.search(line):
                secret_hints.append(
                    {
                        "file": rel,
                        "line": idx,
                        "warning": "Possible hardcoded credential pattern detected (value redacted).",
                    }
                )

    return json.dumps(
        {
            "repo_name": root.name,
            "marker_count": len(markers),
            "markers": markers[:50],
            "secret_hint_count": len(secret_hints),
            "secret_hints": secret_hints[:20],
        },
        indent=2,
    )


@tool(min_scope="READ_ONLY", idempotent=True, tags=("qa", "release"))
def check_release_hygiene(repo_path: str) -> str:
    """Check presence of essential repository release artifacts (README, tests, packaging, license)."""

    root = _safe_resolve(repo_path)
    names = {p.name.lower() for p in root.iterdir()} if root.is_dir() else set()
    has_tests = any(
        (root / candidate).exists() for candidate in ("tests", "test")
    ) or any(p.name.startswith("test_") for p in root.rglob("*.py"))

    checks = {
        "has_readme": any(n.startswith("readme") for n in names),
        "has_license": any(n.startswith("license") for n in names),
        "has_packaging": bool({"pyproject.toml", "setup.py", "requirements.txt", "package.json"} & names),
        "has_tests": has_tests,
        "has_gitignore": ".gitignore" in names,
    }
    missing = [k for k, ok in checks.items() if not ok]
    return json.dumps(
        {
            "repo_name": root.name,
            "checks": checks,
            "missing": missing,
        },
        indent=2,
    )


@tool(min_scope="READ_ONLY", idempotent=True, tags=("qa", "repo"))
def inspect_file_excerpt(file_path: str, max_lines: int = 60) -> str:
    """Read the first N lines of a local text file for focused code inspection."""

    path = _safe_resolve(file_path)
    if not path.is_file():
        return json.dumps({"error": f"Not a file: {path}"})
    capped = max(1, min(max_lines, 120))
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()[:capped]
    return "\n".join(f"{i + 1:3d}: {line}" for i, line in enumerate(lines))


@tool(tags=("report",))
def save_triage_markdown(output_path: str, markdown_body: str) -> str:
    """Write a triage report Markdown file to a local path.

    No ``min_scope`` is declared, so OpenMinion classifies this as ``WRITE_SAFE``
    and the default action policy asks for confirmation before it runs.
    It is not included in the default read-only triage tool set.
    """

    target = Path(output_path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(markdown_body, encoding="utf-8")
    return f"saved report ({len(markdown_body)} chars) to {target}"


@tool(min_scope="READ_ONLY", idempotent=True, tags=("qa", "repo", "release"))
def run_full_repo_audit(repo_path: str) -> str:
    """Run structure, code-marker/secret, and release-hygiene checks in one compact JSON payload."""

    return json.dumps(
        {
            "structure": json.loads(scan_repository_structure(repo_path)),
            "markers": json.loads(find_code_markers(repo_path)),
            "hygiene": json.loads(check_release_hygiene(repo_path)),
        },
        indent=2,
    )


READ_ONLY_TOOLS = [
    run_full_repo_audit,
    scan_repository_structure,
    find_code_markers,
    check_release_hygiene,
    inspect_file_excerpt,
]
ALL_TOOLS = [*READ_ONLY_TOOLS, save_triage_markdown]
