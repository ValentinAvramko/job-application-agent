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
    def test_list_workflows_excludes_bootstrap_setup_command(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f"cli-list-{uuid.uuid4().hex}"
        workspace_dir.mkdir(parents=True, exist_ok=True)
        stdout = io.StringIO()

        with patch.object(
            sys,
            "argv",
            [
                "run_agent.py",
                "--root",
                str(workspace_dir),
                "list-workflows",
            ],
        ), patch("sys.stdout", new=stdout):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(
            [item["name"] for item in payload],
            [
                "analyze-vacancy",
                "build-linkedin",
                "export-resume-pdf",
                "ingest-vacancy",
                "intake-adoptions",
                "prepare-screening",
                "rebuild-master",
                "rebuild-role-resume",
            ],
        )

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

    def test_prepare_screening_cli_routes_to_prepare_workflow(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f"cli-prepare-{uuid.uuid4().hex}"
        workspace_dir.mkdir(parents=True, exist_ok=True)

        result = WorkflowResult(
            workflow="prepare-screening",
            status="completed",
            summary="Prepared screening package for vacancy 20260421-example-role.",
            artifacts=[str(workspace_dir / "vacancies" / "20260421-example-role" / "screening.md")],
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
                "prepare-screening",
                "--vacancy-id",
                "20260421-example-role",
                "--selected-resume",
                "CTO",
                "--output-language",
                "ru",
                "--preparation-depth",
                "deep",
            ],
        ), patch("sys.stdout", new=stdout):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(registry.requested, ["prepare-screening"])
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["workflow"], "prepare-screening")
        self.assertIn("screening", payload["summary"])

    def test_intake_adoptions_cli_routes_to_intake_workflow(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f"cli-intake-{uuid.uuid4().hex}"
        workspace_dir.mkdir(parents=True, exist_ok=True)

        result = WorkflowResult(
            workflow="intake-adoptions",
            status="completed",
            summary="Prepared adoptions intake for vacancy 20260421-example-role.",
            artifacts=[str(workspace_dir / "adoptions" / "inbox" / "20260421-example-role.md")],
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
                "intake-adoptions",
                "--vacancy-id",
                "20260421-example-role",
            ],
        ), patch("sys.stdout", new=stdout):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(registry.requested, ["intake-adoptions"])
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["workflow"], "intake-adoptions")
        self.assertIn("intake", payload["summary"])

    def test_rebuild_master_cli_routes_to_rebuild_workflow(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f"cli-rebuild-{uuid.uuid4().hex}"
        workspace_dir.mkdir(parents=True, exist_ok=True)

        result = WorkflowResult(
            workflow="rebuild-master",
            status="completed",
            summary="Rebuilt MASTER approved-signals section.",
            artifacts=[str(workspace_dir / "resumes" / "MASTER.md")],
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
                "rebuild-master",
            ],
        ), patch("sys.stdout", new=stdout):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(registry.requested, ["rebuild-master"])
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["workflow"], "rebuild-master")
        self.assertIn("MASTER", payload["summary"])

    def test_rebuild_role_resume_cli_routes_to_rebuild_role_workflow(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f"cli-rebuild-role-{uuid.uuid4().hex}"
        workspace_dir.mkdir(parents=True, exist_ok=True)

        result = WorkflowResult(
            workflow="rebuild-role-resume",
            status="completed",
            summary="Rebuilt CTO role resume managed block.",
            artifacts=[str(workspace_dir / "resumes" / "CTO.md")],
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
                "rebuild-role-resume",
                "--target-role",
                "CTO",
            ],
        ), patch("sys.stdout", new=stdout):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(registry.requested, ["rebuild-role-resume"])
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["workflow"], "rebuild-role-resume")
        self.assertIn("CTO", payload["summary"])

    def test_build_linkedin_cli_routes_to_workflow(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f"cli-build-linkedin-{uuid.uuid4().hex}"
        workspace_dir.mkdir(parents=True, exist_ok=True)

        result = WorkflowResult(
            workflow="build-linkedin",
            status="completed",
            summary="Built LinkedIn draft pack for CTO.",
            artifacts=[str(workspace_dir / "profile" / "linkedin" / "CTO.md")],
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
                "build-linkedin",
                "--target-role",
                "CTO",
            ],
        ), patch("sys.stdout", new=stdout):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(registry.requested, ["build-linkedin"])
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["workflow"], "build-linkedin")
        self.assertIn("LinkedIn", payload["summary"])

    def test_export_resume_pdf_cli_routes_to_workflow(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f"cli-export-resume-pdf-{uuid.uuid4().hex}"
        workspace_dir.mkdir(parents=True, exist_ok=True)

        result = WorkflowResult(
            workflow="export-resume-pdf",
            status="completed",
            summary="Exported resume PDF for CTO.",
            artifacts=[str(workspace_dir / "profile" / "pdf" / "CTO" / "ru-EU.pdf")],
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
                "export-resume-pdf",
                "--target-resume",
                "CTO",
                "--output-language",
                "ru",
                "--contact-region",
                "EU",
                "--template-id",
                "default",
            ],
        ), patch("sys.stdout", new=stdout):
            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(registry.requested, ["export-resume-pdf"])
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["workflow"], "export-resume-pdf")
        self.assertIn("PDF", payload["summary"])
if __name__ == "__main__":
    unittest.main()
