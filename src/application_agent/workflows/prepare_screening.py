from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

from application_agent.memory.models import WorkflowRun
from application_agent.memory.store import JsonMemoryStore
from application_agent.utils.placeholders import is_unspecified
from application_agent.utils.simple_yaml import load_simple_yaml, write_simple_yaml
from application_agent.workflows.analyze_vacancy import (
    RequirementAssessment,
    assess_requirement,
    choose_resume,
    dedupe_paths,
    extract_raw_source,
    extract_requirements,
)
from application_agent.workflows.base import WorkflowResult
from application_agent.workspace import WorkspaceLayout


@dataclass
class PrepareScreeningRequest:
    vacancy_id: str = ""
    selected_resume: str = ""
    output_language: str = ""
    preparation_depth: str = ""


class PrepareScreeningWorkflow:
    name = "prepare-screening"
    description = "Готовит screening.md для первичного собеседования по уже собранной вакансии."

    def run(
        self, *, layout: WorkspaceLayout, store: JsonMemoryStore, request: PrepareScreeningRequest
    ) -> WorkflowResult:
        started_at = datetime.now(timezone.utc).isoformat()
        vacancy_id = request.vacancy_id.strip()
        if not vacancy_id:
            raise ValueError("prepare-screening requires a non-empty vacancy_id.")

        vacancy_dir = layout.vacancy_dir(vacancy_id)
        meta_path = vacancy_dir / "meta.yml"
        source_path = vacancy_dir / "source.md"
        analysis_path = vacancy_dir / "analysis.md"
        screening_path = vacancy_dir / "screening.md"

        if not vacancy_dir.exists():
            raise FileNotFoundError(
                f"Vacancy '{vacancy_id}' is missing from vacancies/. Runtime memory or the provided vacancy_id is stale; "
                "run ingest-vacancy again or pass an existing --vacancy-id."
            )

        if not meta_path.exists() or not source_path.exists() or not analysis_path.exists():
            raise FileNotFoundError(
                f"Vacancy '{vacancy_id}' is incomplete: meta.yml, source.md, or analysis.md is missing. "
                "Run ingest-vacancy/analyze-vacancy to rebuild the vacancy scaffold before prepare-screening."
            )

        meta = load_simple_yaml(meta_path)
        raw_source = extract_raw_source(source_path)
        analysis_text = analysis_path.read_text(encoding="utf-8")

        position = str(meta.get("position", "") or "").strip()
        company = str(meta.get("company", "") or "").strip()
        output_language = normalize_language(request.output_language or str(meta.get("language", "ru")))
        preparation_depth = normalize_preparation_depth(request.preparation_depth)
        selected_resume = resolve_selected_resume(
            explicit_resume=request.selected_resume,
            meta_resume=str(meta.get("selected_resume", "") or ""),
            position=position,
            raw_source=raw_source,
        )

        resume_path = layout.resumes_dir / f"{selected_resume}.md"
        if not resume_path.exists():
            raise FileNotFoundError(
                f"Selected resume '{selected_resume}' is missing from resumes/. "
                "Add the resume file or pass --selected-resume with an existing role resume."
            )

        resume_text = resume_path.read_text(encoding="utf-8")
        requirements = extract_requirements(position=position, source_text=raw_source)
        assessments = [assess_requirement(requirement, resume_text) for requirement in requirements]
        strength_signals = collect_strength_signals(analysis_text, assessments)
        gap_signals = collect_gap_signals(analysis_text, assessments)
        recruiter_questions = build_recruiter_questions(assessments, gap_signals, output_language, preparation_depth)
        your_questions = build_your_questions(analysis_text, meta, output_language, preparation_depth)
        resume_highlights = extract_resume_highlights(resume_text, limit=depth_limit(preparation_depth) + 1)
        intro_steps = build_intro_steps(
            position=position,
            company=company,
            selected_resume=selected_resume,
            resume_text=resume_text,
            strength_signals=strength_signals,
            resume_highlights=resume_highlights,
            output_language=output_language,
        )
        storyline_steps = build_storyline_steps(
            position=position,
            company=company,
            strength_signals=strength_signals,
            gap_signals=gap_signals,
            output_language=output_language,
        )
        risk_notes = build_risk_notes(meta, gap_signals, output_language)
        prep_checklist = build_prep_checklist(
            selected_resume=selected_resume,
            resume_path=str(resume_path),
            source_path=str(source_path),
            analysis_path=str(analysis_path),
            output_language=output_language,
        )

        screening_path.write_text(
            render_screening(
                vacancy_id=vacancy_id,
                company=company,
                position=position,
                selected_resume=selected_resume,
                output_language=output_language,
                preparation_depth=preparation_depth,
                strength_signals=strength_signals,
                intro_steps=intro_steps,
                storyline_steps=storyline_steps,
                recruiter_questions=recruiter_questions,
                your_questions=your_questions,
                risk_notes=risk_notes,
                prep_checklist=prep_checklist,
            ),
            encoding="utf-8",
            newline="\n",
        )

        meta["selected_resume"] = selected_resume
        meta["status"] = "screening_prepared"
        meta["screening_prepared_at"] = datetime.now(timezone.utc).isoformat()
        write_simple_yaml(meta_path, meta)

        artifacts = dedupe_paths([str(meta_path), str(screening_path)])
        store.remember_task(self.name, vacancy_id, artifacts)
        store.append_run(
            WorkflowRun(
                workflow=self.name,
                status="completed",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc).isoformat(),
                artifacts=artifacts,
                summary=f"Подготовлен screening-пакет для вакансии {vacancy_id} на основе резюме {selected_resume}.",
            )
        )
        return WorkflowResult(
            workflow=self.name,
            status="completed",
            summary=f"Подготовлен screening-пакет для вакансии {vacancy_id} с опорой на резюме {selected_resume}.",
            artifacts=artifacts,
        )


