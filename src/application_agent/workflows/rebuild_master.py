from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from application_agent.master_rebuild import apply_rebuild_master_projection
from application_agent.memory.models import WorkflowRun
from application_agent.memory.store import JsonMemoryStore
from application_agent.workflows.base import WorkflowResult
from application_agent.workspace import WorkspaceLayout


@dataclass
class RebuildMasterRequest:
    pass


class RebuildMasterWorkflow:
    name = "rebuild-master"
    description = "Обновляет managed approved-signals section в MASTER resume и пишет runtime report."

    def run(self, *, layout: WorkspaceLayout, store: JsonMemoryStore, request: RebuildMasterRequest) -> WorkflowResult:
        started_at = datetime.now(timezone.utc).isoformat()
        master_path = layout.resumes_dir / "MASTER.md"
        accepted_path = layout.adoptions_dir / "accepted" / "MASTER.md"
        report_path = layout.runtime_memory_dir / "rebuild-master" / "latest.md"

        computation = apply_rebuild_master_projection(
            master_path=master_path,
            accepted_path=accepted_path,
            report_path=report_path,
        )

        artifacts = [str(master_path), str(report_path)]
        added_count = len(computation.added_signals)
        updated_count = len(computation.updated_signals)
        removed_count = len(computation.removed_signals)

        summary = build_summary(
            changed=computation.changed,
            added_count=added_count,
            updated_count=updated_count,
            removed_count=removed_count,
        )

        store.remember_task(self.name, None, artifacts)
        store.append_run(
            WorkflowRun(
                workflow=self.name,
                status="completed",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc).isoformat(),
                artifacts=artifacts,
                summary=summary,
            )
        )

        return WorkflowResult(
            workflow=self.name,
            status="completed",
            summary=summary,
            artifacts=artifacts,
        )


def build_summary(*, changed: bool, added_count: int, updated_count: int, removed_count: int) -> str:
    if not changed:
        return "MASTER resume already matches the current approved permanent signals; runtime report refreshed."
    return (
        "Rebuilt MASTER approved-signals section "
        f"(added={added_count}, updated={updated_count}, removed={removed_count})."
    )
