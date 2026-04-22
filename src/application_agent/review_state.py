from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re

QUESTION_STATUSES = ("pending", "answered", "closed")
PENDING_HEADING = "## Pending"
ANSWERED_HEADING = "## Answered"
CLOSED_HEADING = "## Closed"
CURRENT_SIGNALS_HEADING = "## Current Signals"


@dataclass(frozen=True)
class QuestionEntry:
    topic: str
    related_to: str
    why_it_matters: str
    suggested_question: str
    status: str = "pending"
    answer: str = ""
    resolution: str = ""

    def normalized(self) -> QuestionEntry:
        normalized_status = normalize_question_status(self.status)
        return QuestionEntry(
            topic=normalize_text(self.topic),
            related_to=normalize_text(self.related_to),
            why_it_matters=normalize_text(self.why_it_matters),
            suggested_question=normalize_text(self.suggested_question),
            status=normalized_status,
            answer=normalize_text(self.answer),
            resolution=normalize_text(self.resolution),
        )

    @property
    def key(self) -> tuple[str, str]:
        normalized = self.normalized()
        return (normalized.related_to.lower(), normalized.topic.lower())


@dataclass
class QuestionLedger:
    entries: list[QuestionEntry] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> QuestionLedger:
        if not path.exists():
            return cls()

        text = path.read_text(encoding="utf-8")
        entries: list[QuestionEntry] = []
        entries.extend(parse_pending_entries(text))
        entries.extend(parse_answered_entries(text))
        entries.extend(parse_closed_entries(text))
        return cls(entries=dedupe_question_entries(entries))

    def upsert(self, entry: QuestionEntry) -> None:
        normalized = entry.normalized()
        retained = [existing for existing in self.entries if existing.key != normalized.key]
        retained.append(normalized)
        self.entries = dedupe_question_entries(retained)

    def mark_answered(self, *, topic: str, related_to: str, answer: str) -> None:
        entry = self._require_entry(topic=topic, related_to=related_to)
        self.upsert(
            QuestionEntry(
                topic=entry.topic,
                related_to=entry.related_to,
                why_it_matters=entry.why_it_matters,
                suggested_question=entry.suggested_question,
                status="answered",
                answer=answer,
                resolution=entry.resolution,
            )
        )

    def mark_closed(self, *, topic: str, related_to: str, resolution: str) -> None:
        entry = self._require_entry(topic=topic, related_to=related_to)
        self.upsert(
            QuestionEntry(
                topic=entry.topic,
                related_to=entry.related_to,
                why_it_matters=entry.why_it_matters,
                suggested_question=entry.suggested_question,
                status="closed",
                answer=entry.answer,
                resolution=resolution,
            )
        )

    def records(self, status: str | None = None) -> list[QuestionEntry]:
        if status is None:
            return sorted(self.entries, key=question_sort_key)
        normalized_status = normalize_question_status(status)
        return sorted((entry for entry in self.entries if entry.status == normalized_status), key=question_sort_key)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_question_ledger(self.entries), encoding="utf-8", newline="\n")

    def _require_entry(self, *, topic: str, related_to: str) -> QuestionEntry:
        key = (normalize_text(related_to).lower(), normalize_text(topic).lower())
        for entry in self.entries:
            if entry.key == key:
                return entry
        raise KeyError(f"Unknown question '{topic}' for '{related_to}'.")


@dataclass(frozen=True)
class AcceptedSignal:
    signal: str
    target: str
    source_vacancy: str
    rationale: str
    updated_at: str

    def normalized(self) -> AcceptedSignal:
        return AcceptedSignal(
            signal=normalize_text(self.signal),
            target=normalize_text(self.target),
            source_vacancy=normalize_text(self.source_vacancy),
            rationale=normalize_text(self.rationale),
            updated_at=normalize_text(self.updated_at),
        )

    @property
    def key(self) -> tuple[str, str]:
        normalized = self.normalized()
        return (normalized.target.lower(), normalized.signal.lower())