def normalize_language(value: str) -> str:
    normalized = value.strip().lower()
    if normalized.startswith("en"):
        return "en"
    return "ru"


def normalize_preparation_depth(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"brief", "standard", "deep"}:
        return normalized
    return "standard"


def depth_limit(preparation_depth: str) -> int:
    return {"brief": 3, "standard": 5, "deep": 7}.get(preparation_depth, 5)


def resolve_selected_resume(*, explicit_resume: str, meta_resume: str, position: str, raw_source: str) -> str:
    if explicit_resume.strip():
        return explicit_resume.strip()
    if meta_resume.strip() and meta_resume.strip() != "undecided":
        return meta_resume.strip()
    return choose_resume(position=position, source_text=raw_source)


def collect_strength_signals(analysis_text: str, assessments: list[RequirementAssessment]) -> list[str]:
    items = extract_section_bullets(analysis_text, "## Сильные стороны")
    if items:
        return items[:4]
    derived = [trim_signal(item.evidence) for item in assessments if item.coverage == "full"]
    return unique_nonempty(derived)[:4] or ["Резюме уже даёт базовый управленческий и delivery-контур для первого разговора."]


def collect_gap_signals(analysis_text: str, assessments: list[RequirementAssessment]) -> list[str]:
    items = extract_section_bullets(analysis_text, "## Пробелы")
    if items:
        return items[:4]
    derived = [item.requirement for item in assessments if item.coverage != "full"]
    return unique_nonempty(derived)[:4] or ["Критичных пробелов для первичного разговора не найдено, но формулировки стоит уточнять по ходу интервью."]


def build_recruiter_questions(
    assessments: list[RequirementAssessment], gap_signals: list[str], output_language: str, preparation_depth: str
) -> list[str]:
    limit = depth_limit(preparation_depth)
    questions: list[str] = []
    for item in assessments[:limit]:
        if output_language == "en":
            if item.coverage == "full":
                questions.append(
                    f"Question: Tell us about your experience with {trim_signal(item.requirement)}. "
                    f"Anchor: {trim_signal(item.evidence)}."
                )
            else:
                questions.append(
                    f"Question: How do you handle the area around {trim_signal(item.requirement)}? "
                    "Anchor: be explicit about adjacent experience and how you would close the gap."
                )
            continue

        if item.coverage == "full":
            questions.append(
                f"Вопрос: расскажите про опыт в зоне «{trim_signal(item.requirement)}». "
                f"Опора для ответа: {trim_signal(item.evidence)}."
            )
        else:
            questions.append(
                f"Вопрос: как вы закрываете или компенсируете зону «{trim_signal(item.requirement)}»? "
                "Опора для ответа: честно обозначить границу опыта и перевести разговор в смежные кейсы."
            )

    if questions:
        return questions

    fallback = gap_signals[0] if gap_signals else "наиболее важные ожидания вакансии"
    if output_language == "en":
        return [f"Question: Why are you a good fit for this role? Anchor: connect your background to {trim_signal(fallback)}."]
    return [f"Вопрос: почему вы подходите на эту роль? Опора для ответа: связать свой опыт с темой «{trim_signal(fallback)}»."]


