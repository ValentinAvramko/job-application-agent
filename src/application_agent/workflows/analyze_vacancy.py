from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from application_agent.memory.models import WorkflowRun
from application_agent.memory.store import JsonMemoryStore
from application_agent.workflows.base import WorkflowResult
from application_agent.workflows.ingest_vacancy import IngestVacancyRequest, IngestVacancyWorkflow
from application_agent.workspace import WorkspaceLayout

ROLE_HINTS = {
    "CIO": (
        "cio",
        "chief information officer",
        "it director",
        "director of it",
        "директор по ит",
        "руководитель it",
        "digital transformation",
        "governance",
    ),
    "CTO": (
        "cto",
        "chief technology officer",
        "директор по технологиям",
        "technology strategy",
        "architecture",
        "platform strategy",
    ),
    "HoE": (
        "head of engineering",
        "vp of engineering",
        "vp engineering",
        "engineering director",
        "engineering excellence",
        "platform engineering",
    ),
    "HoD": (
        "head of development",
        "director of development",
        "директор по разработке",
        "руководитель разработки",
        "software development",
        "delivery ownership",
    ),
    "EM": (
        "engineering manager",
        "team lead",
        "people management",
        "cross-functional",
        "delivery manager",
        "performance review",
    ),
}

HIGH_PRIORITY_MARKERS = (
    "must",
    "required",
    "requirement",
    "опыт",
    "нужно",
    "обязательно",
    "responsible",
    "ownership",
    "lead",
)
LOW_PRIORITY_MARKERS = ("nice to have", "preferred", "будет плюсом", "желательно", "plus")
REQUIREMENT_MARKERS = HIGH_PRIORITY_MARKERS + (
    "experience",
    "expertise",
    "manage",
    "build",
    "develop",
    "design",
    "drive",
    "требования",
    "ожидания",
    "задачи",
    "будете",
    "отвечать",
)
STOPWORDS = {
    "and",
    "the",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "your",
    "you",
    "our",
    "will",
    "are",
    "как",
    "для",
    "это",
    "что",
    "или",
    "над",
    "под",
    "при",
    "team",
    "teams",
    "опыт",
    "работы",
    "будет",
    "нужно",
    "role",
    "позиция",
}


@dataclass
class AnalyzeVacancyRequest:
    vacancy_id: str | None = None
    company: str = ""
    position: str = ""
    source_text: str = ""
    source_url: str = ""
    source_channel: str = "Manual"
    source_type: str = ""
    language: str = ""
    country: str = ""
    work_mode: str = ""
    target_mode: str = ""
    selected_resume: str = ""
    include_employer_channels: bool = False


@dataclass
class RequirementAssessment:
    requirement: str
    priority: str
    evidence: str
    coverage: str
    notes: str


