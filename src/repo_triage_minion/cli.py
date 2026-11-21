"""Command-line interface for RepoTriage Minion."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from openminion import __version__ as openminion_version

from .agent import RepoTriageRunner, collect_local_snapshot


def _cmd_triage(args: argparse.Namespace) -> int:
    runner = RepoTriageRunner(
        config_path=args.config,
        agent_id=args.agent,
        model=args.model,
        session_id=args.session,
    )

    def _on_delta(event: dict) -> None:
        kind = event.get("kind") or event.get("type") or "delta"
        if args.verbose_stream:
            print(f"[stream:{kind}] {event}", file=sys.stderr)

    res = runner.run_triage(
        args.repo_path,
        structured=args.structured,
        force_initial_tools=not args.model_choice,
        stream=args.stream,
        on_delta=_on_delta if args.stream else None,
    )

    if res.provider_error:
        print(f"ERROR (provider): {res.provider_error}", file=sys.stderr)
        return 1

    if res.validation_error:
        print(f"WARNING (structured output validation failed): {res.validation_error}", file=sys.stderr)
        if res.text:
            print(f"Raw response:\n{res.text}")
        return 2

    if res.structured is not None:
        output_text = res.structured.model_dump_json(indent=2)
    else:
        output_text = res.text

    print(f"[openminion {res.openminion_version}] session={res.session_id}")
    if args.stream:
        print(f"[stream_events={res.stream_event_count}]")
    print(output_text)

    if args.followup:
        follow = runner.run_followup(args.followup)
        print(f"\n[followup session={follow.session_id}]\n{follow.text}")

    return 0


def _cmd_verify_blocks(args: argparse.Namespace) -> int:
    """Exercise core OpenMinion 0.1 building blocks and print a machine-readable report."""

    repo_path = str(Path(args.repo_path).expanduser().resolve())
    runner = RepoTriageRunner(
        config_path=args.config,
        agent_id=args.agent,
        model=args.model,
        session_id=f"{args.session}-main",
    )

    snapshot = collect_local_snapshot(repo_path)
    triage_res = runner.run_triage(repo_path, structured=False, force_initial_tools=True)
    followup_same = runner.run_followup("Repeat the repository name we just inspected.")
    followup_isolated = runner.run_followup(
        "What repository did we inspect?",
        isolated_session_id=f"{args.session}-isolated",
    )
    stream_res = runner.run_triage(repo_path, structured=False, force_initial_tools=False, stream=True)
    structured_res = runner.run_triage(repo_path, structured=True, force_initial_tools=False)

    report = {
        "openminion_version": openminion_version,
        "target_repo": repo_path,
        "local_deterministic_snapshot": {
            "total_files": snapshot["structure"]["total_files"],
            "marker_count": snapshot["markers"]["marker_count"],
            "secret_hint_count": snapshot["markers"]["secret_hint_count"],
            "missing_hygiene": snapshot["hygiene"]["missing"],
        },
        "blocks": {
            "tools_and_forced_tools": {
                "ok": triage_res.provider_error is None,
                "session_id": triage_res.session_id,
                "reply_preview": triage_res.text[:220],
                "error": triage_res.provider_error,
            },
            "session_continuity": {
                "ok": followup_same.provider_error is None and followup_same.session_id == triage_res.session_id,
                "session_id": followup_same.session_id,
                "reply_preview": followup_same.text[:220],
            },
            "session_isolation": {
                "ok": followup_isolated.provider_error is None
                and followup_isolated.session_id != triage_res.session_id,
                "session_id": followup_isolated.session_id,
                "reply_preview": followup_isolated.text[:220],
            },
            "streaming_progress": {
                "ok": stream_res.provider_error is None,
                "stream_event_count": stream_res.stream_event_count,
            },
            "structured_output_validation": {
                "parsed_ok": structured_res.structured is not None,
                "validation_error_caught": structured_res.validation_error is not None,
                "error": structured_res.validation_error or structured_res.provider_error,
            },
        },
    }
    print(json.dumps(report, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="repo-triage-minion",
        description="Local-first repository QA & triage agent built on the OpenMinion 0.1 Python SDK.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_triage = sub.add_parser("triage", help="Run a triage turn on a local repository.")
    p_triage.add_argument("repo_path", help="Path to the local repository to inspect.")
    p_triage.add_argument("--config", default=None, help="Path to OpenMinion agents.json.")
    p_triage.add_argument("--agent", default=None, help="Configured agent id in agents.json.")
    p_triage.add_argument("--model", default=None, help="Optional model override.")
    p_triage.add_argument("--session", default="repo-triage-session", help="Session ID.")
    p_triage.add_argument("--structured", action="store_true", help="Request Pydantic TriageReport JSON.")
    p_triage.add_argument("--model-choice", action="store_true", help="Let the model choose tools instead of forcing.")
    p_triage.add_argument("--stream", action="store_true", help="Use Agent.run_stream() and count progress events.")
    p_triage.add_argument("--verbose-stream", action="store_true", help="Print every stream event to stderr.")
    p_triage.add_argument("--followup", default=None, help="Optional second-turn question in the same session.")
    p_triage.set_defaults(func=_cmd_triage)

    p_verify = sub.add_parser(
        "verify-blocks",
        help="Exercise OpenMinion tools, sessions, isolation, streaming, and structured output.",
    )
    p_verify.add_argument("repo_path", help="Path to the target repository.")
    p_verify.add_argument("--config", default=None, help="Path to OpenMinion agents.json.")
    p_verify.add_argument("--agent", default=None, help="Configured agent id.")
    p_verify.add_argument("--model", default=None, help="Optional model override.")
    p_verify.add_argument("--session", default="verify-blocks", help="Session prefix.")
    p_verify.set_defaults(func=_cmd_verify_blocks)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
