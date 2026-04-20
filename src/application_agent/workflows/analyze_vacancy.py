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
    "what",
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
    "makes",
    "great",
    "fit",
    "year",
    "experience",
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
    source_requirement: str
    requirement: str
    priority: str
    evidence: str
    coverage: str
    notes: str


class AnalyzeVacancyWorkflow:
    name = "analyze-vacancy"
    description = "Создаёт стартовый анализ соответствия вакансии и обновляет артефакты вакансии."

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
        master_resume_recommendations = build_master_resume_recommendations(assessments, selected_resume)
        profile_updates = build_profile_updates(position, company, strengths, gaps)
        competency_updates = build_competency_updates(assessments)
        experience_updates = build_experience_updates(assessments, selected_resume)

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
                master_resume_recommendations=master_resume_recommendations,
                profile_updates=profile_updates,
                competency_updates=competency_updates,
                experience_updates=experience_updates,
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
                summary=f"Собран стартовый анализ вакансии {vacancy_id} на основе резюме {selected_resume}.",
            )
        )
        return WorkflowResult(
            workflow=self.name,
            status="completed",
            summary=f"Подготовлен анализ вакансии {vacancy_id} с резюме {selected_resume}.",
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
        f"Зона лидерства и ответственность за delivery для роли {position or 'целевой роли'}",
        "Техническое принятие решений и влияние на архитектуру",
        "Кросс-функциональное взаимодействие и связка с бизнесом",
    ]


def normalize_requirement_line(value: str) -> str:
    cleaned = value.strip()
    cleaned = re.sub(r"^[\-\*\d\.\)\s]+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def assess_requirement(requirement: str, resume_text: str) -> RequirementAssessment:
    keywords = extract_keywords(requirement)
    resume_lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
    matched_lines = [line for line in resume_lines if line_matches_keywords(line, keywords)]
    display_requirement = localize_requirement(requirement)

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
        source_requirement=requirement,
        requirement=display_requirement,
        priority=priority,
        evidence=evidence,
        coverage=coverage,
        notes=notes,
    )


def extract_keywords(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Zа-яА-ЯёЁ][a-zA-Zа-яА-ЯёЁ\-\+]{2,}", text.lower())
    keywords: list[str] = []
    for word in words:
        normalized = normalize_token(word)
        if normalized in STOPWORDS or normalized in keywords:
            continue
        keywords.append(normalized)
    return keywords[:6] or ["leadership", "delivery"]


def line_matches_keywords(line: str, keywords: list[str]) -> bool:
    tokens = {normalize_token(token) for token in re.findall(r"[a-zA-Zа-яА-ЯёЁ][a-zA-Zа-яА-ЯёЁ\-\+]{2,}", line.lower())}
    tokens.discard("")
    if not tokens:
        return False
    matched = [keyword for keyword in keywords if keyword in tokens]
    return len(matched) >= 2 or (len(matched) == 1 and len(keywords) <= 3)


def normalize_token(token: str) -> str:
    normalized = token.lower().strip("-+ ")
    english_aliases = {
        "led": "lead",
        "leading": "lead",
        "built": "build",
        "building": "build",
        "driven": "drive",
        "driving": "drive",
        "drove": "drive",
        "managing": "manage",
        "managed": "manage",
        "teams": "team",
        "managers": "manager",
        "partnerships": "partnership",
        "processes": "process",
        "services": "service",
        "agents": "agent",
        "years": "year",
    }
    if normalized in english_aliases:
        return english_aliases[normalized]
    if normalized.endswith("'s"):
        normalized = normalized[:-2]
    if len(normalized) > 4 and normalized.endswith("ies"):
        normalized = normalized[:-3] + "y"
    elif len(normalized) > 4 and normalized.endswith("es"):
        normalized = normalized[:-2]
    elif len(normalized) > 3 and normalized.endswith("s"):
        normalized = normalized[:-1]
    return english_aliases.get(normalized, normalized)


