from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re

from application_agent.memory.models import WorkflowRun
from application_agent.memory.store import JsonMemoryStore
from application_agent.review_state import QuestionEntry, QuestionLedger
from application_agent.utils.simple_yaml import load_simple_yaml
from application_agent.workflows.analyze_vacancy import dedupe_paths
from application_agent.workflows.base import WorkflowResult
from application_agent.workspace import WorkspaceLayout

VACANCY_HEADING = "## Vacancy"
TEMP_HEADING = "## TEMP"
PERM_HEADING = "## PERM"
NEW_DATA_HEADING = "## NEW DATA NEEDED"

SOURCE_TEMP_HEADING = "## Временные сигналы"
SOURCE_PERM_HEADING = "## Кандидаты в постоянные сигналы"
SOURCE_QUESTIONS_HEADING = "## Открытые вопросы"
SOURCE_MASTER_HEADING = "## Общие рекомендации по добавлению из MASTER в выбранную ролевую версию"
SOURCE_PROFILE_HEADING = "## Обновление раздела `О себе (профиль)`"
SOURCE_SKILLS_HEADING = "## Обновление раздела `Ключевые компетенции`"
SOURCE_EXPERIENCE_HEADING = "## Обновление раздела `Опыт работы`"


@dataclass
class IntakeAdoptionsRequest:
    vacancy_id: str = ""


@dataclass(frozen=True)
class InboxRow:
    suggestion: str
    target: str
    reason: str
    evidence: str
    status: str


@dataclass(frozen=True)
class NewDataRow:
    missing_data: str
    why_it_matters: str
    suggested_question: str
    status: str


class IntakeAdoptionsWorkflow:
    name = "intake-adoptions"
    description = "Готовит root adoptions inbox и pending questions для уже проанализированной вакансии."

    def run(self, *, layout: WorkspaceLayout, store: JsonMemoryStore, request: IntakeAdoptionsRequest) -> WorkflowResult:
        started_at = datetime.now(timezone.utc).isoformat()
        vacancy_id = request.vacancy_id.strip()
        if not vacancy_id:
            raise ValueError("intake-adoptions requires a non-empty vacancy_id.")

        vacancy_dir = layout.vacancy_dir(vacancy_id)
        meta_path = vacancy_dir / "meta.yml"
        draft_path = vacancy_dir / "adoptions.md"
        inbox_path = layout.adoptions_dir / "inbox" / f"{vacancy_id}.md"
        questions_path = layout.adoptions_dir / "questions" / "open.md"

        if not vacancy_dir.exists():
            raise FileNotFoundError(
                f"Vacancy '{vacancy_id}' is missing from vacancies/. Runtime memory or the provided vacancy_id is stale; "
                "run ingest-vacancy/analyze-vacancy again or pass an existing --vacancy-id."
            )

        if not meta_path.exists() or not draft_path.exists():
            raise FileNotFoundError(
                f"Vacancy '{vacancy_id}' is incomplete: meta.yml or adoptions.md is missing. "
                "Run analyze-vacancy before intake-adoptions."
            )

        meta = load_simple_yaml(meta_path)
        draft_text = draft_path.read_text(encoding="utf-8")

        company = clean_meta_value(meta.get("company"))
        position = clean_meta_value(meta.get("position"))
        selected_resume = clean_meta_value(meta.get("selected_resume"), fallback="undecided")

        temp_rows = build_temp_rows(
            vacancy_id=vacancy_id,
            selected_resume=selected_resume,
            draft_text=draft_text,
        )
        perm_rows = build_perm_rows(vacancy_id=vacancy_id, draft_text=draft_text)
        question_items = extract_section_bullets(draft_text, SOURCE_QUESTIONS_HEADING)
        new_data_rows = build_new_data_rows(vacancy_id=vacancy_id, question_items=question_items)
        pending_entries = build_pending_question_entries(vacancy_id=vacancy_id, question_items=question_items)

        inbox_path.write_text(
            render_inbox(
                vacancy_id=vacancy_id,
                company=company,
                position=position,
                selected_resume=selected_resume,
                temp_rows=temp_rows,
                perm_rows=perm_rows,
                new_data_rows=new_data_rows,
            ),
            encoding="utf-8",
            newline="\n",
        )

        question_ledger = QuestionLedger.load(questions_path)
        question_ledger.entries = [entry for entry in question_ledger.records() if entry.related_to != vacancy_id]
        for entry in pending_entries:
            question_ledger.upsert(entry)
        question_ledger.write(questions_path)

        artifacts = dedupe_paths([str(inbox_path), str(questions_path)])
        store.remember_task(self.name, vacancy_id, artifacts)
        store.append_run(
            WorkflowRun(
                workflow=self.name,
                status="completed",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc).isoformat(),
                artifacts=artifacts,
                summary=f"Подготовлены adoptions inbox и pending questions для вакансии {vacancy_id}.",
            )
        )
        return WorkflowResult(
            workflow=self.name,
            status="completed",
            summary=f"Подготовлен intake adoptions для вакансии {vacancy_id}.",
            artifacts=artifacts,
        )


