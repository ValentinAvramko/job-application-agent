from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from application_agent.integrations.response_monitoring import (
    ResponseMonitoringActiveRow,
    ResponseMonitoringRowUpdate,
    list_active_response_monitoring_rows,
    update_response_monitoring_rows,
)
from application_agent.memory.models import WorkflowRun
from application_agent.memory.store import JsonMemoryStore
from application_agent.workflows.base import WorkflowResult
from application_agent.workflows.vacancy_sources import VacancySourceCheckResult, check_vacancy_source
from application_agent.workspace import WorkspaceLayout


@dataclass(frozen=True)
class CheckResponseMonitoringRequest:
    log_file: str = ""
    dry_run: bool = False


@dataclass
class CheckResponseMonitoringCounters:
    processed: int = 0
    deactivated: int = 0
    updated_dates: int = 0
    unchanged: int = 0
    warnings: int = 0


class CheckResponseMonitoringWorkflow:
    name = "check-response-monitoring"
    description = "Проверяет активные строки response-monitoring.xlsx и обновляет статус вакансий."

    def run(
        self,
        *,
        layout: WorkspaceLayout,
        store: JsonMemoryStore,
        request: CheckResponseMonitoringRequest,
    ) -> WorkflowResult:
        started_at = datetime.now(timezone.utc)
        workbook_path = layout.root / "response-monitoring.xlsx"
        log_path = resolve_log_path(layout=layout, requested_path=request.log_file, started_at=started_at)
        rows = list_active_response_monitoring_rows(workbook_path)
        counters = CheckResponseMonitoringCounters(processed=len(rows))
        updates: dict[int, ResponseMonitoringRowUpdate] = {}
        lines = [
            f"check-response-monitoring started_at={started_at.isoformat()}",
            f"workbook={workbook_path}",
            f"dry_run={str(request.dry_run).lower()}",
            f"active_rows={len(rows)}",
        ]

        for row in rows:
            row_update, row_lines = check_response_monitoring_row(row)
            if row_update.active_value is not None or row_update.updated_date is not None:
                updates[row.row_index] = row_update
                if row_update.active_value is not None:
                    counters.deactivated += 1
                if row_update.updated_date is not None:
                    counters.updated_dates += 1
            else:
                counters.unchanged += 1
            counters.warnings += sum(1 for line in row_lines if line.startswith("WARNING "))
            lines.extend(row_lines)

        if updates and not request.dry_run:
            update_response_monitoring_rows(workbook_path, updates)
            lines.append(f"workbook_updated rows={len(updates)}")
        elif updates:
            lines.append(f"dry_run workbook_not_updated planned_rows={len(updates)}")
        else:
            lines.append("workbook_updated rows=0")

        lines.append(
            "SUMMARY "
            f"processed={counters.processed} "
            f"deactivated={counters.deactivated} "
            f"updated_dates={counters.updated_dates} "
            f"unchanged={counters.unchanged} "
            f"warnings={counters.warnings} "
            f"log_path={log_path}"
        )
        log_text = "\n".join(lines) + "\n"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text(log_text, encoding="utf-8", newline="\n")

        artifacts = [str(log_path), str(workbook_path)]
        store.remember_task(self.name, None, artifacts)
        store.append_run(
            WorkflowRun(
                workflow=self.name,
                status="completed",
                started_at=started_at.isoformat(),
                completed_at=datetime.now(timezone.utc).isoformat(),
                artifacts=artifacts,
                summary=lines[-1],
            )
        )
        return WorkflowResult(workflow=self.name, status="completed", summary=log_text.rstrip("\n"), artifacts=artifacts)


def check_response_monitoring_row(
    row: ResponseMonitoringActiveRow,
) -> tuple[ResponseMonitoringRowUpdate, list[str]]:
    if not row.source_url.strip():
        return (
            ResponseMonitoringRowUpdate(),
            [f"WARNING row={row.row_index} url= status=warning reason=missing source url"],
        )

    try:
        check = check_vacancy_source(row.source_url)
    except Exception as exc:
        check = VacancySourceCheckResult(status="warning", reason=f"unexpected check error: {exc}", final_url=row.source_url)

    active_value = "Нет" if check.should_deactivate else None
    updated_date = check.updated_date if check.updated_date and check.updated_date != row.updated_date else None
    update = ResponseMonitoringRowUpdate(active_value=active_value, updated_date=updated_date)
    lines: list[str] = []

    if active_value is not None:
        lines.append(
            f"CHANGE row={row.row_index} column=D url={row.source_url} old=Да new=Нет reason={check.reason}"
        )
    if updated_date is not None:
        lines.append(
            "CHANGE "
            f"row={row.row_index} column=E url={row.source_url} "
            f"old={display_date(row.updated_date, row.updated_value)} new={updated_date.isoformat()} reason={check.reason}"
        )
    if check.status in {"transient_error", "warning"}:
        lines.append(
            f"WARNING row={row.row_index} url={row.source_url} status={check.status} reason={check.reason}"
        )
    if check.status == "active" and check.updated_date is None:
        lines.append(
            f"WARNING row={row.row_index} url={row.source_url} status=active reason=updated date not found"
        )
    if not lines:
        lines.append(f"UNCHANGED row={row.row_index} url={row.source_url} status={check.status} reason={check.reason}")
    return update, lines


def resolve_log_path(*, layout: WorkspaceLayout, requested_path: str, started_at: datetime) -> Path:
    if requested_path.strip():
        path = Path(requested_path).expanduser()
        return path if path.is_absolute() else layout.root / path
    filename = f"{started_at:%Y%m%d-%H%M%S}.log"
    return layout.runtime_memory_dir / "check-response-monitoring" / filename


def display_date(value: date | None, raw_value: str) -> str:
    if value is not None:
        return value.isoformat()
    return raw_value.strip() or "<empty>"
