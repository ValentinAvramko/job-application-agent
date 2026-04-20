from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from application_agent.memory.models import WorkflowRun
from application_agent.memory.store import JsonMemoryStore
from application_agent.workflows.base import WorkflowResult
from application_agent.workspace import WorkspaceLayout

CYRILLIC_MAP = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def slugify(value: str, fallback: str) -> str:
    lowered = value.strip().lower()
    transliterated = "".join(CYRILLIC_MAP.get(char, char) for char in lowered)
    cleaned = re.sub(r"[^a-z0-9]+", "-", transliterated)
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned or fallback


def build_vacancy_id(day: date, company: str, position: str) -> str:
    return f"{day:%Y%m%d}-{slugify(company, 'company')}-{slugify(position, 'role')}"


def resolve_vacancy_id(layout: WorkspaceLayout, base_id: str) -> str:
    candidate = base_id
    suffix = 2
    while layout.vacancy_dir(candidate).exists():
        candidate = f"{base_id}-{suffix:02d}"
        suffix += 1
    return candidate


@dataclass
class IngestVacancyRequest:
    company: str
    position: str
    source_text: str = ""
    source_url: str = ""
    source_channel: str = "Manual"
    source_type: str = ""
    language: str = "ru"
    country: str = "Не указано"
    work_mode: str = "Не указано"
    target_mode: str = "balanced"
    include_employer_channels: bool = False
    ingest_date: date = field(default_factory=date.today)

    def normalized_source_type(self) -> str:
        if self.source_type:
            return self.source_type
        has_url = bool(self.source_url.strip())
        has_text = bool(self.source_text.strip())
        if has_url and has_text:
            return "url+text"
        if has_url:
            return "url"
        return "text"


class IngestVacancyWorkflow:
    name = "ingest-vacancy"
    description = "Создаёт каркас вакансии и записывает стартовый runtime-след."

    def run(self, *, layout: WorkspaceLayout, store: JsonMemoryStore, request: IngestVacancyRequest) -> WorkflowResult:
        started_at = datetime.now(timezone.utc).isoformat()
        base_id = build_vacancy_id(request.ingest_date, request.company, request.position)
        vacancy_id = resolve_vacancy_id(layout, base_id)
        vacancy_dir = layout.vacancy_dir(vacancy_id)
        vacancy_dir.mkdir(parents=True, exist_ok=True)

        meta_path = vacancy_dir / "meta.yml"
        source_path = vacancy_dir / "source.md"
        analysis_path = vacancy_dir / "analysis.md"
        adoptions_path = vacancy_dir / "adoptions.md"

        timestamp = datetime.now(timezone.utc).isoformat()
        meta_path.write_text(self._render_meta(request, vacancy_id, timestamp), encoding="utf-8", newline="\n")
        source_path.write_text(self._render_source(request, vacancy_id), encoding="utf-8", newline="\n")
        analysis_path.write_text(self._render_analysis(vacancy_id, request), encoding="utf-8", newline="\n")
        adoptions_path.write_text(self._render_adoptions(vacancy_id), encoding="utf-8", newline="\n")

        artifacts = [str(meta_path), str(source_path), str(analysis_path), str(adoptions_path)]
        store.remember_task(self.name, vacancy_id, artifacts)
        store.append_run(
            WorkflowRun(
                workflow=self.name,
                status="completed",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc).isoformat(),
                artifacts=artifacts,
                summary=f"Created vacancy scaffold for {vacancy_id}.",
            )
        )
        return WorkflowResult(
            workflow=self.name,
            status="completed",
            summary=f"Vacancy scaffold created for {vacancy_id}.",
            artifacts=artifacts,
        )

    def _render_meta(self, request: IngestVacancyRequest, vacancy_id: str, timestamp: str) -> str:
        return "\n".join(
            [
                f"vacancy_id: {vacancy_id}",
                f"source_type: {request.normalized_source_type()}",
                f"source_url: {request.source_url or 'null'}",
                f"source_channel: {request.source_channel}",
                f"company: {request.company}",
                f"position: {request.position}",
                f"language: {request.language}",
                f"country: {request.country}",
                f"work_mode: {request.work_mode}",
                'is_active: "Да"',
                f"ingested_at: {timestamp}",
                "selected_resume: undecided",
                f"target_mode: {request.target_mode}",
                f"include_employer_channels: {str(request.include_employer_channels).lower()}",
                "excel_row: null",
                "status: ingested",
                'notes: ""',
                "",
            ]
        )

    def _render_source(self, request: IngestVacancyRequest, vacancy_id: str) -> str:
        return "\n".join(
            [
                "# Vacancy Source",
                "",
                "## Header",
                "",
                f"- Company: {request.company}",
                f"- Position: {request.position}",
                f"- Vacancy ID: {vacancy_id}",
                f"- Source URL: {request.source_url or 'n/a'}",
                f"- Source Channel: {request.source_channel}",
                "",
                "## Raw Text",
                "",
                request.source_text.strip() or "<!-- Insert the original vacancy text here without interpretation. -->",
                "",
            ]
        )

    def _render_analysis(self, vacancy_id: str, request: IngestVacancyRequest) -> str:
        return "\n".join(
            [
                "# Vacancy Analysis",
                "",
                "## Snapshot",
                "",
                f"- Vacancy ID: {vacancy_id}",
                "- Selected Resume: undecided",
                f"- Target Mode: {request.target_mode}",
                f"- Language: {request.language}",
                f"- Include Employer Channels: {str(request.include_employer_channels).lower()}",
                "",
                "## Fit Analysis: Current Resume",
                "",
                "- Overall Fit:",
                "- Fit Summary:",
                "",
                "## Fit Analysis: After Proposed Resume Changes",
                "",
                "- Projected Fit:",
                "- Delta:",
                "- Notes:",
                "",
                "## Requirement Matrix",
                "",
                "| Requirement | Priority | Evidence | Coverage | Notes |",
                "| --- | --- | --- | --- | --- |",
                "",
                "## Strengths",
                "",
                "- ",
                "",
                "## Gaps",
                "",
                "- ",
                "",
                "## Cover Letter Notes",
                "",
                "- ",
                "",
                "## Resume Editing Notes",
                "",
                "- ",
                "",
                "## Employer Contact Channels (Optional)",
                "",
                "- ",
                "",
                "## Follow-up Questions",
                "",
                "- ",
                "",
            ]
        )

    def _render_adoptions(self, vacancy_id: str) -> str:
        return "\n".join(
            [
                "# Vacancy Adoptions",
                "",
                f"- Vacancy ID: {vacancy_id}",
                "",
                "## Temporary Signals",
                "",
                "- ",
                "",
                "## Permanent Candidates",
                "",
                "- ",
                "",
                "## Open Questions",
                "",
                "- ",
                "",
            ]
        )