def build_temp_rows(*, vacancy_id: str, selected_resume: str, draft_text: str) -> list[InboxRow]:
    rows: list[InboxRow] = []
    rows.extend(
        rows_from_section(
            vacancy_id=vacancy_id,
            selected_resume=selected_resume,
            draft_text=draft_text,
            source_heading=SOURCE_TEMP_HEADING,
            target="selected resume",
            reason="Vacancy-specific signal from the generated adoptions draft.",
        )
    )
    rows.extend(
        rows_from_section(
            vacancy_id=vacancy_id,
            selected_resume=selected_resume,
            draft_text=draft_text,
            source_heading=SOURCE_MASTER_HEADING,
            target=f"{selected_resume}.md",
            reason="Candidate adaptation from MASTER into the selected role resume.",
        )
    )
    rows.extend(
        rows_from_section(
            vacancy_id=vacancy_id,
            selected_resume=selected_resume,
            draft_text=draft_text,
            source_heading=SOURCE_PROFILE_HEADING,
            target=f"{selected_resume}.md :: profile",
            reason="Vacancy-specific profile update proposed by the analysis stage.",
        )
    )
    rows.extend(
        rows_from_section(
            vacancy_id=vacancy_id,
            selected_resume=selected_resume,
            draft_text=draft_text,
            source_heading=SOURCE_SKILLS_HEADING,
            target=f"{selected_resume}.md :: skills",
            reason="Vacancy-specific skills update proposed by the analysis stage.",
        )
    )
    rows.extend(
        rows_from_section(
            vacancy_id=vacancy_id,
            selected_resume=selected_resume,
            draft_text=draft_text,
            source_heading=SOURCE_EXPERIENCE_HEADING,
            target=f"{selected_resume}.md :: experience",
            reason="Vacancy-specific experience update proposed by the analysis stage.",
        )
    )
    return dedupe_inbox_rows(rows)


def build_perm_rows(*, vacancy_id: str, draft_text: str) -> list[InboxRow]:
    items = extract_section_bullets(draft_text, SOURCE_PERM_HEADING)
    rows = [
        InboxRow(
            suggestion=item,
            target="MASTER.md",
            reason="Candidate durable signal for later review into accepted/MASTER.md.",
            evidence=f"vacancies/{vacancy_id}/adoptions.md -> {SOURCE_PERM_HEADING.removeprefix('## ')}",
            status="PERM",
        )
        for item in items
    ]
    return dedupe_inbox_rows(rows)


def rows_from_section(
    *,
    vacancy_id: str,
    selected_resume: str,
    draft_text: str,
    source_heading: str,
    target: str,
    reason: str,
) -> list[InboxRow]:
    items = extract_section_bullets(draft_text, source_heading)
    section_name = source_heading.removeprefix("## ")
    normalized_target = target.replace("selected resume", f"{selected_resume}.md")
    return [
        InboxRow(
            suggestion=item,
            target=normalized_target,
            reason=reason,
            evidence=f"vacancies/{vacancy_id}/adoptions.md -> {section_name}",
            status="TEMP",
        )
        for item in items
    ]


def build_new_data_rows(*, vacancy_id: str, question_items: list[str]) -> list[NewDataRow]:
    why_it_matters = (
        f"Blocks confident review of vacancy {vacancy_id} and promotion of durable signals into accepted layers."
    )
    return [
        NewDataRow(
            missing_data=item,
            why_it_matters=why_it_matters,
            suggested_question=item,
            status="NEW DATA NEEDED",
        )
        for item in dedupe_preserve_order(question_items)
    ]