def localize_requirement(requirement: str) -> str:
    if contains_cyrillic(requirement):
        return clean_requirement_text(requirement)

    lowered = requirement.strip().rstrip(".")
    replacements = [
        ("As the Engineering Manager, you will ", ""),
        ("What makes you a great fit:", ""),
        ("Challenges that await you:", ""),
        ("Lead the development and optimization of the workspace for collection and telesales agents", "Развитие и оптимизация рабочего пространства для команд collection и telesales"),
        ("lead a cross-functional team working at high performance and reliability standards", "Руководство кросс-функциональной инженерной командой с высокими стандартами производительности и надёжности"),
        ("years of experience leading engineering teams", "опыт управления инженерными командами"),
        ("years of experience as a Go developer", "опыт разработки на Go"),
        ("A strong technical background and development experience", "сильный технический бэкграунд и опыт разработки"),
        ("Leading the team in hiring, planning, task decomposition, process improvements, and cross-team collaboration", "опыт найма, планирования, декомпозиции задач, улучшения процессов и кросс-командного взаимодействия"),
        ("Excellent cross-team communication skills and the ability to build partnerships", "сильные навыки кросс-функциональной коммуникации и выстраивания партнёрств"),
        ("Experience in building and optimizing development processes", "опыт построения и оптимизации процессов разработки"),
        ("Drive platform strategy, architecture decisions, and delivery execution", "управление платформенной стратегией, архитектурными решениями и delivery"),
        ("Partner with product and operations on company-wide priorities", "партнёрство с product- и operations-командами по общекомандным приоритетам"),
        ("Build scalable engineering processes and hiring practices", "построение масштабируемых инженерных процессов и практик найма"),
        ("Lead multiple engineering teams and managers", "руководство несколькими инженерными командами и менеджерами"),
    ]

    translated = lowered
    for source, target in replacements:
        translated = translated.replace(source, target)

    translated = translated.strip(" :;-")
    translated = re.sub(r"\b3\+\s*", "от 3 лет ", translated)
    translated = re.sub(r"\b4\+\s*", "от 4 лет ", translated)
    translated = re.sub(r"\s+", " ", translated).strip()

    if translated and translated[0].islower():
        translated = translated[0].upper() + translated[1:]
    if translated and not translated.endswith("."):
        translated += "."
    return translated or clean_requirement_text(requirement)


def contains_cyrillic(text: str) -> bool:
    return bool(re.search(r"[а-яА-ЯёЁ]", text))


