from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from application_agent.review_state import (
    AcceptedSignal,
    AcceptedSignalsStore,
    QuestionEntry,
    QuestionLedger,
    extract_markdown_section,
    split_markdown_row,
)
from application_agent.workspace import WorkspaceLayout

VACANCY_HEADING = "## Vacancy"
TEMP_HEADING = "## TEMP"
PERM_HEADING = "## PERM"
NEW_DATA_HEADING = "## NEW DATA NEEDED"


@dataclass(frozen=True)
class ReviewInboxRow:
    suggestion: str
    target: str
    reason: str
    evidence: str
    status: str


@dataclass(frozen=True)
class ReviewMissingDataRow:
    missing_data: str
    why_it_matters: str
    suggested_question: str
    status: str


@dataclass(frozen=True)
class ReviewSessionContext:
    vacancy_id: str
    company: str
    position: str
    selected_resume: str
    temp_rows: list[ReviewInboxRow]
    perm_rows: list[ReviewInboxRow]
    new_data_rows: list[ReviewMissingDataRow]
    pending_questions: list[QuestionEntry]
    answered_questions: list[QuestionEntry]
    closed_questions: list[QuestionEntry]
    accepted_signals: list[AcceptedSignal]


@dataclass(frozen=True)
class ApprovedSignalInput:
    signal: str
    rationale: str
    target: str = "MASTER.md"
    updated_at: str = ""


@dataclass(frozen=True)
class AnsweredQuestionInput:
    topic: str
    answer: str


@dataclass(frozen=True)
class ClosedQuestionInput:
    topic: str
    resolution: str


@dataclass(frozen=True)
class ApplyReviewDecisionRequest:
    vacancy_id: str
    approved_signals: list[ApprovedSignalInput] = field(default_factory=list)
    answered_questions: list[AnsweredQuestionInput] = field(default_factory=list)
    closed_questions: list[ClosedQuestionInput] = field(default_factory=list)


@dataclass(frozen=True)
class ApplyReviewDecisionResult:
    vacancy_id: str
    approved_signal_count: int
    answered_question_count: int
    closed_question_count: int
    artifacts: list[str]


def load_review_session_context(*, layout: WorkspaceLayout, vacancy_id: str) -> ReviewSessionContext:
    normalized_vacancy_id = vacancy_id.strip()
    if not normalized_vacancy_id:
        raise ValueError("load_review_session_context requires a non-empty vacancy_id.")

    inbox_path = layout.adoptions_dir / "inbox" / f"{normalized_vacancy_id}.md"
    if not inbox_path.exists():
        raise FileNotFoundError(
            f"Missing adoptions inbox for vacancy '{normalized_vacancy_id}'. Run intake-adoptions before review."
        )

    inbox_text = inbox_path.read_text(encoding="utf-8")
    vacancy_fields = parse_vacancy_block(inbox_text)
    temp_rows = parse_inbox_rows(inbox_text, TEMP_HEADING)
    perm_rows = parse_inbox_rows(inbox_text, PERM_HEADING)
    new_data_rows = parse_missing_data_rows(inbox_text)

    question_ledger = QuestionLedger.load(layout.adoptions_dir / "questions" / "open.md")
    accepted_store = AcceptedSignalsStore.load(layout.adoptions_dir / "accepted" / "MASTER.md")

    return ReviewSessionContext(
        vacancy_id=normalized_vacancy_id,
        company=vacancy_fields.get("Company", "n/a"),
        position=vacancy_fields.get("Position", "n/a"),
        selected_resume=vacancy_fields.get("Selected Resume", "n/a"),
        temp_rows=temp_rows,
        perm_rows=perm_rows,
        new_data_rows=new_data_rows,
        pending_questions=[
            entry for entry in question_ledger.records("pending") if entry.related_to == normalized_vacancy_id
        ],
        answered_questions=[
            entry for entry in question_ledger.records("answered") if entry.related_to == normalized_vacancy_id
        ],
        closed_questions=[
            entry for entry in question_ledger.records("closed") if entry.related_to == normalized_vacancy_id
        ],
        accepted_signals=accepted_store.records(),
    )