def build_your_questions(
    analysis_text: str, meta: dict[str, object], output_language: str, preparation_depth: str
) -> list[str]:
    items = extract_section_bullets(analysis_text, "## Вопросы на уточнение")
    limit = max(3, min(depth_limit(preparation_depth), 5))
    result = items[:limit]

    if is_unspecified(str(meta.get("work_mode", "") or "").strip()):
        result.append(
            "Уточнить формат работы: офис, гибрид, удалённо." if output_language == "ru" else "Clarify the work mode: office, hybrid, or remote."
        )
    if is_unspecified(str(meta.get("country", "") or "").strip()):
        result.append(
            "Уточнить географию, юрисдикцию и ограничения по найму."
            if output_language == "ru"
            else "Clarify geography, hiring jurisdiction, and any legal constraints."
        )

    defaults = (
        [
            "Какие первые 3-6 месяцев считаются успешными для этой роли?",
            "Как сейчас устроена команда и кому будет репортить эта позиция?",
            "Где у компании главный технологический или организационный bottleneck?",
        ]
        if output_language == "ru"
        else [
            "What would success look like in the first 3-6 months?",
            "How is the team structured today and who does this role report to?",
            "What is the main technology or organizational bottleneck right now?",
        ]
    )
    result.extend(defaults)
    return unique_nonempty(result)[:limit]


def extract_resume_highlights(resume_text: str, limit: int) -> list[str]:
    current_heading = ""
    scored: list[tuple[int, int, str]] = []
    for index, raw_line in enumerate(resume_text.splitlines()):
        line = raw_line.strip()
        if line.startswith("#"):
            current_heading = line.lower()
            continue
        if not line.startswith("- "):
            continue
        item = trim_signal(line[2:])
        lower = item.lower()
        if len(item) < 24:
            continue
        if any(marker in lower for marker in ("телефон", "e-mail", "telegram", "linkedin", "whatsapp", "email")):
            continue
        score = 0
        if any(marker in current_heading for marker in ("достижен", "achievement", "опыт", "experience")):
            score += 3
        if any(char.isdigit() for char in item):
            score += 2
        if any(marker in lower for marker in ("руковод", "управ", "lead", "delivery", "architecture", "архитект")):
            score += 1
        scored.append((score, index, item))

    ordered = [item for _, _, item in sorted(scored, key=lambda row: (-row[0], row[1]))]
    return unique_nonempty(ordered)[:limit]


def build_intro_steps(
    *,
    position: str,
    company: str,
    selected_resume: str,
    resume_text: str,
    strength_signals: list[str],
    resume_highlights: list[str],
    output_language: str,
) -> list[str]:
    profile_summary = extract_profile_summary(resume_text)
    primary_signal = trim_signal(strength_signals[0] if strength_signals else "")
    highlight = trim_signal(resume_highlights[0] if resume_highlights else "")

    if output_language == "en":
        steps = [
            f"I am approaching this conversation as a candidate for the {position or 'target role'} position with a {selected_resume} resume foundation.",
            profile_summary
            or "My background is strongest where engineering leadership, delivery discipline, and cross-functional coordination need to come together.",
            f"The most relevant proof point I would surface early is: {primary_signal or highlight or 'hands-on leadership in similar delivery contexts'}.",
            f"I would close the intro by connecting that experience to the needs of {company or 'the company'} and invite the recruiter to focus on the highest-priority part of the role.",
        ]
        return unique_nonempty(steps)

    steps = [
        f"Я иду на разговор как кандидат на роль {position or 'целевой позиции'} с опорой на резюме {selected_resume}.",
        profile_summary
        or "Мой базовый контур - инженерное руководство, delivery-дисциплина и связка между командой, технологиями и бизнесом.",
        f"В первые 30-40 секунд стоит подсветить главный релевантный сигнал: {primary_signal or highlight or 'подтверждённый опыт управленческого и delivery-лидерства'}.",
        f"Закрыть самопрезентацию лучше связкой с потребностью {company or 'компании'} и приглашением обсудить самый критичный для роли участок ответственности.",
    ]
    return unique_nonempty(steps)