def clean_requirement_text(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^[#>\-\*\d\.\)\s]+", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


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
        notes.append(f"Подсветить один сильный аргумент из анализа соответствия: {trim_signal(strengths[0])}")
    if gaps:
        notes.append(f"Один спорный пункт заранее переупаковать как переносимый опыт: {trim_signal(gaps[0])}")
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
    channels.append("Сверить, есть ли прямой контакт рекрутера или нанимающего руководителя до отправки отклика.")
    return channels


def build_follow_up_questions(meta: dict[str, object], raw_source: str, gaps: list[str]) -> list[str]:
    questions: list[str] = []
    if not raw_source.strip():
        questions.append("Нужен полный текст вакансии или хотя бы блок требований и задач.")
    if str(meta.get("country", "")).strip() in {"", "Не указано"}:
        questions.append("Уточнить географию и ожидания по юридическим ограничениям и релокации.")
    if str(meta.get("work_mode", "")).strip() in {"", "Не указано"}:
        questions.append("Уточнить формат работы: офис / гибрид / удалённо.")
    if gaps:
        questions.append(f"Проверить, действительно ли обязателен пункт: {trim_signal(gaps[0])}")
    return questions or ["Дополнительных уточнений для стартового прохода пока нет."]


def build_permanent_candidates(strengths: list[str]) -> list[str]:
    candidates = [trim_signal(item) for item in strengths[:3]]
    return candidates or ["Сильные сигналы проявятся после нескольких обработанных вакансий."]


def build_master_resume_recommendations(assessments: list[RequirementAssessment], selected_resume: str) -> list[str]:
    covered = [item.requirement.rstrip(".") for item in assessments if item.coverage != "gap"][:3]
    gaps = [item.requirement.rstrip(".") for item in assessments if item.coverage == "gap"][:2]
    recommendations = [
        f"Переносить из `MASTER` в `{selected_resume}.md` только подтверждённые сигналы, которые напрямую поддерживают целевую роль.",
    ]
    if covered:
        recommendations.append(f"В первую очередь усиливать уже релевантные сигналы: {', '.join(covered)}.")
    if gaps:
        recommendations.append(f"Пробелы закрывать через точную адаптацию формулировок и фактов из `MASTER`: {', '.join(gaps)}.")
    recommendations.append("Не добавлять в ролевую версию неподтверждённый опыт; спорные зоны выносить в аккуратное позиционирование и сопроводительное письмо.")
    return recommendations


def build_profile_updates(position: str, company: str, strengths: list[str], gaps: list[str]) -> list[str]:
    recommendations = [
        f"Переписать блок `О себе (профиль)` под роль `{position}` и контекст компании `{company or 'работодателя'}`.",
    ]
    if strengths:
        recommendations.append(f"В первой фразе профиля отразить главный сильный сигнал: {trim_signal(strengths[0])}.")
    if gaps:
        recommendations.append(f"Во второй части профиля аккуратно сблизить позиционирование с вакансией через формулировку: {trim_signal(gaps[0])}.")
    recommendations.append("Профиль должен звучать как короткое русскоязычное позиционирование, а не как список английских требований из вакансии.")
    return recommendations


def build_competency_updates(assessments: list[RequirementAssessment]) -> list[str]:
    competencies = collect_competencies(assessments)
    if not competencies:
        return ["Обновить `Ключевые компетенции` под лексику вакансии и убрать второстепенные пункты."]
    return [
        f"Поднять выше в `Ключевых компетенциях`: {', '.join(competencies[:6])}.",
        "Оставлять только те компетенции, которые реально подтверждаются опытом и пригодятся именно для этой вакансии.",
    ]


def build_experience_updates(assessments: list[RequirementAssessment], selected_resume: str) -> list[str]:
    strong = [item.requirement.rstrip(".") for item in assessments if item.coverage == "strong"][:2]
    partial = [item.requirement.rstrip(".") for item in assessments if item.coverage == "partial"][:2]
    gaps = [item.requirement.rstrip(".") for item in assessments if item.coverage == "gap"][:2]
    recommendations = [f"В разделе `Опыт работы` пересобрать bullets в `{selected_resume}.md` вокруг самых релевантных кейсов и измеримого результата."]
    if strong:
        recommendations.append(f"Поднять выше подтверждённые кейсы по темам: {', '.join(strong)}.")
    if partial:
        recommendations.append(f"Сделать явнее уже присутствующие, но недокрученные сигналы: {', '.join(partial)}.")
    if gaps:
        recommendations.append(f"Проверить, есть ли в `MASTER` факты для усиления тем: {', '.join(gaps)}.")
    return recommendations


def collect_competencies(assessments: list[RequirementAssessment]) -> list[str]:
    competencies: list[str] = []
    patterns = [
        ("найм", "найм и развитие команды"),
        ("инженерн", "инженерный менеджмент"),
        ("процесс", "процессы разработки"),
        ("архитект", "архитектура решений"),
        ("go", "Go"),
        ("платформ", "платформенное развитие"),
        ("delivery", "delivery-управление"),
        ("кросс", "кросс-функциональное взаимодействие"),
        ("коммуникац", "коммуникация со стейкхолдерами"),
        ("партнёр", "выстраивание партнёрств"),
        ("надёжност", "надёжность и стабильность"),
        ("масштаб", "масштабирование команд и процессов"),
    ]
    token_sets = [
        {normalize_token(token) for token in re.findall(r"[a-zA-Zа-яА-ЯёЁ][a-zA-Zа-яА-ЯёЁ\-\+]{2,}", item.requirement.lower())}
        for item in assessments
    ]
    for marker, label in patterns:
        if marker == "go":
            matched = any("go" in token_set for token_set in token_sets)
        else:
            matched = any(any(marker in token for token in token_set) for token_set in token_sets)
        if matched and label not in competencies:
            competencies.append(label)
    return competencies


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
        "# Анализ вакансии",
        "",
        "## Сводка",
        "",
        f"- ID вакансии: {vacancy_id}",
        f"- Выбранное резюме: {selected_resume}",
        f"- Режим адаптации: {format_target_mode(target_mode)}",
        f"- Язык: {language}",
        f"- Каналы работодателя: {render_boolean(include_employer_channels)}",
        "",
        "## Анализ соответствия: текущее резюме",
        "",
        f"- Общее соответствие: {current_fit}/100",
        f"- Краткий вывод: Стартовая эвристика показывает опору на `{selected_resume}.md` и {coverage_summary(assessments)}.",
        "",
        "## Анализ соответствия: после предложенных правок",
        "",
        f"- Прогноз соответствия: {projected_fit}/100",
        f"- Прирост: +{delta}",
        "- Комментарий: Прогноз построен по тем пунктам, где формулировки можно приблизить к языку вакансии без искажения опыта.",
        "",
        "## Матрица требований",
        "",
        "| Требование | Приоритет | Подтверждение | Покрытие | Комментарий |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in assessments:
        lines.append(
            f"| {escape_table(item.requirement)} | {format_priority(item.priority)} | {escape_table(item.evidence)} | {format_coverage(item.coverage)} | {escape_table(item.notes)} |"
        )

    lines.extend(
        [
            "",
            "## Сильные стороны",
            "",
            *format_bullets(strengths),
            "",
            "## Пробелы",
            "",
            *format_bullets(gaps),
            "",
            "## Заметки для сопроводительного письма",
            "",
            *format_bullets(cover_letter_notes),
            "",
            "## Заметки по правкам резюме",
            "",
            *format_bullets(resume_edit_notes),
            "",
            "## Каналы связи с работодателем",
            "",
            *format_bullets(contact_channels),
            "",
            "## Вопросы на уточнение",
            "",
            *format_bullets(follow_up_questions),
            "",
        ]
    )
    return "\n".join(lines)


def render_adoptions(
    *,
    vacancy_id: str,
    strengths: list[str],
    permanent_candidates: list[str],
    open_questions: list[str],
    master_resume_recommendations: list[str],
    profile_updates: list[str],
    competency_updates: list[str],
    experience_updates: list[str],
) -> str:
    return "\n".join(
        [
            "# Адаптации по вакансии",
            "",
            f"- ID вакансии: {vacancy_id}",
            "",
            "## Временные сигналы",
            "",
            *format_bullets(strengths[:3]),
            "",
            "## Кандидаты в постоянные сигналы",
            "",
            *format_bullets(permanent_candidates),
            "",
            "## Открытые вопросы",
            "",
            *format_bullets(open_questions),
            "",
            "## Общие рекомендации по добавлению из MASTER в выбранную ролевую версию",
            "",
            *format_bullets(master_resume_recommendations),
            "",
            "## Обновление раздела `О себе (профиль)`",
            "",
            *format_bullets(profile_updates),
            "",
            "## Обновление раздела `Ключевые компетенции`",
            "",
            *format_bullets(competency_updates),
            "",
            "## Обновление раздела `Опыт работы`",
            "",
            *format_bullets(experience_updates),
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
    return trimmed.strip().rstrip(".")


def coverage_summary(assessments: list[RequirementAssessment]) -> str:
    strong = sum(1 for item in assessments if item.coverage == "strong")
    partial = sum(1 for item in assessments if item.coverage == "partial")
    gaps = sum(1 for item in assessments if item.coverage == "gap")
    return f"{strong} сильных / {partial} частичных / {gaps} пробелов"


def format_priority(priority: str) -> str:
    mapping = {
        "high": "высокий",
        "medium": "средний",
        "low": "низкий",
    }
    return mapping.get(priority, priority)


def format_coverage(coverage: str) -> str:
    mapping = {
        "strong": "сильное",
        "partial": "частичное",
        "gap": "пробел",
    }
    return mapping.get(coverage, coverage)


def render_boolean(value: bool) -> str:
    return "да" if value else "нет"


def format_target_mode(target_mode: str) -> str:
    mapping = {
        "conservative": "консервативный",
        "balanced": "сбалансированный",
        "aggressive": "агрессивный",
    }
    return mapping.get(target_mode, target_mode)


def escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def extract_raw_source(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    for marker in ("## Исходный текст", "## Raw Text"):
        if marker in text:
            return text.split(marker, maxsplit=1)[1].strip()
    return text.strip()


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
