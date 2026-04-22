from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from application_agent.master_rebuild import apply_rebuild_master_projection
from application_agent.review_state import AcceptedSignal, AcceptedSignalsStore
from application_agent.role_resume_rebuild import (
    MANAGED_SECTION_END,
    MANAGED_SECTION_START,
    apply_rebuild_role_resume_projection,
)
from application_agent.workspace import WorkspaceLayout


class RebuildRoleResumeHelpersTests(unittest.TestCase):
    def test_projection_syncs_master_signals_without_role_knowledge_and_is_idempotent(self) -> None:
        workspace_dir, layout = build_workspace("rebuild-role-idempotent")
        prepare_master_with_signals(
            layout,
            [
                AcceptedSignal(
                    signal="Leadership of 6 teams through engineering leads",
                    target="MASTER.md",
                    source_vacancy="vacancy-1",
                    rationale="Approved durable leadership signal.",
                    updated_at="2026-04-22T19:10:00+00:00",
                )
            ],
        )

        role_resume_path = layout.resumes_dir / "CTO.md"
        report_path = layout.runtime_memory_dir / "rebuild-role-resume" / "CTO.md"
        original_intro = "# CTO Resume"

        first = apply_rebuild_role_resume_projection(
            target_role="CTO",
            master_path=layout.resumes_dir / "MASTER.md",
            role_resume_path=role_resume_path,
            role_signal_path=layout.knowledge_dir / "roles" / "CTO.md",
            report_path=report_path,
        )
        second = apply_rebuild_role_resume_projection(
            target_role="CTO",
            master_path=layout.resumes_dir / "MASTER.md",
            role_resume_path=role_resume_path,
            role_signal_path=layout.knowledge_dir / "roles" / "CTO.md",
            report_path=report_path,
        )

        role_resume_text = role_resume_path.read_text(encoding="utf-8")
        report_text = report_path.read_text(encoding="utf-8")

        self.assertTrue(first.changed)
        self.assertFalse(second.changed)
        self.assertIn(original_intro, role_resume_text)
        self.assertIn(MANAGED_SECTION_START, role_resume_text)
        self.assertIn(MANAGED_SECTION_END, role_resume_text)
        self.assertIn("Leadership of 6 teams through engineering leads", role_resume_text)
        self.assertIn("- Target Role: CTO", report_text)
        self.assertIn("- Role Signals Added: 0", report_text)
        self.assertLess(role_resume_text.index(MANAGED_SECTION_START), role_resume_text.index("## Рекомендации"))

    def test_projection_reports_master_and_role_signal_diffs_and_preserves_unmanaged_text(self) -> None:
        workspace_dir, layout = build_workspace("rebuild-role-diff")
        prepare_master_with_signals(
            layout,
            [
                AcceptedSignal(
                    signal="OpenAI and Codex as working AI tools",
                    target="MASTER.md",
                    source_vacancy="vacancy-1",
                    rationale="Confirmed as reusable AI tooling signal.",
                    updated_at="2026-04-22T19:20:00+00:00",
                ),
                AcceptedSignal(
                    signal="Leadership of 6 teams through engineering leads",
                    target="MASTER.md",
                    source_vacancy="vacancy-2",
                    rationale="Approved durable leadership signal.",
                    updated_at="2026-04-22T19:21:00+00:00",
                ),
            ],
        )
        role_signal_path = layout.knowledge_dir / "roles" / "HoE.md"
        role_signal_path.write_text(
            "# HoE Signals\n\n- Platform engineering leadership\n",
            encoding="utf-8",
            newline="\n",
        )

        role_resume_path = layout.resumes_dir / "HoE.md"
        original_unmanaged_line = "Existing role-specific narrative."
        report_path = layout.runtime_memory_dir / "rebuild-role-resume" / "HoE.md"

        apply_rebuild_role_resume_projection(
            target_role="HoE",
            master_path=layout.resumes_dir / "MASTER.md",
            role_resume_path=role_resume_path,
            role_signal_path=role_signal_path,
            report_path=report_path,
        )

        prepare_master_with_signals(
            layout,
            [
                AcceptedSignal(
                    signal="Leadership of 6 teams through engineering leads",
                    target="MASTER.md",
                    source_vacancy="vacancy-3",
                    rationale="Refined after additional review.",
                    updated_at="2026-04-22T19:30:00+00:00",
                ),
                AcceptedSignal(
                    signal="Built internal RAG prototype with pgvector",
                    target="MASTER.md",
                    source_vacancy="vacancy-4",
                    rationale="Confirmed as reusable product AI signal.",
                    updated_at="2026-04-22T19:31:00+00:00",
                ),
            ],
        )
        role_signal_path.write_text(
            "# HoE Signals\n\n- Engineering excellence and delivery systems\n",
            encoding="utf-8",
            newline="\n",
        )

        result = apply_rebuild_role_resume_projection(
            target_role="HoE",
            master_path=layout.resumes_dir / "MASTER.md",
            role_resume_path=role_resume_path,
            role_signal_path=role_signal_path,
            report_path=report_path,
        )

        role_resume_text = role_resume_path.read_text(encoding="utf-8")
        report_text = report_path.read_text(encoding="utf-8")

        self.assertTrue(result.changed)
        self.assertIn(original_unmanaged_line, role_resume_text)
        self.assertIn("Built internal RAG prototype with pgvector", role_resume_text)
        self.assertIn("Engineering excellence and delivery systems", role_resume_text)
        self.assertNotIn("OpenAI and Codex as working AI tools", role_resume_text)
        self.assertNotIn("Platform engineering leadership", role_resume_text)
        self.assertIn("- Master Signals Added: 1", report_text)
        self.assertIn("- Master Signals Updated: 1", report_text)
        self.assertIn("- Master Signals Removed: 1", report_text)
        self.assertIn("- Role Signals Added: 1", report_text)
        self.assertIn("- Role Signals Removed: 1", report_text)


def build_workspace(prefix: str) -> tuple[Path, WorkspaceLayout]:
    temp_root = Path(__file__).resolve().parents[1] / ".tmp-tests"
    temp_root.mkdir(exist_ok=True)
    workspace_dir = temp_root / f"{prefix}-{uuid.uuid4().hex}"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    layout = WorkspaceLayout(workspace_dir)
    layout.bootstrap()
    write_master_resume(layout.resumes_dir / "MASTER.md")
    write_role_resume(layout.resumes_dir / "CTO.md", "CTO Resume")
    write_role_resume(layout.resumes_dir / "HoE.md", "HoE Resume")
    return workspace_dir, layout


def write_master_resume(path: Path) -> None:
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


def write_role_resume(path: Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                f"# {title}",
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


def prepare_master_with_signals(layout: WorkspaceLayout, signals: list[AcceptedSignal]) -> None:
    accepted_path = layout.adoptions_dir / "accepted" / "MASTER.md"
    report_path = layout.runtime_memory_dir / "rebuild-master" / "latest.md"
    store = AcceptedSignalsStore()
    for signal in signals:
        store.upsert(signal)
    store.write(accepted_path)
    apply_rebuild_master_projection(
        master_path=layout.resumes_dir / "MASTER.md",
        accepted_path=accepted_path,
        report_path=report_path,
    )


if __name__ == "__main__":
    unittest.main()