def build_pending_question_entries(*, vacancy_id: str, question_items: list[str]) -> list[QuestionEntry]:
    return [
        QuestionEntry(
            topic=item,
            related_to=vacancy_id,
            why_it_matters="Initial unresolved item imported during adoptions intake.",
            suggested_question=item,
            status="pending",
        )
        for item in dedupe_preserve_order(question_items)
    ]


def render_inbox(
    *,
    vacancy_id: str,
    company: str,
    position: str,
    selected_resume: str,
    temp_rows: list[InboxRow],
    perm_rows: list[InboxRow],
    new_data_rows: list[NewDataRow],
) -> str:
    lines = [
        "# Adoptions Inbox",
        "",
        VACANCY_HEADING,
        "",
        f"- Vacancy ID: {vacancy_id}",
        f"- Company: {company}",
        f"- Position: {position}",
        f"- Selected Resume: {selected_resume}",
        "",
        TEMP_HEADING,
        "",
        "| Suggestion | Target | Reason | Evidence | Status |",
        "| --- | --- | --- | --- | --- |",
        *render_inbox_rows(temp_rows),
        "",
        PERM_HEADING,
        "",
        "| Suggestion | Target | Reason | Evidence | Status |",
        "| --- | --- | --- | --- | --- |",
        *render_inbox_rows(perm_rows),
        "",
        NEW_DATA_HEADING,
        "",
        "| Missing Data | Why It Matters | Suggested Question | Status |",
        "| --- | --- | --- | --- |",
        *render_new_data_rows(new_data_rows),
        "",
    ]
    return "\n".join(lines)


def render_inbox_rows(rows: list[InboxRow]) -> list[str]:
    if not rows:
        return ["|  |  |  |  |  |"]
    return [
        "| "
        + " | ".join(
            [
                escape_table(row.suggestion),
                escape_table(row.target),
                escape_table(row.reason),
                escape_table(row.evidence),
                escape_table(row.status),
            ]
        )
        + " |"
        for row in rows
    ]


def render_new_data_rows(rows: list[NewDataRow]) -> list[str]:
    if not rows:
        return ["|  |  |  |  |"]
    return [
        "| "
        + " | ".join(
            [
                escape_table(row.missing_data),
                escape_table(row.why_it_matters),
                escape_table(row.suggested_question),
                escape_table(row.status),
            ]
        )
        + " |"
        for row in rows
    ]


def extract_section_bullets(markdown: str, heading: str) -> list[str]:
    if heading not in markdown:
        return []
    section = markdown.split(heading, maxsplit=1)[1]
    match = re.search(r"\n##\s", section)
    if match:
        section = section[: match.start()]
    items: list[str] = []
    table_headers: list[str] = []
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if line.startswith("- "):
            item = normalize_bullet(line[2:])
            if item:
                items.append(item)
            continue
        if line.startswith("|") and line.endswith("|"):
            cells = split_table_row(line)
            if not cells or is_table_separator(cells):
                continue
            if not table_headers:
                table_headers = cells
                continue
            item = normalize_table_item(table_headers, cells)
            if item:
                items.append(item)
    return dedupe_preserve_order(items)


def split_table_row(line: str) -> list[str]:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return [cell for cell in cells if cell]


def is_table_separator(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def normalize_table_item(headers: list[str], cells: list[str]) -> str:
    pairs: list[str] = []
    for index, cell in enumerate(cells):
        normalized_cell = normalize_bullet(cell)
        if not normalized_cell:
            continue
        header = headers[index] if index < len(headers) else f"Column {index + 1}"
        pairs.append(f"{header}: {normalized_cell}")
    return "; ".join(pairs)


def normalize_bullet(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value.strip())
    if normalized in {"", "-", "—"}:
        return ""
    return normalized.rstrip(".")


def clean_meta_value(value: object, *, fallback: str = "n/a") -> str:
    normalized = str(value or "").strip()
    return normalized or fallback


def dedupe_inbox_rows(rows: list[InboxRow]) -> list[InboxRow]:
    seen: set[tuple[str, str, str]] = set()
    result: list[InboxRow] = []
    for row in rows:
        key = (row.status.lower(), row.target.lower(), row.suggestion.lower())
        if key in seen:
            continue
        seen.add(key)
        result.append(row)
    return result


def dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
