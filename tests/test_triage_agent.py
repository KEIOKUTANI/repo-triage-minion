"""Automated tests for RepoTriage Minion tools and OpenMinion 0.1 SDK integration."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from repo_triage_minion.agent import RepoTriageRunner, collect_local_snapshot
from repo_triage_minion.tools import check_release_hygiene, find_code_markers, scan_repository_structure

SAMPLE_REPO = Path(__file__).resolve().parent.parent / "sample_target_repo"


class TestLocalTools(unittest.TestCase):
    def test_scan_repository_structure(self) -> None:
        data = json.loads(scan_repository_structure(str(SAMPLE_REPO)))
        self.assertEqual(data["repo_name"], "sample_target_repo")
        self.assertGreaterEqual(data["python_files"], 1)

    def test_find_code_markers_and_secret_hints(self) -> None:
        data = json.loads(find_code_markers(str(SAMPLE_REPO)))
        self.assertGreaterEqual(data["marker_count"], 3)
        self.assertEqual(data["secret_hint_count"], 1)

    def test_check_release_hygiene(self) -> None:
        data = json.loads(check_release_hygiene(str(SAMPLE_REPO)))
        self.assertTrue(data["checks"]["has_readme"])
        self.assertIn("has_license", data["missing"])
        self.assertIn("has_tests", data["missing"])


class TestOpenMinionIntegration(unittest.TestCase):
    def test_echo_provider_session_and_structured_error_handling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            cfg_path = tmp_path / "agents.json"
            cfg_path.write_text(
                json.dumps(
                    {
                        "default_agent": "triage-echo",
                        "agents": {
                            "triage-echo": {
                                "name": "triage-echo",
                                "default_channel": "console",
                                "provider": "echo",
                                "model": "echo-1",
                            }
                        },
                    }
                ),
                encoding="utf-8",
            )

            old_home = os.environ.get("OPENMINION_HOME")
            old_data = os.environ.get("OPENMINION_DATA_ROOT")
            os.environ["OPENMINION_HOME"] = str(tmp_path)
            os.environ["OPENMINION_DATA_ROOT"] = str(tmp_path / ".openminion")
            try:
                runner = RepoTriageRunner(
                    config_path=str(cfg_path),
                    agent_id="triage-echo",
                    session_id="unit-test-session",
                )
                first = runner.run_triage(str(SAMPLE_REPO), structured=False, force_initial_tools=True)
                self.assertIsNone(first.provider_error)
                self.assertEqual(first.session_id, "unit-test-session")
                self.assertTrue(len(first.text) > 0)

                isolated = runner.run_followup("Check isolated session", isolated_session_id="unit-test-isolated")
                self.assertIsNone(isolated.provider_error)
                self.assertEqual(isolated.session_id, "unit-test-isolated")

                # Under echo provider, non-JSON output should cleanly raise and be captured as validation_error
                structured = runner.run_triage(str(SAMPLE_REPO), structured=True, force_initial_tools=False)
                self.assertIsNotNone(structured.validation_error)

                snapshot = collect_local_snapshot(str(SAMPLE_REPO))
                self.assertEqual(snapshot["markers"]["secret_hint_count"], 1)
            finally:
                if old_home is None:
                    os.environ.pop("OPENMINION_HOME", None)
                else:
                    os.environ["OPENMINION_HOME"] = old_home
                if old_data is None:
                    os.environ.pop("OPENMINION_DATA_ROOT", None)
                else:
                    os.environ["OPENMINION_DATA_ROOT"] = old_data


if __name__ == "__main__":
    unittest.main()