def build_storyline_steps(
    *,
    position: str,
    company: str,
    strength_signals: list[str],
    gap_signals: list[str],
    output_language: str,
) -> list[str]:
    first_strength = trim_signal(strength_signals[0] if strength_signals else "")
    second_strength = trim_signal(strength_signals[1] if len(strength_signals) > 1 else "")
    first_gap = trim_signal(gap_signals[0] if gap_signals else "")

    if output_language == "en":
        steps = [
            f"Open with concise positioning: why the {position or 'role'} scope matches your background.",
            f"Move quickly to one proof point: {first_strength or 'a concrete delivery or leadership case'}.",
            f"Add a second signal that broadens the picture: {second_strength or 'team scaling, architecture, or process improvement experience'}.",
            f"If asked about a weaker area, address it directly and reframe it through adjacent experience: {first_gap or 'the main uncertainty from the vacancy brief'}.",
            f"Close by checking whether the biggest challenge at {company or 'the company'} matches the picture from the vacancy description.",
        ]
        return unique_nonempty(steps)

    steps = [
        f"Открыть разговор коротким позиционированием: почему контур роли {position or 'позиции'} логично продолжает ваш опыт.",
        f"Сразу перейти к одному доказательству релевантности: {first_strength or 'конкретному кейсу про delivery или лидерство'}.",
        f"Затем расширить картину вторым сигналом: {second_strength or 'масштабирование команды, архитектурные решения или улучшение процессов'}.",
        f"Если всплывёт слабая зона, не спорить с ней, а честно перевести в смежный опыт: {first_gap or 'главную неопределённость из вакансии'}.",
        f"Финал разговора: сверить, действительно ли главный вызов {company or 'компании'} совпадает с тем, что видно из вакансии.",
    ]
    return unique_nonempty(steps)


def build_risk_notes(meta: dict[str, object], gap_signals: list[str], output_language: str) -> list[str]:
    items: list[str] = []
    if gap_signals:
        if output_language == "en":
            items.append(f"Be ready for a follow-up on the weakest area: {trim_signal(gap_signals[0])}.")
        else:
            items.append(f"Подготовить спокойный ответ по самой спорной зоне: {trim_signal(gap_signals[0])}.")
    if is_unspecified(str(meta.get("work_mode", "") or "").strip()):
        items.append(
            "Work format is still unspecified; do not assume remote/hybrid conditions."
            if output_language == "en"
            else "Формат работы пока не уточнён; не стоит заранее предполагать удалёнку или гибрид."
        )
    if is_unspecified(str(meta.get("country", "") or "").strip()):
        items.append(
            "Location and hiring jurisdiction are still open questions."
            if output_language == "en"
            else "География и юридический контур найма пока остаются открытым вопросом."
        )
    items.append(
        "Do not over-promise missing experience; anchor the conversation in verified cases."
        if output_language == "en"
        else "Не обещать неподтверждённый опыт; держать разговор на верифицируемых кейсах."
    )
    return unique_nonempty(items)


def build_prep_checklist(
    *, selected_resume: str, resume_path: str, source_path: str, analysis_path: str, output_language: str
) -> list[str]:
    if output_language == "en":
        return [
            f"Re-read the selected resume before the call: {resume_path}",
            f"Refresh the original vacancy wording: {source_path}",
            f"Refresh the latest vacancy analysis and gap notes: {analysis_path}",
            "Prepare one short metric-driven example and one team/process example for the first 10 minutes.",
        ]
    return [
        f"Перед звонком перечитать выбранное резюме {selected_resume}: {resume_path}",
        f"Освежить формулировки исходной вакансии: {source_path}",
        f"Пересмотреть актуальный анализ вакансии и пробелы: {analysis_path}",
        "Подготовить один короткий кейс с цифрами и один кейс про команду/процессы на первые 10 минут разговора.",
    ]