class AnalyzeVacancyWorkflow:
    name = "analyze-vacancy"
    description = "Создаёт стартовый fit-анализ вакансии и обновляет артефакты вакансии."

    def run(self, *, layout: WorkspaceLayout, store: JsonMemoryStore, request: AnalyzeVacancyRequest) -> WorkflowResult:
        started_at = datetime.now(timezone.utc).isoformat()
        bootstrap_artifacts: list[str] = []

        vacancy_id = request.vacancy_id
        if not vacancy_id:
            if not request.company.strip() or not request.position.strip():
                raise ValueError("analyze-vacancy requires either vacancy_id or company + position.")
            ingest_result = IngestVacancyWorkflow().run(
                layout=layout,
                store=store,
                request=IngestVacancyRequest(
                    company=request.company,
                    position=request.position,
                    source_text=request.source_text,
                    source_url=request.source_url,
                    source_channel=request.source_channel,
                    source_type=request.source_type,
                    language=request.language,
                    country=request.country,
                    work_mode=request.work_mode,
                    target_mode=request.target_mode,
                    include_employer_channels=request.include_employer_channels,
                ),
            )
            bootstrap_artifacts = list(ingest_result.artifacts)
            vacancy_id = store.load_task_memory().active_vacancy_id

        if not vacancy_id:
            raise ValueError("Unable to resolve vacancy_id for analyze-vacancy.")

        vacancy_dir = layout.vacancy_dir(vacancy_id)
        meta_path = vacancy_dir / "meta.yml"
        source_path = vacancy_dir / "source.md"
        analysis_path = vacancy_dir / "analysis.md"
        adoptions_path = vacancy_dir / "adoptions.md"

        if not meta_path.exists() or not source_path.exists():
            raise FileNotFoundError(f"Vacancy '{vacancy_id}' is missing meta.yml or source.md.")

        meta = load_simple_yaml(meta_path)
        raw_source = extract_raw_source(source_path)
        position = request.position.strip() or str(meta.get("position", "")).strip()
        company = request.company.strip() or str(meta.get("company", "")).strip()
        language = request.language or str(meta.get("language", "ru"))
        target_mode = request.target_mode or str(meta.get("target_mode", "balanced"))
        include_employer_channels = request.include_employer_channels or bool(meta.get("include_employer_channels", False))
        selected_resume = request.selected_resume.strip() or choose_resume(position=position, source_text=raw_source)

        resume_path = layout.root / "CV" / f"{selected_resume}.md"
        resume_text = resume_path.read_text(encoding="utf-8") if resume_path.exists() else ""

        requirements = extract_requirements(position=position, source_text=raw_source)
        assessments = [assess_requirement(requirement, resume_text) for requirement in requirements]

        current_fit = compute_fit_score(assessments)
        projected_fit = min(100, current_fit + estimate_fit_delta(assessments, target_mode))
        delta = projected_fit - current_fit

        strengths = build_strengths(assessments, selected_resume)
        gaps = build_gaps(assessments)
        cover_letter_notes = build_cover_letter_notes(company, position, strengths, gaps)
        resume_edit_notes = build_resume_edit_notes(gaps, selected_resume)
        contact_channels = build_contact_channels(meta, include_employer_channels)
        follow_up_questions = build_follow_up_questions(meta, raw_source, gaps)
        permanent_candidates = build_permanent_candidates(strengths)

        analysis_path.write_text(
            render_analysis(
                vacancy_id=vacancy_id,
                selected_resume=selected_resume,
                target_mode=target_mode,
                language=language,
                include_employer_channels=include_employer_channels,
                current_fit=current_fit,
                projected_fit=projected_fit,
                delta=delta,
                assessments=assessments,
                strengths=strengths,
                gaps=gaps,
                cover_letter_notes=cover_letter_notes,
                resume_edit_notes=resume_edit_notes,
                contact_channels=contact_channels,
                follow_up_questions=follow_up_questions,
            ),
            encoding="utf-8",
            newline="\n",
        )
        adoptions_path.write_text(
            render_adoptions(
                vacancy_id=vacancy_id,
                strengths=strengths,
                permanent_candidates=permanent_candidates,
                open_questions=(gaps[:2] + follow_up_questions[:2])[:4],
            ),
            encoding="utf-8",
            newline="\n",
        )

        meta["selected_resume"] = selected_resume
        meta["target_mode"] = target_mode
        meta["include_employer_channels"] = include_employer_channels
        meta["status"] = "analyzed"
        meta["analyzed_at"] = datetime.now(timezone.utc).isoformat()
        write_simple_yaml(meta_path, meta)

        artifacts = dedupe_paths(bootstrap_artifacts + [str(meta_path), str(analysis_path), str(adoptions_path)])
        store.remember_task(self.name, vacancy_id, artifacts)
        store.append_run(
            WorkflowRun(
                workflow=self.name,
                status="completed",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc).isoformat(),
                artifacts=artifacts,
                summary=f"Built first-pass vacancy analysis for {vacancy_id} using {selected_resume}.",
            )
        )
        return WorkflowResult(
            workflow=self.name,
            status="completed",
            summary=f"Vacancy analysis prepared for {vacancy_id} with resume {selected_resume}.",
            artifacts=artifacts,
        )


