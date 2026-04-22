from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from application_agent.config import ROLE_RESUMES
from application_agent.memory.models import WorkflowRun
from application_agent.memory.store import JsonMemoryStore
from application_agent.review_state import normalize_text
from application_agent.role_resume_rebuild import apply_rebuild_role_resume_projection
from application_agent.workflows.base import WorkflowResult
from application_agent.workspace import WorkspaceLayout


@dataclass
class RebuildRoleResumeRequest:
    target_role: str


class RebuildRoleResumeWorkflow:
    name = "rebuild-role-resume"
    description = "Синхронизирует managed canonical block в выбранном role resume из MASTER и optional role signals."

    def run(
        self,
        *,
        layout: WorkspaceLayout,
        store: JsonMemoryStore,
        request: RebuildRoleResumeRequest,
    ) -> WorkflowResult:
        started_at = datetime.now(timezone.utc).isoformat()
        target_role = normalize_target_role(request.target_role)
        master_path = layout.resumes_dir / "MASTER.md"
        role_resume_path = layout.resumes_dir / f"{target_role}.md"
        role_signal_path = layout.knowledge_dir / "roles" / f"{target_role}.md"
        report_path = layout.runtime_memory_dir / "rebuild-role-resume" / f"{target_role}.md"

        computation = apply_rebuild_role_resume_projection(
            target_role=target_role,
            master_path=master_path,
            role_resume_path=role_resume_path,
            role_signal_path=role_signal_path,
            report_path=report_path,
        )

        artifacts = [str(role_resume_path), str(report_path)]
        summary = build_summary(
            target_role=target_role,
            changed=computation.changed,
            added_master_count=len(computation.added_master_signals),
            updated_master_count=len(computation.updated_master_signals),
            removed_master_count=len(computation.removed_master_signals),
            added_role_count=len(computation.added_role_signals),
            removed_role_count=len(computation.removed_role_signals),
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


def normalize_target_role(target_role: str) -> str:
    value = normalize_text(target_role)
    if value.lower().endswith(".md"):
        value = value[:-3]
    mapping = {role.lower(): role for role in ROLE_RESUMES}
    resolved = mapping.get(value.lower())
    if resolved is None:
        known = ", ".join(ROLE_RESUMES)
        raise ValueError(f"Unknown target_role '{target_role}'. Expected one of: {known}.")
    return resolved


def build_summary(
    *,
    target_role: str,
    changed: bool,
    added_master_count: int,
    updated_master_count: int,
    removed_master_count: int,
    added_role_count: int,
    removed_role_count: int,
) -> str:
    if not changed:
        return (
            f"{target_role} resume already matches the current MASTER-managed signals and role shaping layer; "
            "runtime report refreshed."
        )
    return (
        f"Rebuilt {target_role} role resume managed block "
        f"(master_added={added_master_count}, master_updated={updated_master_count}, master_removed={removed_master_count}, "
        f"role_added={added_role_count}, role_removed={removed_role_count})."
    )
