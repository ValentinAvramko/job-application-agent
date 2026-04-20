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
                summary=f"Создан каркас вакансии {vacancy_id}.",
            )
        )
        return WorkflowResult(
            workflow=self.name,
            status="completed",
            summary=f"Создан каркас вакансии {vacancy_id}.",
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
                "# Источник вакансии",
                "",
                "## Паспорт",
                "",
                f"- Компания: {request.company}",
                f"- Позиция: {request.position}",
                f"- ID вакансии: {vacancy_id}",
                f"- Исходная ссылка: {request.source_url or 'n/a'}",
                f"- Источник: {request.source_channel}",
                "",
                "## Исходный текст",
                "",
                request.source_text.strip() or "<!-- Вставь сюда исходный текст вакансии без интерпретации. -->",
                "",
            ]
        )

    def _render_analysis(self, vacancy_id: str, request: IngestVacancyRequest) -> str:
        return "\n".join(
            [
                "# Анализ вакансии",
                "",
                "## Сводка",
                "",
                f"- ID вакансии: {vacancy_id}",
                "- Выбранное резюме: undecided",
                f"- Режим адаптации: {self._render_target_mode(request.target_mode)}",
                f"- Язык: {request.language}",
                f"- Каналы работодателя: {'да' if request.include_employer_channels else 'нет'}",
                "",
                "## Анализ соответствия: текущее резюме",
                "",
                "- Общее соответствие:",
                "- Краткий вывод:",
                "",
                "## Анализ соответствия: после предложенных правок",
                "",
                "- Прогноз соответствия:",
                "- Прирост:",
                "- Комментарий:",
                "",
                "## Матрица требований",
                "",
                "| Требование | Приоритет | Подтверждение | Покрытие | Комментарий |",
                "| --- | --- | --- | --- | --- |",
                "",
                "## Сильные стороны",
                "",
                "- ",
                "",
                "## Пробелы",
                "",
                "- ",
                "",
                "## Заметки для сопроводительного письма",
                "",
                "- ",
                "",
                "## Заметки по правкам резюме",
                "",
                "- ",
                "",
                "## Каналы связи с работодателем",
                "",
                "- ",
                "",
                "## Вопросы на уточнение",
                "",
                "- ",
                "",
            ]
        )

    def _render_adoptions(self, vacancy_id: str) -> str:
        return "\n".join(
            [
                "# Адаптации по вакансии",
                "",
                f"- ID вакансии: {vacancy_id}",
                "",
                "## Временные сигналы",
                "",
                "- ",
                "",
                "## Кандидаты в постоянные сигналы",
                "",
                "- ",
                "",
                "## Открытые вопросы",
                "",
                "- ",
                "",
                "## Общие рекомендации по добавлению из MASTER в выбранную ролевую версию",
                "",
                "- ",
                "",
                "## Обновление раздела `О себе (профиль)`",
                "",
                "- ",
                "",
                "## Обновление раздела `Ключевые компетенции`",
                "",
                "- ",
                "",
                "## Обновление раздела `Опыт работы`",
                "",
                "- ",
                "",
            ]
        )

    def _render_target_mode(self, target_mode: str) -> str:
        mapping = {
            "conservative": "консервативный",
            "balanced": "сбалансированный",
            "aggressive": "агрессивный",
        }
        return mapping.get(target_mode, target_mode)