def render_screening(
    *,
    vacancy_id: str,
    company: str,
    position: str,
    selected_resume: str,
    output_language: str,
    preparation_depth: str,
    strength_signals: list[str],
    intro_steps: list[str],
    storyline_steps: list[str],
    recruiter_questions: list[str],
    your_questions: list[str],
    risk_notes: list[str],
    prep_checklist: list[str],
) -> str:
    heading = "Screening Preparation" if output_language == "en" else "Подготовка к screening"
    passport = "Passport" if output_language == "en" else "Паспорт"
    strengths = "Positioning Signals" if output_language == "en" else "Что стоит подсветить"
    intro = "Mini Self-Intro Script" if output_language == "en" else "Мини-сценарий самопрезентации"
    storyline = "Interview Storyline" if output_language == "en" else "Сценарий разговора"
    recruiter = "Likely Screening Questions" if output_language == "en" else "Вероятные вопросы на screening"
    your = "Questions To Ask" if output_language == "en" else "Что спросить в ответ"
    risks = "Risk Notes" if output_language == "en" else "Риски и аккуратные зоны"
    checklist = "Prep Checklist" if output_language == "en" else "Чек-лист перед звонком"

    lines = [
        f"# {heading}",
        "",
        f"## {passport}",
        "",
        f"- {'Vacancy ID' if output_language == 'en' else 'ID вакансии'}: {vacancy_id}",
        f"- {'Company' if output_language == 'en' else 'Компания'}: {company or ('n/a' if output_language == 'en' else 'нет данных')}",
        f"- {'Position' if output_language == 'en' else 'Позиция'}: {position or ('n/a' if output_language == 'en' else 'нет данных')}",
        f"- {'Selected resume' if output_language == 'en' else 'Выбранное резюме'}: {selected_resume}",
        f"- {'Output language' if output_language == 'en' else 'Язык результата'}: {output_language}",
        f"- {'Preparation depth' if output_language == 'en' else 'Глубина подготовки'}: {preparation_depth}",
        "",
        f"## {strengths}",
        "",
        *format_bullets(strength_signals),
        "",
        f"## {intro}",
        "",
        *format_numbered(intro_steps),
        "",
        f"## {storyline}",
        "",
        *format_numbered(storyline_steps),
        "",
        f"## {recruiter}",
        "",
        *format_numbered(recruiter_questions),
        "",
        f"## {your}",
        "",
        *format_numbered(your_questions),
        "",
        f"## {risks}",
        "",
        *format_bullets(risk_notes),
        "",
        f"## {checklist}",
        "",
        *format_bullets(prep_checklist),
        "",
    ]
    return "\n".join(lines)


def extract_profile_summary(resume_text: str) -> str:
    in_profile = False
    paragraphs: list[str] = []
    for raw_line in resume_text.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            lower = line.lower()
            in_profile = "о себе" in lower or "profile" in lower
            continue
        if not in_profile or not line or line.startswith("- "):
            continue
        paragraphs.append(trim_signal(line))
        if len(paragraphs) == 2:
            break
    return " ".join(paragraphs)


def extract_section_bullets(markdown: str, heading: str) -> list[str]:
    heading_text = heading.lstrip("#").strip()
    pattern = re.compile(rf"^#+\s+{re.escape(heading_text)}(?:\s+.*)?$", re.MULTILINE)
    match = pattern.search(markdown)
    if not match:
        return []
    section = markdown[match.end() :]
    next_heading = re.search(r"\n#+\s", section)
    if next_heading:
        section = section[: next_heading.start()]
    items: list[str] = []
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line.startswith("- "):
            continue
        item = trim_signal(line[2:])
        if item:
            items.append(item)
    return unique_nonempty(items)


def format_bullets(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] or ["- "]


def format_numbered(items: list[str]) -> list[str]:
    return [f"{index}. {item}" for index, item in enumerate(items, start=1)] or ["1. "]


def trim_signal(value: str) -> str:
    trimmed = value.strip()
    trimmed = re.sub(r"^[\-\*\d\.\)\s]+", "", trimmed)
    trimmed = re.sub(r"\s+", " ", trimmed)
    if trimmed in {"", "—", "-"}:
        return ""
    return trimmed.rstrip(".")


def unique_nonempty(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        cleaned = trim_signal(item)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result
