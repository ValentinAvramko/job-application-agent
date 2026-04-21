from __future__ import annotations

import sys
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from application_agent.cli import autopush_ingest_artifacts, build_ingest_commit_message, extract_vacancy_id_from_artifacts


class CliTests(unittest.TestCase):
    def test_extract_vacancy_id_from_artifacts(self) -> None:
        artifacts = [
            r"C:\workspace\vacancies\20260421-example-role\meta.yml",
            r"C:\workspace\vacancies\20260421-example-role\source.md",
        ]

        self.assertEqual(extract_vacancy_id_from_artifacts(artifacts), "20260421-example-role")

    def test_build_ingest_commit_message(self) -> None:
        self.assertEqual(build_ingest_commit_message("20260421-example-role"), "Ingest vacancy 20260421-example-role")

    def test_autopush_ingest_artifacts_stages_only_workflow_outputs(self) -> None:
        repo_root = Path(r"C:\workspace")
        artifacts = [
            str(repo_root / "vacancies" / "20260421-example-role" / "meta.yml"),
            str(repo_root / "vacancies" / "20260421-example-role" / "source.md"),
            str(repo_root / "vacancies" / "20260421-example-role" / "analysis.md"),
            str(repo_root / "vacancies" / "20260421-example-role" / "adoptions.md"),
            str(repo_root / "response-monitoring.xlsx"),
        ]
        git_calls: list[list[str]] = []

        def fake_git_command(_repo_root: Path, args: list[str]) -> CompletedProcess[str]:
            git_calls.append(args)
            if args[:2] == ["branch", "--show-current"]:
                return CompletedProcess(["git", *args], 0, stdout="main\n", stderr="")
            return CompletedProcess(["git", *args], 0, stdout="", stderr="")

        with patch("application_agent.cli.run_git_command", side_effect=fake_git_command):
            commit_message = autopush_ingest_artifacts(repo_root, artifacts)

        self.assertEqual(commit_message, "Ingest vacancy 20260421-example-role")
        self.assertEqual(
            git_calls,
            [
                [
                    "add",
                    "--",
                    "vacancies\\20260421-example-role\\meta.yml",
                    "vacancies\\20260421-example-role\\source.md",
                    "vacancies\\20260421-example-role\\analysis.md",
                    "vacancies\\20260421-example-role\\adoptions.md",
                    "response-monitoring.xlsx",
                ],
                ["commit", "-m", "Ingest vacancy 20260421-example-role"],
                ["branch", "--show-current"],
                ["push", "origin", "main"],
            ],
        )


if __name__ == "__main__":
    unittest.main()