@dataclass
class AcceptedSignalsStore:
    signals: list[AcceptedSignal] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> AcceptedSignalsStore:
        if not path.exists():
            return cls()

        text = path.read_text(encoding="utf-8")
        block = extract_markdown_section(text, CURRENT_SIGNALS_HEADING)
        if not block:
            return cls()

        table_lines = [line.strip() for line in block.splitlines() if line.strip().startswith("|")]
        signals: list[AcceptedSignal] = []
        for line in table_lines[2:]:
            cells = split_markdown_row(line)
            if len(cells) != 5:
                continue
            if not any(cell.strip() for cell in cells):
                continue
            signals.append(
                AcceptedSignal(
                    signal=cells[0].strip(),
                    target=cells[1].strip(),
                    source_vacancy=cells[2].strip(),
                    rationale=cells[3].strip(),
                    updated_at=cells[4].strip(),
                )
            )
        return cls(signals=dedupe_accepted_signals(signals))

    def upsert(self, signal: AcceptedSignal) -> None:
        normalized = signal.normalized()
        retained = [existing for existing in self.signals if existing.key != normalized.key]
        retained.append(normalized)
        self.signals = dedupe_accepted_signals(retained)

    def remove(self, *, signal: str, target: str) -> None:
        key = (normalize_text(target).lower(), normalize_text(signal).lower())
        self.signals = [existing for existing in self.signals if existing.key != key]

    def records(self) -> list[AcceptedSignal]:
        return sorted(self.signals, key=accepted_sort_key)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_accepted_signals(self.signals), encoding="utf-8", newline="\n")


def render_question_ledger(entries: list[QuestionEntry]) -> str:
    pending = [entry for entry in dedupe_question_entries(entries) if entry.status == "pending"]
    answered = [entry for entry in dedupe_question_entries(entries) if entry.status == "answered"]
    closed = [entry for entry in dedupe_question_entries(entries) if entry.status == "closed"]

    lines = [
        "# Open Questions",
        "",
        PENDING_HEADING,
        "",
        "| Topic | Related To | Why It Matters | Suggested Question | Status |",
        "| --- | --- | --- | --- | --- |",
        *render_pending_rows(pending),
        "",
        ANSWERED_HEADING,
        "",
        "| Topic | Related To | Why It Matters | Suggested Question | Answer | Status |",
        "| --- | --- | --- | --- | --- | --- |",
        *render_answered_rows(answered),
        "",
        CLOSED_HEADING,
        "",
        "| Topic | Related To | Why It Matters | Resolution | Status |",
        "| --- | --- | --- | --- | --- |",
        *render_closed_rows(closed),
        "",
    ]
    return "\n".join(lines)


def render_accepted_signals(signals: list[AcceptedSignal]) -> str:
    lines = [
        "# Accepted Adoptions for MASTER",
        "",
        CURRENT_SIGNALS_HEADING,
        "",
        "| Signal | Target | Source Vacancy | Rationale | Updated At |",
        "| --- | --- | --- | --- | --- |",
        *render_accepted_rows(dedupe_accepted_signals(signals)),
        "",
    ]
    return "\n".join(lines)


def render_pending_rows(entries: list[QuestionEntry]) -> list[str]:
    if not entries:
        return ["|  |  |  |  |  |"]
    return [
        "| "
        + " | ".join(
            [
                escape_table(entry.topic),
                escape_table(entry.related_to),
                escape_table(entry.why_it_matters),
                escape_table(entry.suggested_question),
                escape_table(entry.status),
            ]
        )
        + " |"
        for entry in sorted(entries, key=question_sort_key)
    ]


def render_answered_rows(entries: list[QuestionEntry]) -> list[str]:
    if not entries:
        return ["|  |  |  |  |  |  |"]
    return [
        "| "
        + " | ".join(
            [
                escape_table(entry.topic),
                escape_table(entry.related_to),
                escape_table(entry.why_it_matters),
                escape_table(entry.suggested_question),
                escape_table(entry.answer),
                escape_table(entry.status),
            ]
        )
        + " |"
        for entry in sorted(entries, key=question_sort_key)
    ]


def render_closed_rows(entries: list[QuestionEntry]) -> list[str]:
    if not entries:
        return ["|  |  |  |  |  |"]
    return [
        "| "
        + " | ".join(
            [
                escape_table(entry.topic),
                escape_table(entry.related_to),
                escape_table(entry.why_it_matters),
                escape_table(entry.resolution or entry.answer),
                escape_table(entry.status),
            ]
        )
        + " |"
        for entry in sorted(entries, key=question_sort_key)
    ]


