from __future__ import annotations

import io
import json
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from application_agent.cli import main
from application_agent.workflows.base import WorkflowResult


class _FakeRegistry:
    def __init__(self, result: WorkflowResult) -> None:
        self._result = result
        self.requested: list[str] = []

    def get(self, name: str):
        self.requested.append(name)

        class _FakeWorkflow:
            def __init__(self, result: WorkflowResult) -> None:
                self._result = result

            def run(self, **_: object) -> WorkflowResult:
                return self._result

        return _FakeWorkflow(self._result)


class CliTests(unittest.TestCase):
    def test_ingest_cli_returns_workflow_result_without_git_publication_suffix(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f"cli-ingest-{uuid.uuid4().hex}"
        workspace_dir.mkdir(parents=True, exist_ok=True)

        result = WorkflowResult(
            workflow="ingest-vacancy",
            status="completed",
            summary="Создан каркас вакансии 20260421-example-role.",
            artifacts=[str(workspace_dir / "vacancies" / "20260421-example-role" / "meta.yml")],
        )
        registry = _FakeRegistry(result)
        stdout = io.StringIO()

        with patch("application_agent.cli.build_default_registry", return_value=registry), patch.object(
            sys,
            "argv",
            [
                "run_agent.py",
                "--root",
                str(workspace_dir),
                "ingest-vacancy",
                "--company",
                "Example",
                "--position",
                "Role",
                "--source-text",
                "Example vacancy text",
            ],
        ), patch("sys.stdout", new=stdout):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(registry.requested, ["ingest-vacancy"])
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["summary"], "Создан каркас вакансии 20260421-example-role.")
        self.assertNotIn("git commit", payload["summary"])
        self.assertNotIn("git push", payload["summary"])


if __name__ == "__main__":
    unittest.main()