def apply_review_decision(
    *, layout: WorkspaceLayout, request: ApplyReviewDecisionRequest
) -> ApplyReviewDecisionResult:
    vacancy_id = request.vacancy_id.strip()
    if not vacancy_id:
        raise ValueError("apply_review_decision requires a non-empty vacancy_id.")

    # Validate the vacancy context before mutating shared state.
    load_review_session_context(layout=layout, vacancy_id=vacancy_id)

    questions_path = layout.adoptions_dir / "questions" / "open.md"
    accepted_path = layout.adoptions_dir / "accepted" / "MASTER.md"
    question_ledger = QuestionLedger.load(questions_path)
    accepted_store = AcceptedSignalsStore.load(accepted_path)

    for approved_signal in request.approved_signals:
        accepted_store.upsert(
            AcceptedSignal(
                signal=approved_signal.signal,
                target=approved_signal.target,
                source_vacancy=vacancy_id,
                rationale=approved_signal.rationale,
                updated_at=approved_signal.updated_at or datetime.now(timezone.utc).isoformat(),
            )
        )

    for answered_question in request.answered_questions:
        question_ledger.mark_answered(
            topic=answered_question.topic,
            related_to=vacancy_id,
            answer=answered_question.answer,
        )

    for closed_question in request.closed_questions:
        question_ledger.mark_closed(
            topic=closed_question.topic,
            related_to=vacancy_id,
            resolution=closed_question.resolution,
        )

    accepted_store.write(accepted_path)
    question_ledger.write(questions_path)

    return ApplyReviewDecisionResult(
        vacancy_id=vacancy_id,
        approved_signal_count=len(request.approved_signals),
        answered_question_count=len(request.answered_questions),
        closed_question_count=len(request.closed_questions),
        artifacts=[str(questions_path), str(accepted_path)],
    )


def parse_vacancy_block(markdown: str) -> dict[str, str]:
    block = extract_markdown_section(markdown, VACANCY_HEADING)
    fields: dict[str, str] = {}
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line.startswith("- "):
            continue
        content = line[2:]
        if ":" not in content:
            continue
        key, value = content.split(":", maxsplit=1)
        fields[key.strip()] = value.strip()
    return fields


def parse_inbox_rows(markdown: str, heading: str) -> list[ReviewInboxRow]:
    block = extract_markdown_section(markdown, heading)
    if not block:
        return []

    table_lines = [line.strip() for line in block.splitlines() if line.strip().startswith("|")]
    rows: list[ReviewInboxRow] = []
    for line in table_lines[2:]:
        cells = split_markdown_row(line)
        if len(cells) != 5:
            continue
        if not any(cell.strip() for cell in cells):
            continue
        rows.append(
            ReviewInboxRow(
                suggestion=cells[0].strip(),
                target=cells[1].strip(),
                reason=cells[2].strip(),
                evidence=cells[3].strip(),
                status=cells[4].strip(),
            )
        )
    return rows


def parse_missing_data_rows(markdown: str) -> list[ReviewMissingDataRow]:
    block = extract_markdown_section(markdown, NEW_DATA_HEADING)
    if not block:
        return []

    table_lines = [line.strip() for line in block.splitlines() if line.strip().startswith("|")]
    rows: list[ReviewMissingDataRow] = []
    for line in table_lines[2:]:
        cells = split_markdown_row(line)
        if len(cells) != 4:
            continue
        if not any(cell.strip() for cell in cells):
            continue
        rows.append(
            ReviewMissingDataRow(
                missing_data=cells[0].strip(),
                why_it_matters=cells[1].strip(),
                suggested_question=cells[2].strip(),
                status=cells[3].strip(),
            )
        )
    return rows
