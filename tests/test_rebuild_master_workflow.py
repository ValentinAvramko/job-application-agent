from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from application_agent.memory.store import JsonMemoryStore
from application_agent.review_state import AcceptedSignal, AcceptedSignalsStore
from application_agent.workflows.rebuild_master import RebuildMasterRequest, RebuildMasterWorkflow
from application_agent.workspace import WorkspaceLayout


class RebuildMasterWorkflowTests(unittest.TestCase):
    def test_workflow_updates_master_and_runtime_report_without_touching_role_resumes(self) -> None:
        workspace_dir, layout, store = build_workspace("rebuild-master-workflow")
        accepted_path = layout.adoptions_dir / "accepted" / "MASTER.md"
        role_resume_path = layout.resumes_dir / "CTO.md"
        original_role_resume = role_resume_path.read_text(encoding="utf-8")

        write_accepted_signals(
            accepted_path,
            [
                AcceptedSignal(
                    signal="Leadership of 6 teams through engineering leads",
                    target="MASTER.md",
                    source_vacancy="vacancy-1",
                    rationale="Approved durable leadership signal.",
                    updated_at="2026-04-22T18:40:00+00:00",
                )
            ],
        )

        result = RebuildMasterWorkflow().run(layout=layout, store=store, request=RebuildMasterRequest())

        master_text = (layout.resumes_dir / "MASTER.md").read_text(encoding="utf-8")
        report_path = layout.runtime_memory_dir / "rebuild-master" / "latest.md"
        snapshot = store.snapshot()

        self.assertEqual(result.workflow, "rebuild-master")
        self.assertEqual(result.status, "completed")
        self.assertIn("added=1", result.summary)
        self.assertIn("Leadership of 6 teams through engineering leads", master_text)
        self.assertTrue(report_path.exists())
        self.assertEqual(role_resume_path.read_text(encoding="utf-8"), original_role_resume)
        self.assertEqual(snapshot["task_memory"]["active_workflow"], "rebuild-master")
        self.assertIsNone(snapshot["task_memory"]["active_vacancy_id"])
        self.assertIn(str(report_path), snapshot["task_memory"]["active_artifacts"])
        self.assertEqual(snapshot["workflow_runs"][-1]["workflow"], "rebuild-master")

    def test_workflow_no_op_when_master_already_matches_current_signals(self) -> None:
        workspace_dir, layout, store = build_workspace("rebuild-master-noop")
        accepted_path = layout.adoptions_dir / "accepted" / "MASTER.md"

        write_accepted_signals(
            accepted_path,
            [
                AcceptedSignal(
                    signal="OpenAI and Codex as working AI tools",
                    target="MASTER.md",
                    source_vacancy="vacancy-2",
                    rationale="Confirmed as reusable AI tooling signal.",
                    updated_at="2026-04-22T18:41:00+00:00",
                )
            ],
        )

        workflow = RebuildMasterWorkflow()
        first = workflow.run(layout=layout, store=store, request=RebuildMasterRequest())
        second = workflow.run(layout=layout, store=store, request=RebuildMasterRequest())

        self.assertIn("added=1", first.summary)
        self.assertIn("already matches", second.summary)


def build_workspace(prefix: str) -> tuple[Path, WorkspaceLayout, JsonMemoryStore]:
    temp_root = Path(__file__).resolve().parents[1] / ".tmp-tests"
    temp_root.mkdir(exist_ok=True)
    workspace_dir = temp_root / f"{prefix}-{uuid.uuid4().hex}"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    layout = WorkspaceLayout(workspace_dir)
    layout.bootstrap()
    write_resume(layout.resumes_dir / "MASTER.md")
    (layout.resumes_dir / "CTO.md").write_text("# CTO\n", encoding="utf-8", newline="\n")
    store = JsonMemoryStore(layout)
    store.bootstrap()
    return workspace_dir, layout, store


def write_resume(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# Candidate",
                "",
                "## О себе",
                "",
                "- Existing profile summary.",
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


def write_accepted_signals(path: Path, signals: list[AcceptedSignal]) -> None:
    store = AcceptedSignalsStore()
    for signal in signals:
        store.upsert(signal)
    store.write(path)


if __name__ == "__main__":
    unittest.main()
