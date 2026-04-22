from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from application_agent.memory.store import JsonMemoryStore
from application_agent.review_state import AcceptedSignal, AcceptedSignalsStore
from application_agent.workflows.rebuild_master import RebuildMasterRequest, RebuildMasterWorkflow
from application_agent.workflows.rebuild_role_resume import RebuildRoleResumeRequest, RebuildRoleResumeWorkflow
from application_agent.workspace import WorkspaceLayout


class RebuildRoleResumeWorkflowTests(unittest.TestCase):
    def test_workflow_updates_only_selected_role_resume_and_runtime_report(self) -> None:
        workspace_dir, layout, store = build_workspace("rebuild-role-workflow")
        prepare_master(layout, store)
        other_role_resume_path = layout.resumes_dir / "CIO.md"
        original_other_resume = other_role_resume_path.read_text(encoding="utf-8")

        role_signal_path = layout.knowledge_dir / "roles" / "CTO.md"
        role_signal_path.write_text(
            "# CTO Signals\n\n- Architecture ownership and platform strategy\n",
            encoding="utf-8",
            newline="\n",
        )

        result = RebuildRoleResumeWorkflow().run(
            layout=layout,
            store=store,
            request=RebuildRoleResumeRequest(target_role="cto"),
        )

        target_resume_text = (layout.resumes_dir / "CTO.md").read_text(encoding="utf-8")
        report_path = layout.runtime_memory_dir / "rebuild-role-resume" / "CTO.md"
        snapshot = store.snapshot()

        self.assertEqual(result.workflow, "rebuild-role-resume")
        self.assertEqual(result.status, "completed")
        self.assertIn("CTO", result.summary)
        self.assertIn("Architecture ownership and platform strategy", target_resume_text)
        self.assertIn("Leadership of 6 teams through engineering leads", target_resume_text)
        self.assertTrue(report_path.exists())
        self.assertEqual(other_role_resume_path.read_text(encoding="utf-8"), original_other_resume)
        self.assertEqual(snapshot["task_memory"]["active_workflow"], "rebuild-role-resume")
        self.assertIsNone(snapshot["task_memory"]["active_vacancy_id"])
        self.assertIn(str(report_path), snapshot["task_memory"]["active_artifacts"])
        self.assertEqual(snapshot["workflow_runs"][-1]["workflow"], "rebuild-role-resume")

    def test_workflow_rejects_unknown_role(self) -> None:
        workspace_dir, layout, store = build_workspace("rebuild-role-invalid")
        prepare_master(layout, store)

        with self.assertRaisesRegex(ValueError, "Unknown target_role"):
            RebuildRoleResumeWorkflow().run(
                layout=layout,
                store=store,
                request=RebuildRoleResumeRequest(target_role="VP"),
            )


def build_workspace(prefix: str) -> tuple[Path, WorkspaceLayout, JsonMemoryStore]:
    temp_root = Path(__file__).resolve().parents[1] / ".tmp-tests"
    temp_root.mkdir(exist_ok=True)
    workspace_dir = temp_root / f"{prefix}-{uuid.uuid4().hex}"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    layout = WorkspaceLayout(workspace_dir)
    layout.bootstrap()
    write_resume(layout.resumes_dir / "MASTER.md", "# Candidate")
    write_resume(layout.resumes_dir / "CTO.md", "# CTO")
    write_resume(layout.resumes_dir / "CIO.md", "# CIO")
    store = JsonMemoryStore(layout)
    store.bootstrap()
    return workspace_dir, layout, store


def write_resume(path: Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                title,
                "",
                "## О себе",
                "",
                "Existing role-specific narrative.",
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


def prepare_master(layout: WorkspaceLayout, store: JsonMemoryStore) -> None:
    accepted_path = layout.adoptions_dir / "accepted" / "MASTER.md"
    accepted_store = AcceptedSignalsStore()
    accepted_store.upsert(
        AcceptedSignal(
            signal="Leadership of 6 teams through engineering leads",
            target="MASTER.md",
            source_vacancy="vacancy-1",
            rationale="Approved durable leadership signal.",
            updated_at="2026-04-22T19:40:00+00:00",
        )
    )
    accepted_store.write(accepted_path)
    RebuildMasterWorkflow().run(layout=layout, store=store, request=RebuildMasterRequest())


if __name__ == "__main__":
    unittest.main()
