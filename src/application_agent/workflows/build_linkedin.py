from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from application_agent.linkedin_builder import BuildLinkedInComputation, apply_build_linkedin_projection
from application_agent.memory.models import WorkflowRun
from application_agent.memory.store import JsonMemoryStore
from application_agent.workflows.base import WorkflowResult
from application_agent.workflows.rebuild_role_resume import normalize_target_role
from application_agent.workspace import WorkspaceLayout


@dataclass
class BuildLinkedInRequest:
    target_role: str


class BuildLinkedInWorkflow:
    name = "build-linkedin"
    description = "Собирает deterministic LinkedIn draft pack для выбранного role resume и пишет runtime report."

    def run(
        self,
        *,
        layout: WorkspaceLayout,
        store: JsonMemoryStore,
        request: BuildLinkedInRequest,
    ) -> WorkflowResult:
        started_at = datetime.now(timezone.utc).isoformat()
        target_role = normalize_target_role(request.target_role)
        master_path = layout.resumes_dir / "MASTER.md"
        role_resume_path = layout.resumes_dir / f"{target_role}.md"
        profile_metadata_path = layout.profile_dir / "contact-regions.yml"
        output_path = layout.profile_dir / "linkedin" / f"{target_role}.md"
        report_path = layout.runtime_memory_dir / "build-linkedin" / f"{target_role}.md"

        computation = apply_build_linkedin_projection(
            target_role=target_role,
            master_path=master_path,
            role_resume_path=role_resume_path,
            profile_metadata_path=profile_metadata_path,
            output_path=output_path,
        )
        write_runtime_report(
            report_path=report_path,
            target_role=target_role,
            output_path=output_path,
            profile_metadata_path=profile_metadata_path,
            computation=computation,
        )

        artifacts = [str(output_path), str(report_path)]
        summary = build_summary(
            target_role=target_role,
            changed=computation.changed,
            gap_count=count_blocking_gaps(computation.gaps),
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


def build_summary(*, target_role: str, changed: bool, gap_count: int) -> str:
    if not changed:
        return (
            f"LinkedIn draft pack for {target_role} already matches the current resume inputs; "
            f"runtime report refreshed (blocking_gaps={gap_count})."
        )
    return f"Built LinkedIn draft pack for {target_role} (blocking_gaps={gap_count})."


def count_blocking_gaps(gaps: tuple[str, ...]) -> int:
    return sum(1 for gap in gaps if not gap.startswith("OPTIONAL:"))


def write_runtime_report(
    *,
    report_path: Path,
    target_role: str,
    output_path: Path,
    profile_metadata_path: Path,
    computation: BuildLinkedInComputation,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_status = "present" if profile_metadata_path.exists() else "missing"
    lines = [
        f"# build-linkedin runtime report for {target_role}",
        "",
        f"- Artifact path: `{output_path}`",
        f"- Artifact changed: `{'yes' if computation.changed else 'no'}`",
        f"- Profile metadata: `{metadata_status}`",
        f"- Blocking gaps: `{count_blocking_gaps(computation.gaps)}`",
        "",
        "## Inputs",
        "",
        "- `resumes/MASTER.md`",
        f"- `resumes/{target_role}.md`",
        "- `profile/contact-regions.yml` (optional)",
        "",
        "## Executive Summary",
        "",
        *[f"- {item}" for item in computation.executive_summary],
        "",
        "## GAP List",
        "",
        *[f"- {item}" for item in computation.gaps],
        "",
    ]
    report_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
