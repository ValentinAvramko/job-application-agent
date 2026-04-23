from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from application_agent.memory.store import JsonMemoryStore
from application_agent.workflows.build_linkedin import BuildLinkedInRequest, BuildLinkedInWorkflow
from application_agent.workspace import WorkspaceLayout


class BuildLinkedInWorkflowTests(unittest.TestCase):
    def test_workflow_writes_only_profile_artifact_and_runtime_report(self) -> None:
        workspace_dir, layout, store = build_workspace("build-linkedin-workflow")
        master_path = layout.resumes_dir / "MASTER.md"
        role_resume_path = layout.resumes_dir / "CTO.md"
        other_role_resume_path = layout.resumes_dir / "EM.md"
        original_master = master_path.read_text(encoding="utf-8")
        original_role_resume = role_resume_path.read_text(encoding="utf-8")
        original_other_resume = other_role_resume_path.read_text(encoding="utf-8")

        result = BuildLinkedInWorkflow().run(
            layout=layout,
            store=store,
            request=BuildLinkedInRequest(target_role="cto"),
        )

        output_path = layout.profile_dir / "linkedin" / "CTO.md"
        report_path = layout.runtime_memory_dir / "build-linkedin" / "CTO.md"
        artifact = output_path.read_text(encoding="utf-8")
        report = report_path.read_text(encoding="utf-8")
        snapshot = store.snapshot()

        self.assertEqual(result.workflow, "build-linkedin")
        self.assertEqual(result.status, "completed")
        self.assertIn("CTO", result.summary)
        self.assertTrue(output_path.exists())
        self.assertTrue(report_path.exists())
        self.assertIn("# LinkedIn Draft Pack for CTO", artifact)
        self.assertIn("blocking_gaps=", result.summary)
        self.assertIn("Artifact path:", report)
        self.assertIn("Profile metadata: `present`", report)
        self.assertEqual(master_path.read_text(encoding="utf-8"), original_master)
        self.assertEqual(role_resume_path.read_text(encoding="utf-8"), original_role_resume)
        self.assertEqual(other_role_resume_path.read_text(encoding="utf-8"), original_other_resume)
        self.assertEqual(snapshot["task_memory"]["active_workflow"], "build-linkedin")
        self.assertIsNone(snapshot["task_memory"]["active_vacancy_id"])
        self.assertEqual(snapshot["task_memory"]["active_artifacts"], [str(output_path), str(report_path)])
        self.assertEqual(snapshot["workflow_runs"][-1]["workflow"], "build-linkedin")

    def test_workflow_rejects_unknown_role(self) -> None:
        workspace_dir, layout, store = build_workspace("build-linkedin-invalid")

        with self.assertRaisesRegex(ValueError, "Unknown target_role"):
            BuildLinkedInWorkflow().run(
                layout=layout,
                store=store,
                request=BuildLinkedInRequest(target_role="VP"),
            )


def build_workspace(prefix: str) -> tuple[Path, WorkspaceLayout, JsonMemoryStore]:
    temp_root = Path(__file__).resolve().parents[1] / ".tmp-tests"
    temp_root.mkdir(exist_ok=True)
    workspace_dir = temp_root / f"{prefix}-{uuid.uuid4().hex}"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    layout = WorkspaceLayout(workspace_dir)
    layout.bootstrap()
    write_master_resume(layout.resumes_dir / "MASTER.md")
    write_cto_resume(layout.resumes_dir / "CTO.md")
    write_em_resume(layout.resumes_dir / "EM.md")
    write_profile_metadata(layout.profile_dir / "contact-regions.yml")
    store = JsonMemoryStore(layout)
    store.bootstrap()
    return workspace_dir, layout, store


def write_master_resume(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "---",
                "full_name:",
                '  ru: "Валентин Аврамко"',
                '  eu: "Valentin Avramko"',
                "location:",
                '  ru: "Краснодар, Россия"',
                '  eu: "Bilbao, Spain"',
                "contacts:",
                '  email: "private@example.com"',
                '  phone: "+34 699 00 11 22"',
                "links:",
                '  linkedin: "https://linkedin.com/in/Avramko"',
                "---",
                "",
                "# Валентин Аврамко - Executive Profile",
                "",
                "## О себе",
                "",
                "Руковожу архитектурой, delivery и инженерными командами.",
                "",
                "## Ключевые достижения",
                "",
                "- Built internal RAG prototype with pgvector",
                "- Improved delivery metrics through CI/CD discipline",
                "",
                "## Опыт работы",
                "",
                "### Free2Trip",
                "",
                "**CTO**",
                "",
                "- Led architecture and product delivery.",
                "",
                "## Рекомендации",
                "",
                "References available on request.",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )


def write_cto_resume(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# Валентин Аврамко - Технический директор",
                "",
                "## О себе",
                "",
                "Технический директор с опытом управления инженерными командами и delivery.",
                "",
                "## Ключевые акценты",
                "",
                "- Platform engineering and delivery systems",
                "- Executive stakeholder management",
                "",
                "## Технологии и инструменты",
                "",
                "- OpenAI",
                "- PostgreSQL",
                "",
                "## Опыт работы",
                "",
                "### Free2Trip",
                "",
                "**CTO**",
                "",
                "- Own product architecture and delivery.",
                "",
                "## Рекомендации",
                "",
                "References available on request.",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )


def write_em_resume(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# Валентин Аврамко - Engineering Manager",
                "",
                "## О себе",
                "",
                "Руковожу инженерной командой и улучшаю процессы поставки изменений.",
                "",
                "## Рекомендации",
                "",
                "References available on request.",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )


def write_profile_metadata(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "public_name:",
                '  ru: "Валентин Аврамко"',
                '  eu: "Valentin Avramko"',
                "public_location:",
                '  ru: "Краснодар"',
                '  eu: "Bilbao, Spain"',
                "links:",
                '  linkedin: "https://linkedin.com/in/valentin-avramko"',
                "contacts:",
                '  email: "public@example.com"',
                '  phone: "+34 600 11 22 33"',
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    unittest.main()