def render_accepted_rows(signals: list[AcceptedSignal]) -> list[str]:
    if not signals:
        return ["|  |  |  |  |  |"]
    return [
        "| "
        + " | ".join(
            [
                escape_table(signal.signal),
                escape_table(signal.target),
                escape_table(signal.source_vacancy),
                escape_table(signal.rationale),
                escape_table(signal.updated_at),
            ]
        )
        + " |"
        for signal in sorted(signals, key=accepted_sort_key)
    ]


def parse_pending_entries(markdown: str) -> list[QuestionEntry]:
    block = extract_markdown_section(markdown, PENDING_HEADING)
    return parse_question_block(block=block, expected_cells=5, status="pending")


def parse_answered_entries(markdown: str) -> list[QuestionEntry]:
    block = extract_markdown_section(markdown, ANSWERED_HEADING)
    return parse_question_block(block=block, expected_cells=6, status="answered")


def parse_closed_entries(markdown: str) -> list[QuestionEntry]:
    block = extract_markdown_section(markdown, CLOSED_HEADING)
    return parse_question_block(block=block, expected_cells=5, status="closed")


def parse_question_block(*, block: str, expected_cells: int, status: str) -> list[QuestionEntry]:
    if not block:
        return []

    table_lines = [line.strip() for line in block.splitlines() if line.strip().startswith("|")]
    entries: list[QuestionEntry] = []
    for line in table_lines[2:]:
        cells = split_markdown_row(line)
        if len(cells) != expected_cells:
            continue
        if not any(cell.strip() for cell in cells):
            continue

        if status == "pending":
            entries.append(
                QuestionEntry(
                    topic=cells[0].strip(),
                    related_to=cells[1].strip(),
                    why_it_matters=cells[2].strip(),
                    suggested_question=cells[3].strip(),
                    status=cells[4].strip() or status,
                )
            )
            continue

        if status == "answered":
            entries.append(
                QuestionEntry(
                    topic=cells[0].strip(),
                    related_to=cells[1].strip(),
                    why_it_matters=cells[2].strip(),
                    suggested_question=cells[3].strip(),
                    answer=cells[4].strip(),
                    status=cells[5].strip() or status,
                )
            )
            continue

        entries.append(
            QuestionEntry(
                topic=cells[0].strip(),
                related_to=cells[1].strip(),
                why_it_matters=cells[2].strip(),
                suggested_question="",
                resolution=cells[3].strip(),
                status=cells[4].strip() or status,
            )
        )
    return entries


def extract_markdown_section(markdown: str, heading: str) -> str:
    heading_index = markdown.find(heading)
    if heading_index == -1:
        return ""

    section = markdown[heading_index:]
    match = re.search(r"\n##\s", section[len(heading) :])
    if not match:
        return section
    return section[: len(heading) + match.start()]


def normalize_question_status(value: str) -> str:
    normalized = normalize_text(value).lower()
    if normalized not in QUESTION_STATUSES:
        raise ValueError(f"Unsupported question status: {value}")
    return normalized


def dedupe_question_entries(entries: list[QuestionEntry]) -> list[QuestionEntry]:
    ordered: dict[tuple[str, str], QuestionEntry] = {}
    for entry in entries:
        normalized = entry.normalized()
        ordered[normalized.key] = normalized
    return sorted(ordered.values(), key=question_sort_key)


def dedupe_accepted_signals(signals: list[AcceptedSignal]) -> list[AcceptedSignal]:
    ordered: dict[tuple[str, str], AcceptedSignal] = {}
    for signal in signals:
        normalized = signal.normalized()
        ordered[normalized.key] = normalized
    return sorted(ordered.values(), key=accepted_sort_key)


def question_sort_key(entry: QuestionEntry) -> tuple[str, str]:
    return (entry.related_to.lower(), entry.topic.lower())


def accepted_sort_key(signal: AcceptedSignal) -> tuple[str, str]:
    return (signal.target.lower(), signal.signal.lower())


def split_markdown_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.replace("\\|", "|") for cell in stripped.split(" | ")]


def escape_table(value: str) -> str:
    return normalize_text(value).replace("|", "\\|").replace("\n", " ")


def normalize_text(value: object) -> str:
    normalized = re.sub(r"\s+", " ", str(value or "").strip())
    if normalized in {"", "-", "—"}:
        return ""
    return normalized
