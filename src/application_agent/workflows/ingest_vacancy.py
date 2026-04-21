from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone

from application_agent.integrations.response_monitoring import ResponseMonitoringIngestRecord, append_ingest_record
from application_agent.memory.models import WorkflowRun
from application_agent.memory.store import JsonMemoryStore
from application_agent.utils.placeholders import is_unspecified
from application_agent.utils.simple_yaml import load_simple_yaml, write_simple_yaml
from application_agent.workflows.base import WorkflowResult
from application_agent.workflows.vacancy_rendering import (
    render_adoptions,
    render_analysis,
    render_meta,
    render_source,
    render_target_mode,
)
from application_agent.workflows.vacancy_sources import (
    VacancySourceDetails,
    build_enriched_source_markdown,
    build_vacancy_id,
    fetch_source_details,
    infer_source_channel,
    merge_source_details,
    normalize_country_value,
    normalize_language_tag,
    parse_generic_vacancy_page,
    parse_hh_vacancy_page,
    parse_hh_vacancy_payload,
    resolve_vacancy_id,
)
from application_agent.workspace import WorkspaceLayout


def build_response_monitoring_record(request: "IngestVacancyRequest", vacancy_id: str) -> ResponseMonitoringIngestRecord:
    source_channel = request.source_channel.strip() or infer_source_channel(request.source_url, request.source_text)
    return ResponseMonitoringIngestRecord(
        vacancy_id=vacancy_id,
        source_channel=source_channel,
        source_url=request.source_url.strip(),
        company=request.company.strip(),
        position=request.position.strip(),
        country=request.country.strip(),
        work_mode=request.work_mode.strip(),
        ingest_date=request.ingest_date,
    )


def enrich_request(request: "IngestVacancyRequest") -> "IngestVacancyRequest":
    source_markdown = request.source_markdown.strip() or request.source_text.strip()
    if source_markdown:
        source_markdown = build_enriched_source_markdown(source_markdown, request.key_skills)
    source_channel = infer_source_channel(request.source_url, request.source_text, request.source_channel)
    request = replace(request, source_markdown=source_markdown, source_channel=source_channel)

    if not request.source_url.strip():
        if is_unspecified(request.country):
            request = replace(request, country="")
        if is_unspecified(request.work_mode):
            request = replace(request, work_mode="")
        return request

    needs_enrichment = (
        not request.company.strip()
        or not request.position.strip()
        or not request.source_text.strip()
        or is_unspecified(request.country)
        or is_unspecified(request.work_mode)
        or not request.key_skills
    )
    if not needs_enrichment:
        return request
    try:
        details = fetch_source_details(request.source_url.strip())
    except Exception as exc:
        missing_required = [name for name, value in (("company", request.company), ("position", request.position)) if not value.strip()]
        if missing_required:
            missing = ", ".join(missing_required)
            raise ValueError(
                f"Failed to fetch vacancy details from source_url {request.source_url.strip()}: {exc}. "
                f"Missing required fields: {missing}. Provide them manually or retry with a reachable URL."
            ) from exc
        return request

    language = request.language
    if not language.strip() and details.language:
        language = details.language

    country = request.country
    if is_unspecified(country):
        country = details.country

    work_mode = request.work_mode
    if is_unspecified(work_mode):
        work_mode = details.work_mode

    key_skills = request.key_skills or details.key_skills
    if request.source_markdown.strip():
        source_markdown = build_enriched_source_markdown(request.source_markdown.strip(), key_skills)
    elif details.source_markdown.strip():
        source_markdown = build_enriched_source_markdown(details.source_markdown.strip(), key_skills)
    else:
        source_markdown = build_enriched_source_markdown(details.source_text, key_skills)

    return replace(
        request,
        company=request.company.strip() or details.company,
        position=request.position.strip() or details.position,
        source_text=request.source_text.strip() or details.source_text,
        source_markdown=source_markdown,
        language=language,
        source_channel=request.source_channel.strip() or details.source_channel or infer_source_channel(request.source_url, details.source_text),
        country=country,
        city=request.city.strip() or details.city,
        work_mode=work_mode,
        employment_type=request.employment_type.strip() or details.employment_type,
        work_schedule=request.work_schedule.strip() or details.work_schedule,
        key_skills=key_skills,
    )


@dataclass
class IngestVacancyRequest:
    company: str = ""
    position: str = ""
    source_text: str = ""
    source_markdown: str = ""
    source_url: str = ""
    source_channel: str = ""
    source_type: str = ""
    language: str = ""
    country: str = ""
    city: str = ""
    work_mode: str = ""
    employment_type: str = ""
    work_schedule: str = ""
    key_skills: list[str] = field(default_factory=list)
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
    description = "\u0421\u043e\u0437\u0434\u0430\u0451\u0442 \u043a\u0430\u0440\u043a\u0430\u0441 \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u0438 \u0438 \u0437\u0430\u043f\u0438\u0441\u044b\u0432\u0430\u0435\u0442 \u0441\u0442\u0430\u0440\u0442\u043e\u0432\u044b\u0439 runtime-\u0441\u043b\u0435\u0434."

    def run(self, *, layout: WorkspaceLayout, store: JsonMemoryStore, request: IngestVacancyRequest) -> WorkflowResult:
        started_at = datetime.now(timezone.utc).isoformat()
        request = enrich_request(request)
        missing_fields = [name for name, value in (("company", request.company), ("position", request.position)) if not value.strip()]
        if missing_fields:
            missing = ", ".join(missing_fields)
            raise ValueError(
                f"ingest-vacancy requires company and position, unless they can be extracted from source_url. Missing: {missing}."
            )

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
        response_monitoring_path = layout.root / "response-monitoring.xlsx"
        excel_row = append_ingest_record(response_monitoring_path, build_response_monitoring_record(request, vacancy_id))
        meta_payload = load_simple_yaml(meta_path)
        meta_payload["excel_row"] = excel_row
        write_simple_yaml(meta_path, meta_payload)

        artifacts = [str(meta_path), str(source_path), str(analysis_path), str(adoptions_path), str(response_monitoring_path)]
        store.remember_task(self.name, vacancy_id, artifacts)
        store.append_run(
            WorkflowRun(
                workflow=self.name,
                status="completed",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc).isoformat(),
                artifacts=artifacts,
                summary=f"\u0421\u043e\u0437\u0434\u0430\u043d \u043a\u0430\u0440\u043a\u0430\u0441 \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u0438 {vacancy_id}.",
            )
        )
        return WorkflowResult(
            workflow=self.name,
            status="completed",
            summary=f"\u0421\u043e\u0437\u0434\u0430\u043d \u043a\u0430\u0440\u043a\u0430\u0441 \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u0438 {vacancy_id}.",
            artifacts=artifacts,
        )

    def _render_meta(self, request: IngestVacancyRequest, vacancy_id: str, timestamp: str, excel_row: int | None = None) -> str:
        return render_meta(request, vacancy_id, timestamp, infer_source_channel, excel_row=excel_row)

    def _render_source(self, request: IngestVacancyRequest, vacancy_id: str) -> str:
        return render_source(request, vacancy_id, infer_source_channel)

    def _render_analysis(self, vacancy_id: str, request: IngestVacancyRequest) -> str:
        return render_analysis(vacancy_id, request)

    def _render_adoptions(self, vacancy_id: str) -> str:
        return render_adoptions(vacancy_id)

    def _render_target_mode(self, target_mode: str) -> str:
        return render_target_mode(target_mode)
