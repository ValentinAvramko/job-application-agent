from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from application_agent.master_rebuild import (
    MANAGED_SECTION_END,
    MANAGED_SECTION_START,
    apply_rebuild_master_projection,
)
from application_agent.review_state import AcceptedSignal, AcceptedSignalsStore
from application_agent.workspace import WorkspaceLayout


class RebuildMasterHelpersTests(unittest.TestCase):
    def test_missing_accepted_store_is_valid_empty_input_and_no_op(self) -> None:
        workspace_dir, layout = build_workspace("rebuild-master-empty")
        master_path = layout.resumes_dir / "MASTER.md"
        report_path = layout.runtime_memory_dir / "rebuild-master" / "latest.md"
        original_text = master_path.read_text(encoding="utf-8")

        result = apply_rebuild_master_projection(
            master_path=master_path,
            accepted_path=layout.adoptions_dir / "accepted" / "MASTER.md",
            report_path=report_path,
        )

        self.assertFalse(result.changed)
        self.assertEqual(master_path.read_text(encoding="utf-8"), original_text)
        self.assertTrue(report_path.exists())
        report_text = report_path.read_text(encoding="utf-8")
        self.assertIn("- Changed: no", report_text)
        self.assertIn("- Added: 0", report_text)
        self.assertIn("- Removed: 0", report_text)

    def test_projection_inserts_managed_section_and_second_run_is_idempotent(self) -> None:
        workspace_dir, layout = build_workspace("rebuild-master-idempotent")
        master_path = layout.resumes_dir / "MASTER.md"
        accepted_path = layout.adoptions_dir / "accepted" / "MASTER.md"
        report_path = layout.runtime_memory_dir / "rebuild-master" / "latest.md"

        write_accepted_signals(
            accepted_path,
            [
                AcceptedSignal(
                    signal="Leadership of 6 teams through engineering leads",
                    target="MASTER.md",
                    source_vacancy="vacancy-1",
                    rationale="Approved durable leadership signal.",
                    updated_at="2026-04-22T18:10:00+00:00",
                ),
                AcceptedSignal(
                    signal="OpenAI and Codex as working AI tools",
                    target="MASTER.md",
                    source_vacancy="vacancy-2",
                    rationale="Confirmed as reusable AI tooling signal.",
                    updated_at="2026-04-22T18:11:00+00:00",
                ),
            ],
        )

        first = apply_rebuild_master_projection(
            master_path=master_path,
            accepted_path=accepted_path,
            report_path=report_path,
        )
        second = apply_rebuild_master_projection(
            master_path=master_path,
            accepted_path=accepted_path,
            report_path=report_path,
        )

        master_text = master_path.read_text(encoding="utf-8")

        self.assertTrue(first.changed)
        self.assertFalse(second.changed)
        self.assertIn(MANAGED_SECTION_START, master_text)
        self.assertIn(MANAGED_SECTION_END, master_text)
        self.assertIn("## Approved Permanent Signals", master_text)
        self.assertIn("Leadership of 6 teams through engineering leads", master_text)
        self.assertIn("OpenAI and Codex as working AI tools", master_text)
        self.assertLess(master_text.index(MANAGED_SECTION_START), master_text.index("## Рекомендации"))

    def test_projection_reports_added_updated_and_removed_signals(self) -> None:
        workspace_dir, layout = build_workspace("rebuild-master-diff")
        master_path = layout.resumes_dir / "MASTER.md"
        accepted_path = layout.adoptions_dir / "accepted" / "MASTER.md"
        report_path = layout.runtime_memory_dir / "rebuild-master" / "latest.md"
        role_resume_path = layout.resumes_dir / "CIO.md"
        original_role_resume = role_resume_path.read_text(encoding="utf-8")

        write_accepted_signals(
            accepted_path,
            [
                AcceptedSignal(
                    signal="Leadership of 6 teams through engineering leads",
                    target="MASTER.md",
                    source_vacancy="vacancy-1",
                    rationale="Approved durable leadership signal.",
                    updated_at="2026-04-22T18:20:00+00:00",
                ),
                AcceptedSignal(
                    signal="OpenAI and Codex as working AI tools",
                    target="MASTER.md",
                    source_vacancy="vacancy-2",
                    rationale="Confirmed as reusable AI tooling signal.",
                    updated_at="2026-04-22T18:21:00+00:00",
                ),
            ],
        )
        apply_rebuild_master_projection(
            master_path=master_path,
            accepted_path=accepted_path,
            report_path=report_path,
        )

        write_accepted_signals(
            accepted_path,
            [
                AcceptedSignal(
                    signal="Leadership of 6 teams through engineering leads",
                    target="MASTER.md",
                    source_vacancy="vacancy-3",
                    rationale="Refined wording after additional review.",
                    updated_at="2026-04-22T18:30:00+00:00",
                ),
                AcceptedSignal(
                    signal="Built internal RAG prototype with pgvector",
                    target="MASTER.md",
                    source_vacancy="vacancy-4",
                    rationale="Confirmed as reusable product AI signal.",
                    updated_at="2026-04-22T18:31:00+00:00",
                ),
            ],
        )

        result = apply_rebuild_master_projection(
            master_path=master_path,
            accepted_path=accepted_path,
            report_path=report_path,
        )

        master_text = master_path.read_text(encoding="utf-8")
        report_text = report_path.read_text(encoding="utf-8")

        self.assertTrue(result.changed)
        self.assertIn("- Added: 1", report_text)
        self.assertIn("- Updated: 1", report_text)
        self.assertIn("- Removed: 1", report_text)
        self.assertIn("- Unchanged: 0", report_text)
        self.assertIn("Built internal RAG prototype with pgvector", master_text)
        self.assertIn("Refined wording after additional review.", master_text)
        self.assertNotIn("OpenAI and Codex as working AI tools", master_text)
        self.assertEqual(role_resume_path.read_text(encoding="utf-8"), original_role_resume)


def build_workspace(prefix: str) -> tuple[Path, WorkspaceLayout]:
    temp_root = Path(__file__).resolve().parents[1] / ".tmp-tests"
    temp_root.mkdir(exist_ok=True)
    workspace_dir = temp_root / f"{prefix}-{uuid.uuid4().hex}"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    layout = WorkspaceLayout(workspace_dir)
    layout.bootstrap()
    write_resume(layout.resumes_dir / "MASTER.md")
    (layout.resumes_dir / "CIO.md").write_text("# CIO\n", encoding="utf-8", newline="\n")
    return workspace_dir, layout


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
                "## Ключевые компетенции",
                "",
                "- Existing leadership signal.",
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