def dedupe_paths(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        result.append(path)
    return result


def choose_resume(*, position: str, source_text: str) -> str:
    combined = f"{position}\n{source_text}".lower()
    position_lower = position.lower()
    scores: dict[str, int] = {}
    for role, hints in ROLE_HINTS.items():
        position_hits = sum(3 for hint in hints if hint in position_lower)
        text_hits = sum(1 for hint in hints if hint in combined)
        scores[role] = position_hits + text_hits

    best_role = max(scores, key=scores.get)
    if scores[best_role] == 0:
        if "cto" in position_lower or "technology" in position_lower:
            return "CTO"
        if "cio" in position_lower or "директор по ит" in position_lower:
            return "CIO"
        if "vp" in position_lower or "engineering" in position_lower:
            return "HoE"
        if "development" in position_lower or "разработк" in position_lower:
            return "HoD"
        return "EM"
    return best_role


def extract_requirements(*, position: str, source_text: str) -> list[str]:
    candidates: list[tuple[int, str]] = []
    raw_chunks = re.split(r"[\n\r]+|(?<=[.!?])\s+", source_text)
    for chunk in raw_chunks:
        cleaned = normalize_requirement_line(chunk)
        if len(cleaned) < 24:
            continue
        lower = cleaned.lower()
        score = 0
        if any(marker in lower for marker in REQUIREMENT_MARKERS):
            score += 4
        if any(token in lower for token in position.lower().split()):
            score += 1
        if len(cleaned) <= 160:
            score += 1
        candidates.append((score, cleaned))

    unique: list[str] = []
    seen: set[str] = set()
    for _, candidate in sorted(candidates, key=lambda item: (-item[0], item[1])):
        key = candidate.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
        if len(unique) == 8:
            break

    if unique:
        return unique

    return [
        f"Leadership scope and delivery ownership for the {position or 'target'} role",
        "Technical decision-making and architectural influence",
        "Cross-functional stakeholder management and business alignment",
    ]


def normalize_requirement_line(value: str) -> str:
    cleaned = value.strip()
    cleaned = re.sub(r"^[\-\*\d\.\)\s]+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def assess_requirement(requirement: str, resume_text: str) -> RequirementAssessment:
    keywords = extract_keywords(requirement)
    resume_lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
    matched_lines = [line for line in resume_lines if any(keyword in line.lower() for keyword in keywords)]

    if len(matched_lines) >= 2:
        coverage = "strong"
    elif len(matched_lines) == 1:
        coverage = "partial"
    else:
        coverage = "gap"

    evidence = matched_lines[0] if matched_lines else "Нужен явный сигнал в выбранном резюме."
    priority = classify_priority(requirement)
    if coverage == "strong":
        notes = "Есть прямой сигнал в текущем резюме."
    elif coverage == "partial":
        notes = "Сигнал есть, но его стоит сделать заметнее и ближе к формулировке вакансии."
    else:
        notes = "Нужно либо добавить переносимый опыт, либо честно закрыть пробел в сопроводительном письме."

    return RequirementAssessment(
        requirement=requirement,
        priority=priority,
        evidence=evidence,
        coverage=coverage,
        notes=notes,
    )


def extract_keywords(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Zа-яА-ЯёЁ][a-zA-Zа-яА-ЯёЁ\-\+]{2,}", text.lower())
    keywords: list[str] = []
    for word in words:
        if word in STOPWORDS or word in keywords:
            continue
        keywords.append(word)
    return keywords[:6] or ["leadership", "delivery"]


def classify_priority(requirement: str) -> str:
    lower = requirement.lower()
    if any(marker in lower for marker in LOW_PRIORITY_MARKERS):
        return "low"
    if any(marker in lower for marker in HIGH_PRIORITY_MARKERS):
        return "high"
    return "medium"


def compute_fit_score(assessments: list[RequirementAssessment]) -> int:
    if not assessments:
        return 0
    weight = {"strong": 1.0, "partial": 0.6, "gap": 0.2}
    score = sum(weight[item.coverage] for item in assessments) / len(assessments)
    return round(score * 100)


def estimate_fit_delta(assessments: list[RequirementAssessment], target_mode: str) -> int:
    base = sum(6 for item in assessments if item.coverage == "gap")
    base += sum(3 for item in assessments if item.coverage == "partial")
    mode_bonus = {"conservative": 0, "balanced": 4, "aggressive": 8}.get(target_mode, 4)
    return min(25, base + mode_bonus)


def build_strengths(assessments: list[RequirementAssessment], selected_resume: str) -> list[str]:
    strengths = [
        f"{item.requirement} -> подтверждается в `{selected_resume}.md`."
        for item in assessments
        if item.coverage == "strong"
    ]
    return strengths[:4] or [f"Выбранное резюме `{selected_resume}.md` даёт базовый управленческий контур для роли."]


def build_gaps(assessments: list[RequirementAssessment]) -> list[str]:
    gaps = [
        f"{item.requirement} -> нужен более явный сигнал или честное позиционирование."
        for item in assessments
        if item.coverage != "strong"
    ]
    return gaps[:4] or ["Критичных пробелов в стартовом проходе не найдено, но формулировки можно сделать точнее."]


def build_cover_letter_notes(company: str, position: str, strengths: list[str], gaps: list[str]) -> list[str]:
    notes = [f"Открыть письмо через контекст роли `{position}` и ценность для `{company or 'компании'}`."]
    if strengths:
        notes.append(f"Подсветить один сильный аргумент из fit: {trim_signal(strengths[0])}")
    if gaps:
        notes.append(f"Один спорный пункт заранее переупаковать как transferable experience: {trim_signal(gaps[0])}")
    return notes


def build_resume_edit_notes(gaps: list[str], selected_resume: str) -> list[str]:
    notes = [f"Проверить, можно ли добавить в `{selected_resume}.md`: {trim_signal(gap)}" for gap in gaps[:3]]
    if not notes:
        notes.append(f"В `{selected_resume}.md` можно сделать формулировки ближе к языку вакансии.")
    return notes


def build_contact_channels(meta: dict[str, object], include_employer_channels: bool) -> list[str]:
    if not include_employer_channels:
        return ["Каналы работодателя не запрашивались в этом запуске."]

    channels = []
    source_url = str(meta.get("source_url", "") or "").strip()
    source_channel = str(meta.get("source_channel", "") or "").strip()
    if source_channel:
        channels.append(f"Исходный канал вакансии: {source_channel}.")
    if source_url and source_url != "null":
        channels.append(f"Проверить актуальность карточки по ссылке: {source_url}.")
    channels.append("Сверить, есть ли прямой recruiter или hiring manager контакт до отправки отклика.")
    return channels


def build_follow_up_questions(meta: dict[str, object], raw_source: str, gaps: list[str]) -> list[str]:
    questions: list[str] = []
    if not raw_source.strip():
        questions.append("Нужен полный текст вакансии или хотя бы блок requirements/responsibilities.")
    if str(meta.get("country", "")).strip() in {"", "Не указано"}:
        questions.append("Уточнить географию и ожидания по legal / relocation.")
    if str(meta.get("work_mode", "")).strip() in {"", "Не указано"}:
        questions.append("Уточнить формат работы: onsite / hybrid / remote.")
    if gaps:
        questions.append(f"Проверить, действительно ли обязателен пункт: {trim_signal(gaps[0])}")
    return questions or ["Дополнительных уточнений для стартового прохода пока нет."]


def build_permanent_candidates(strengths: list[str]) -> list[str]:
    candidates = [trim_signal(item) for item in strengths[:3]]
    return candidates or ["Сильные сигналы проявятся после нескольких обработанных вакансий."]


def render_analysis(
    *,
    vacancy_id: str,
    selected_resume: str,
    target_mode: str,
    language: str,
    include_employer_channels: bool,
    current_fit: int,
    projected_fit: int,
    delta: int,
    assessments: list[RequirementAssessment],
    strengths: list[str],
    gaps: list[str],
    cover_letter_notes: list[str],
    resume_edit_notes: list[str],
    contact_channels: list[str],
    follow_up_questions: list[str],
) -> str:
    lines = [
        "# Vacancy Analysis",
        "",
        "## Snapshot",
        "",
        f"- Vacancy ID: {vacancy_id}",
        f"- Selected Resume: {selected_resume}",
        f"- Target Mode: {target_mode}",
        f"- Language: {language}",
        f"- Include Employer Channels: {str(include_employer_channels).lower()}",
        "",
        "## Fit Analysis: Current Resume",
        "",
        f"- Overall Fit: {current_fit}/100",
        f"- Fit Summary: Стартовая эвристика показывает опору на `{selected_resume}.md` и {coverage_summary(assessments)}.",
        "",
        "## Fit Analysis: After Proposed Resume Changes",
        "",
        f"- Projected Fit: {projected_fit}/100",
        f"- Delta: +{delta}",
        "- Notes: Прогноз построен по тем пунктам, где формулировки можно приблизить к языку вакансии без искажения опыта.",
        "",
        "## Requirement Matrix",
        "",
        "| Requirement | Priority | Evidence | Coverage | Notes |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in assessments:
        lines.append(
            f"| {escape_table(item.requirement)} | {item.priority} | {escape_table(item.evidence)} | {item.coverage} | {escape_table(item.notes)} |"
        )

    lines.extend(
        [
            "",
            "## Strengths",
            "",
            *format_bullets(strengths),
            "",
            "## Gaps",
            "",
            *format_bullets(gaps),
            "",
            "## Cover Letter Notes",
            "",
            *format_bullets(cover_letter_notes),
            "",
            "## Resume Editing Notes",
            "",
            *format_bullets(resume_edit_notes),
            "",
            "## Employer Contact Channels (Optional)",
            "",
            *format_bullets(contact_channels),
            "",
            "## Follow-up Questions",
            "",
            *format_bullets(follow_up_questions),
            "",
        ]
    )
    return "\n".join(lines)


def render_adoptions(*, vacancy_id: str, strengths: list[str], permanent_candidates: list[str], open_questions: list[str]) -> str:
    return "\n".join(
        [
            "# Vacancy Adoptions",
            "",
            f"- Vacancy ID: {vacancy_id}",
            "",
            "## Temporary Signals",
            "",
            *format_bullets(strengths[:3]),
            "",
            "## Permanent Candidates",
            "",
            *format_bullets(permanent_candidates),
            "",
            "## Open Questions",
            "",
            *format_bullets(open_questions),
            "",
        ]
    )


def format_bullets(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] or ["- "]


def trim_signal(value: str) -> str:
    trimmed = value
    for suffix in (
        " -> подтверждается в `CIO.md`.",
        " -> подтверждается в `CTO.md`.",
        " -> подтверждается в `HoE.md`.",
        " -> подтверждается в `HoD.md`.",
        " -> подтверждается в `EM.md`.",
        " -> нужен более явный сигнал или честное позиционирование.",
    ):
        trimmed = trimmed.replace(suffix, "")
    return trimmed


def coverage_summary(assessments: list[RequirementAssessment]) -> str:
    strong = sum(1 for item in assessments if item.coverage == "strong")
    partial = sum(1 for item in assessments if item.coverage == "partial")
    gaps = sum(1 for item in assessments if item.coverage == "gap")
    return f"{strong} strong / {partial} partial / {gaps} gap signal(s)"


def escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def extract_raw_source(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    marker = "## Raw Text"
    if marker not in text:
        return text.strip()
    return text.split(marker, maxsplit=1)[1].strip()


def load_simple_yaml(path: Path) -> dict[str, object]:
    payload: dict[str, object] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, raw_value = stripped.split(":", maxsplit=1)
        payload[key.strip()] = parse_simple_scalar(raw_value.strip())
    return payload


def parse_simple_scalar(value: str) -> object:
    if value == "null":
        return None
    if value in {"true", "false"}:
        return value == "true"
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    return value


def write_simple_yaml(path: Path, payload: dict[str, object]) -> None:
    preferred_order = [
        "vacancy_id",
        "source_type",
        "source_url",
        "source_channel",
        "company",
        "position",
        "language",
        "country",
        "work_mode",
        "is_active",
        "ingested_at",
        "analyzed_at",
        "selected_resume",
        "target_mode",
        "include_employer_channels",
        "excel_row",
        "status",
        "notes",
    ]
    keys = [key for key in preferred_order if key in payload] + [key for key in payload if key not in preferred_order]
    lines = [f"{key}: {dump_simple_scalar(payload[key])}" for key in keys]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def dump_simple_scalar(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return str(value).lower()
    if value == "":
        return '""'
    return str(value)
