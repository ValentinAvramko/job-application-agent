from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from application_agent.config import CONTACT_REGIONS, ROLE_RESUMES
from application_agent.export_resume_pdf import (
    SUPPORTED_OUTPUT_LANGUAGES,
    SUPPORTED_TEMPLATE_IDS,
    apply_export_resume_pdf_projection,
    load_nested_scalar_map,
)
from application_agent.memory.models import WorkflowRun
from application_agent.memory.store import JsonMemoryStore
from application_agent.review_state import normalize_text
from application_agent.workflows.base import WorkflowResult
from application_agent.workspace import WorkspaceLayout


@dataclass
class ExportResumePdfRequest:
    target_resume: str
    output_language: str = ""
    contact_region: str = ""
    template_id: str = ""


class ExportResumePdfWorkflow:
    name = "export-resume-pdf"
    description = "Рендерит PDF-версию выбранного resume и пишет verification trail в runtime memory."

    def run(
        self,
        *,
        layout: WorkspaceLayout,
        store: JsonMemoryStore,
        request: ExportResumePdfRequest,
    ) -> WorkflowResult:
        started_at = datetime.now(timezone.utc).isoformat()
        target_resume = normalize_target_resume(request.target_resume)
        output_language = normalize_output_language(request.output_language)
        template_id = normalize_template_id(request.template_id)

        profile_metadata_path = layout.profile_dir / "contact-regions.yml"
        contact_region = resolve_contact_region(request.contact_region, profile_metadata_path)
        resume_path = resolve_resume_path(layout=layout, target_resume=target_resume)

        artifact_stem = f"{output_language}-{contact_region}"
        pdf_output_path = layout.profile_dir / "pdf" / target_resume / f"{artifact_stem}.pdf"
        preview_dir = layout.runtime_memory_dir / "export-resume-pdf" / target_resume / artifact_stem
        report_path = preview_dir / "report.md"

        computation = apply_export_resume_pdf_projection(
            target_resume=target_resume,
            output_language=output_language,
            contact_region=contact_region,
            template_id=template_id,
            resume_path=resume_path,
            profile_metadata_path=profile_metadata_path,
            pdf_output_path=pdf_output_path,
            preview_dir=preview_dir,
            report_path=report_path,
        )

        artifacts = [str(pdf_output_path), str(report_path), *[str(path) for path in computation.preview_files]]
        summary = build_summary(
            target_resume=target_resume,
            output_language=output_language,
            contact_region=contact_region,
            template_id=template_id,
            page_count=computation.page_count,
            changed=computation.changed,
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


def normalize_target_resume(target_resume: str) -> str:
    value = normalize_text(target_resume)
    if value.lower().endswith(".md"):
        value = value[:-3]
    if value.upper() == "MASTER":
        return "MASTER"

    mapping = {role.lower(): role for role in ROLE_RESUMES}
    resolved = mapping.get(value.lower())
    if resolved is None:
        known = ", ".join(("MASTER", *ROLE_RESUMES))
        raise ValueError(f"Unknown target_resume '{target_resume}'. Expected one of: {known}.")
    return resolved


def normalize_output_language(output_language: str) -> str:
    value = normalize_text(output_language).lower() or SUPPORTED_OUTPUT_LANGUAGES[0]
    return value


def normalize_template_id(template_id: str) -> str:
    value = normalize_text(template_id).lower() or SUPPORTED_TEMPLATE_IDS[0]
    return value


def resolve_contact_region(contact_region: str, profile_metadata_path: Path) -> str:
    normalized = normalize_text(contact_region).upper()
    if normalized:
        return normalized
    if not profile_metadata_path.exists():
        raise FileNotFoundError(f"Profile metadata is missing: {profile_metadata_path}")

    scalars = load_nested_scalar_map(profile_metadata_path.read_text(encoding="utf-8"))
    default_region = normalize_text(scalars.get("defaults.contact_region_by_vacancy_country.default", "")).upper() or "EU"
    if default_region not in CONTACT_REGIONS:
        known = ", ".join(CONTACT_REGIONS)
        raise ValueError(
            f"Default contact region '{default_region}' in profile/contact-regions.yml is unsupported. Expected one of: {known}."
        )
    return default_region


def resolve_resume_path(*, layout: WorkspaceLayout, target_resume: str) -> Path:
    resume_path = layout.resumes_dir / f"{target_resume}.md"
    if not resume_path.exists():
        raise FileNotFoundError(
            f"Selected resume '{target_resume}' is missing from resumes/. "
            "Add the resume file or pass --target-resume with an existing resume source."
        )
    return resume_path


def build_summary(
    *,
    target_resume: str,
    output_language: str,
    contact_region: str,
    template_id: str,
    page_count: int,
    changed: bool,
) -> str:
    if not changed:
        return (
            f"Resume PDF for {target_resume} already matches the current inputs "
            f"({output_language}/{contact_region}, template={template_id}, pages={page_count})."
        )
    return (
        f"Exported resume PDF for {target_resume} "
        f"({output_language}/{contact_region}, template={template_id}, pages={page_count})."
    )
