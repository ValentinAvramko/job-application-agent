from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from application_agent.memory.models import WorkflowRun
from application_agent.memory.store import JsonMemoryStore
from application_agent.utils.simple_yaml import load_simple_yaml, write_simple_yaml
from application_agent.workflows.base import WorkflowResult
from application_agent.workflows.ingest_vacancy import IngestVacancyRequest, IngestVacancyWorkflow
from application_agent.workspace import WorkspaceLayout

ROLE_README = "README.md"
VALID_COVERAGE = {"full", "partial", "none", "unclear"}
VALID_PRIORITY = {"must", "nice"}

RU_PRIORITY = {"must": "Обязательное", "nice": "Плюс"}
RU_COVERAGE = {"full": "Полное", "partial": "Частичное", "none": "Нет", "unclear": "Неясно"}
RU_CONFIDENCE = {"high": "Высокая", "medium": "Средняя", "low": "Низкая"}

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
    "опыт",
    "работы",
    "будет",
    "нужно",
    "роль",
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
    llm_provider: str = "openai"
    llm_model: str = ""
    llm_temperature: float = 0.2


@dataclass(frozen=True)
class RoleProfile:
    role_id: str
    path: Path
    positioning_signals: list[str]
    strong_evidence_patterns: list[str]
    safe_emphasis_areas: list[str]
    risky_claims: list[str]
    frequent_ats_terms: list[str]
    notes: list[str]


@dataclass(frozen=True)
class RoleCandidate:
    role_id: str
    resume_path: Path
    profile: RoleProfile
    score: int
    rationale: str
    diagnostics: list[str]


@dataclass
class RequirementAssessment:
    source_requirement: str
    requirement: str
    priority: str
    evidence: str
    coverage: str
    notes: str
    selected_evidence: str = ""
    master_evidence: str = ""
    action: str = ""


@dataclass(frozen=True)
class FitResult:
    score: int
    verdict: str
    confidence: str
    rationale: str


class AnalyzeVacancyError(RuntimeError):
    pass


class LLMProvider:
    def generate(self, *, evidence_pack: dict[str, Any], model: str, temperature: float) -> dict[str, Any]:
        raise NotImplementedError


class FakeLLMProvider(LLMProvider):
    def generate(self, *, evidence_pack: dict[str, Any], model: str, temperature: float) -> dict[str, Any]:
        return build_deterministic_llm_package(evidence_pack)


class OpenAICompatibleProvider(LLMProvider):
    def generate(self, *, evidence_pack: dict[str, Any], model: str, temperature: float) -> dict[str, Any]:
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise AnalyzeVacancyError("OPENAI_API_KEY is required for llm_provider=openai.")
        if not model:
            raise AnalyzeVacancyError("llm_model is required for llm_provider=openai. Pass --llm-model or set a default.")

        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        payload = {
            "model": model,
            "temperature": temperature,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a career editor for senior IT leadership roles. "
                        "Return only valid JSON matching the requested analysis package. "
                        "Do not invent facts; use only the evidence pack."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "task": "Create a rich vacancy analysis, two cover letters and resume adaptation draft inputs.",
                            "language": evidence_pack.get("language", "ru"),
                            "required_json_keys": [
                                "why_this_resume",
                                "why_not_others",
                                "strengths",
                                "gaps",
                                "positioning",
                                "final_recommendation",
                                "cover_letter_standard",
                                "cover_letter_short",
                                "adaptation_overview",
                                "temp_signals",
                                "perm_signals",
                                "open_questions",
                                "profile_updates",
                                "competency_updates",
                                "experience_updates",
                            ],
                            "evidence_pack": evidence_pack,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "response_format": {"type": "json_object"},
        }
        request = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise AnalyzeVacancyError(f"LLM request failed: {exc}") from exc

        content = raw.get("choices", [{}])[0].get("message", {}).get("content", "")
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise AnalyzeVacancyError("LLM returned invalid JSON content.") from exc


class AnalyzeVacancyWorkflow:
    name = "analyze-vacancy"
    description = "Создаёт глубокий LLM-backed анализ вакансии и draft-входы для адаптации резюме."

    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider

    def run(self, *, layout: WorkspaceLayout, store: JsonMemoryStore, request: AnalyzeVacancyRequest) -> WorkflowResult:
        started_at = datetime.now(timezone.utc).isoformat()
        bootstrap_artifacts: list[str] = []
        vacancy_id = request.vacancy_id

        if not vacancy_id:
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

        if not vacancy_dir.exists():
            raise FileNotFoundError(
                f"Vacancy '{vacancy_id}' is missing from vacancies/. Runtime memory or the provided vacancy_id is stale; "
                "run ingest-vacancy again or pass an existing --vacancy-id."
            )
        if not meta_path.exists() or not source_path.exists():
            raise FileNotFoundError(
                f"Vacancy '{vacancy_id}' is incomplete: meta.yml or source.md is missing. "
                "Re-run ingest-vacancy to rebuild the vacancy scaffold."
            )

        meta = load_simple_yaml(meta_path)
        raw_source = extract_raw_source(source_path)
        position = request.position.strip() or str(meta.get("position", "")).strip()
        company = request.company.strip() or str(meta.get("company", "")).strip()
        language = normalize_language(request.language or str(meta.get("language", "ru")))
        target_mode = request.target_mode or str(meta.get("target_mode", "balanced"))
        include_employer_channels = request.include_employer_channels or bool(meta.get("include_employer_channels", False))

        role_profiles, role_diagnostics = load_role_profiles(layout)
        role_candidates = build_role_candidates(layout=layout, profiles=role_profiles)
        role_diagnostics.extend(candidate_diagnostics(role_profiles=role_profiles, candidates=role_candidates))
        if not role_candidates:
            raise AnalyzeVacancyError(
                "No valid role profiles found. Add role files to knowledge/roles/ and matching resumes/<Role>.md files."
            )

        master_text = read_optional(layout.resumes_dir / "MASTER.md")
        requirements = extract_requirements(position=position, source_text=raw_source)
        selected_resume, override_note = resolve_selected_resume(
            explicit_resume=request.selected_resume,
            position=position,
            source_text=raw_source,
            candidates=role_candidates,
            requirements=requirements,
            master_text=master_text,
        )
        selected_candidate = require_candidate(role_candidates, selected_resume)
        selected_resume_text = selected_candidate.resume_path.read_text(encoding="utf-8")
        assessments = [assess_requirement(requirement, selected_resume_text, master_text=master_text) for requirement in requirements]
        fit = compute_fit_result(assessments)
        ranked_candidates = rank_role_candidates(
            position=position,
            source_text=raw_source,
            candidates=role_candidates,
            requirements=requirements,
            master_text=master_text,
        )

        evidence_pack = build_evidence_pack(
            vacancy_id=vacancy_id,
            company=company,
            position=position,
            language=language,
            target_mode=target_mode,
            selected_resume=selected_resume,
            selected_resume_text=selected_resume_text,
            selected_profile=selected_candidate.profile,
            ranked_candidates=ranked_candidates,
            role_diagnostics=role_diagnostics,
            override_note=override_note,
            requirements=requirements,
            assessments=assessments,
            fit=fit,
            master_text=master_text,
            raw_source=raw_source,
        )
        provider = self.provider or build_llm_provider(request.llm_provider)
        llm_model = request.llm_model or os.environ.get("APPLICATION_AGENT_LLM_MODEL", "").strip()
        llm_package = provider.generate(evidence_pack=evidence_pack, model=llm_model, temperature=request.llm_temperature)
        analysis_package = validate_llm_package(llm_package)

        analysis_path.write_text(
            render_analysis(evidence_pack=evidence_pack, analysis_package=analysis_package),
            encoding="utf-8",
            newline="\n",
        )
        adoptions_path.write_text(
            render_adoptions(vacancy_id=vacancy_id, selected_resume=selected_resume, analysis_package=analysis_package),
            encoding="utf-8",
            newline="\n",
        )

        meta["selected_resume"] = selected_resume
        meta["target_mode"] = target_mode
        meta["include_employer_channels"] = include_employer_channels
        meta["llm_provider"] = request.llm_provider
        meta["llm_model"] = llm_model or "n/a"
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
                summary=f"Собран глубокий анализ вакансии {vacancy_id} на основе резюме {selected_resume}.",
            )
        )
        return WorkflowResult(
            workflow=self.name,
            status="completed",
            summary=f"Подготовлен глубокий анализ вакансии {vacancy_id} с резюме {selected_resume}.",
            artifacts=artifacts,
        )


def load_role_profiles(layout: WorkspaceLayout) -> tuple[list[RoleProfile], list[str]]:
    roles_dir = layout.knowledge_dir / "roles"
    diagnostics: list[str] = []
    profiles: list[RoleProfile] = []
    if not roles_dir.exists():
        return profiles, [f"Каталог ролей не найден: {roles_dir}."]

    for path in sorted(roles_dir.glob("*.md")):
        if path.name.lower() == ROLE_README.lower():
            continue
        text = path.read_text(encoding="utf-8")
        role_id = parse_role_id(text, path)
        if not role_id:
            diagnostics.append(f"Профиль роли {path.name} пропущен: не удалось определить Role.")
            continue
        profiles.append(
            RoleProfile(
                role_id=role_id,
                path=path,
                positioning_signals=extract_role_section_bullets(
                    text, "## Сигналы позиционирования", "## Positioning Signals"
                ),
                strong_evidence_patterns=extract_role_section_bullets(
                    text, "## Сильные доказательные паттерны", "## Strong Evidence Patterns"
                ),
                safe_emphasis_areas=extract_role_section_bullets(
                    text, "## Безопасные акценты", "## Safe Emphasis Areas"
                ),
                risky_claims=extract_role_section_bullets(
                    text, "## Рискованные утверждения", "## Risky Claims"
                ),
                frequent_ats_terms=extract_role_section_bullets(
                    text, "## Частые ATS-термины", "## Frequent ATS Terms"
                ),
                notes=extract_role_section_bullets(
                    text, "## Заметки по обработанным вакансиям", "## Notes From Processed Vacancies"
                ),
            )
        )
    return profiles, diagnostics


def parse_role_id(text: str, path: Path) -> str:
    for line in text.splitlines():
        match = re.match(r"\s*-\s*(?:Role|Роль):\s*(.+?)\s*$", line, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return path.stem.strip()


def build_role_candidates(*, layout: WorkspaceLayout, profiles: list[RoleProfile]) -> list[RoleCandidate]:
    candidates: list[RoleCandidate] = []
    for profile in profiles:
        resume_path = layout.resumes_dir / f"{profile.role_id}.md"
        if not resume_path.exists():
            continue
        candidates.append(RoleCandidate(profile.role_id, resume_path, profile, 0, "", []))
    return candidates


def candidate_diagnostics(*, role_profiles: list[RoleProfile], candidates: list[RoleCandidate]) -> list[str]:
    candidate_ids = {candidate.role_id for candidate in candidates}
    return [
        f"Роль `{profile.role_id}` исключена из выбора: нет файла `resumes/{profile.role_id}.md`."
        for profile in role_profiles
        if profile.role_id not in candidate_ids
    ]


def resolve_selected_resume(
    *,
    explicit_resume: str,
    position: str,
    source_text: str,
    candidates: list[RoleCandidate],
    requirements: list[str],
    master_text: str,
) -> tuple[str, str]:
    if explicit_resume.strip():
        candidate_ids = {candidate.role_id for candidate in candidates}
        selected = explicit_resume.strip()
        if selected not in candidate_ids:
            raise AnalyzeVacancyError(f"Selected resume '{selected}' has no valid role profile and matching resume.")
        return selected, f"Выбор резюме вручную переопределён параметром `--selected-resume {selected}`."
    ranked = rank_role_candidates(
        position=position,
        source_text=source_text,
        candidates=candidates,
        requirements=requirements,
        master_text=master_text,
    )
    return ranked[0].role_id, ""


def require_candidate(candidates: list[RoleCandidate], role_id: str) -> RoleCandidate:
    for candidate in candidates:
        if candidate.role_id == role_id:
            return candidate
    raise AnalyzeVacancyError(f"Role candidate '{role_id}' is not available.")


def rank_role_candidates(
    *,
    position: str,
    source_text: str,
    candidates: list[RoleCandidate],
    requirements: list[str],
    master_text: str,
) -> list[RoleCandidate]:
    ranked: list[RoleCandidate] = []
    combined = f"{position}\n{source_text}"
    for candidate in candidates:
        resume_text = candidate.resume_path.read_text(encoding="utf-8")
        assessments = [assess_requirement(requirement, resume_text, master_text=master_text) for requirement in requirements]
        fit = compute_fit_result(assessments)
        profile_score = role_profile_match_score(candidate.profile, combined)
        title_score = title_match_score(candidate.role_id, position)
        scope_score = senior_scope_alignment_score(candidate.profile, combined)
        risky_penalty = risky_claim_penalty(candidate.profile, combined)
        score = fit.score + profile_score + scope_score + title_score - risky_penalty
        rationale = (
            f"fit={fit.score}, role_profile={profile_score}, scope_alignment={scope_score}, title_signal={title_score}, "
            f"risky_claim_penalty={risky_penalty}"
        )
        ranked.append(RoleCandidate(candidate.role_id, candidate.resume_path, candidate.profile, score, rationale, candidate.diagnostics))
    return sorted(ranked, key=lambda item: (-item.score, item.role_id))


def role_profile_match_score(profile: RoleProfile, text: str) -> int:
    text_tokens = tokenize(text)
    score = 0
    for signal in profile.positioning_signals + profile.strong_evidence_patterns + profile.frequent_ats_terms:
        signal_tokens = tokenize(signal)
        if not signal_tokens:
            continue
        matches = text_tokens & signal_tokens
        if len(matches) >= min(2, len(signal_tokens)):
            score += 3
        elif matches:
            score += 1
    return min(score, 20)


def title_match_score(role_id: str, position: str) -> int:
    lower = position.lower()
    mapping = {
        "cio": ("cio", "директор по ит", "руководитель ит"),
        "cto": ("cto", "технический директор", "директор по технологиям"),
        "hoe": ("head of engineering", "vp engineering", "engineering director"),
        "hod": ("head of development", "руководитель разработки", "директор по разработке"),
        "em": ("engineering manager", "team lead"),
    }
    return 2 if any(marker in lower for marker in mapping.get(role_id.lower(), (role_id.lower(),))) else 0


def senior_scope_alignment_score(profile: RoleProfile, text: str) -> int:
    text_tokens = tokenize(text)
    scope_tokens = {
        "organization",
        "engineering",
        "engineer",
        "culture",
        "performance",
        "onboarding",
        "review",
        "leadership",
        "lead",
        "manager",
        "кластер",
        "инженер",
        "культура",
        "культур",
        "организац",
        "организация",
        "организации",
        "тимлид",
        "лидер",
        "ментор",
        "найм",
    }
    vacancy_scope_hits = text_tokens & scope_tokens
    if not vacancy_scope_hits:
        return 0

    score = 0
    profile_signals = (
        profile.positioning_signals
        + profile.strong_evidence_patterns
        + profile.safe_emphasis_areas
        + profile.notes
    )
    for signal in profile_signals:
        signal_tokens = tokenize(signal)
        if signal_tokens & scope_tokens and signal_tokens & text_tokens:
            score += 2
    return min(score, 12)


def risky_claim_penalty(profile: RoleProfile, text: str) -> int:
    text_tokens = tokenize(text)
    penalty = 0
    for claim in profile.risky_claims:
        if tokenize(claim) & text_tokens:
            penalty += 1
    return min(penalty, 5)


def extract_requirements(*, position: str, source_text: str) -> list[str]:
    requirements: list[tuple[str, str]] = []
    active_priority = "must"
    for raw_line in source_text.splitlines():
        line = normalize_requirement_line(raw_line)
        if not line:
            continue
        lower = line.lower()
        if any(marker in lower for marker in ("обязательно", "must", "requirements", "что ищем")):
            active_priority = "must"
            continue
        if any(marker in lower for marker in ("будут плюсом", "nice to have", "preferred", "желательно")):
            active_priority = "nice"
            continue
        if raw_line.strip().startswith(("-", "*")) and len(line) >= 12:
            requirements.append((active_priority, line))

    if not requirements:
        chunks = re.split(r"[\n\r]+|(?<=[.!?])\s+", source_text)
        for chunk in chunks:
            line = normalize_requirement_line(chunk)
            if len(line) >= 24 and looks_like_requirement(line):
                requirements.append((classify_priority(line), line))

    unique: list[str] = []
    seen: set[str] = set()
    for priority, requirement in requirements:
        key = requirement.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(f"[{priority}] {requirement}")
        if len(unique) >= 16:
            break
    return unique or [f"[must] Зона лидерства и ответственность за delivery для роли {position or 'целевой роли'}"]


def normalize_requirement_line(value: str) -> str:
    cleaned = value.strip()
    cleaned = re.sub(r"^[#>\-\*\d\.\)\s]+", "", cleaned)
    cleaned = cleaned.replace("**", "")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" :;")


def looks_like_requirement(line: str) -> bool:
    lower = line.lower()
    markers = (
        "опыт",
        "управ",
        "руковод",
        "архитект",
        "delivery",
        "ci/cd",
        "docker",
        "kubernetes",
        "java",
        "команд",
        "stakeholder",
        "required",
        "must",
    )
    return any(marker in lower for marker in markers)


def assess_requirement(requirement: str, resume_text: str, master_text: str = "") -> RequirementAssessment:
    priority, text = split_requirement_priority(requirement)
    selected_evidence = find_evidence(text, resume_text)
    master_evidence = find_evidence(text, master_text) if master_text else ""

    if selected_evidence and master_evidence:
        coverage = "full"
    elif selected_evidence and len(extract_keywords(text)) <= 4:
        coverage = "full"
    elif selected_evidence or master_evidence:
        coverage = "partial"
    else:
        coverage = "none"

    evidence = selected_evidence or master_evidence or "Подтверждение не найдено в выбранном резюме или MASTER."
    if coverage == "full":
        notes = "Требование убедительно покрыто подтверждёнными фактами."
        action = "Оставить как сильный аргумент."
    elif coverage == "partial":
        notes = "Покрытие частичное или косвенное; формулировку нужно усилить без добавления новых фактов."
        action = "Усилить через подтверждённый опыт из выбранного резюме или MASTER."
    else:
        notes = "Покрытия нет; не добавлять как факт без подтверждения."
        action = "Отметить как gap или NEW DATA NEEDED."

    return RequirementAssessment(
        source_requirement=text,
        requirement=text,
        priority=priority,
        evidence=evidence,
        coverage=coverage,
        notes=notes,
        selected_evidence=selected_evidence,
        master_evidence=master_evidence,
        action=action,
    )


def split_requirement_priority(requirement: str) -> tuple[str, str]:
    match = re.match(r"^\[(must|nice)\]\s+(.+)$", requirement)
    if match:
        return match.group(1), match.group(2).strip()
    return classify_priority(requirement), requirement


def classify_priority(requirement: str) -> str:
    lower = requirement.lower()
    if any(marker in lower for marker in ("будет плюсом", "nice to have", "preferred", "желательно", "plus")):
        return "nice"
    return "must"


def find_evidence(requirement: str, text: str) -> str:
    if not text.strip():
        return ""
    keywords = extract_keywords(requirement)
    best_line = ""
    best_score = 0
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or len(line) < 20:
            continue
        tokens = tokenize(line)
        score = sum(1 for keyword in keywords if keyword in tokens or any(keyword in token or token in keyword for token in tokens))
        if any(char.isdigit() for char in line) and any(keyword in tokens for keyword in ("команд", "team", "lead", "метрик", "metric")):
            score += 1
        if score > best_score:
            best_score = score
            best_line = trim_markdown_bullet(line)
    if best_score >= 2 or (best_score == 1 and len(keywords) <= 3):
        return best_line
    return ""


def extract_keywords(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Zа-яА-ЯёЁ][a-zA-Zа-яА-ЯёЁ0-9/\-\+\.]{1,}", text.lower())
    result: list[str] = []
    for word in words:
        normalized = normalize_token(word)
        if len(normalized) < 3 or normalized in STOPWORDS or normalized in result:
            continue
        result.append(normalized)
    return result[:8]


def tokenize(text: str) -> set[str]:
    return {normalize_token(token) for token in re.findall(r"[a-zA-Zа-яА-ЯёЁ][a-zA-Zа-яА-ЯёЁ0-9/\-\+\.]{1,}", text.lower())} - {""}


def normalize_token(token: str) -> str:
    normalized = token.lower().strip("-+.,:;()[]{} ")
    aliases = {
        "teams": "team",
        "managers": "manager",
        "managed": "manage",
        "managing": "manage",
        "leading": "lead",
        "led": "lead",
        "processes": "process",
        "services": "service",
        "metrics": "metric",
        "engineers": "engineer",
        "командами": "команд",
        "команды": "команд",
        "командам": "команд",
        "руководил": "руковод",
        "руководство": "руковод",
        "управления": "управ",
        "управлял": "управ",
        "метрики": "метрик",
        "метрик": "метрик",
        "архитектурные": "архитект",
        "архитектурных": "архитект",
        "процессы": "процесс",
        "процессов": "процесс",
    }
    if normalized in aliases:
        return aliases[normalized]
    if len(normalized) > 4 and normalized.endswith("ами"):
        normalized = normalized[:-3]
    elif len(normalized) > 4 and normalized.endswith("ов"):
        normalized = normalized[:-2]
    elif len(normalized) > 4 and normalized.endswith("ы"):
        normalized = normalized[:-1]
    elif len(normalized) > 4 and normalized.endswith("s"):
        normalized = normalized[:-1]
    return aliases.get(normalized, normalized)


def compute_fit_result(assessments: list[RequirementAssessment]) -> FitResult:
    if not assessments:
        return FitResult(0, "Weak fit", "low", "Нет требований для расчёта.")
    max_score = 0.0
    actual = 0.0
    for item in assessments:
        if item.priority == "nice":
            max_score += 0.5
            actual += {"full": 0.5, "partial": 0.25, "none": 0.0, "unclear": 0.0}.get(item.coverage, 0.0)
        else:
            max_score += 1.0
            actual += {"full": 1.0, "partial": 0.5, "none": 0.0, "unclear": 0.0}.get(item.coverage, 0.0)
    score = round((actual / max_score) * 100) if max_score else 0
    if score >= 85:
        verdict = "Strong fit"
    elif score >= 68:
        verdict = "Good fit with gaps"
    elif score >= 50:
        verdict = "Borderline fit"
    else:
        verdict = "Weak fit"
    full_count = sum(1 for item in assessments if item.coverage == "full")
    unknown_count = sum(1 for item in assessments if item.coverage in {"none", "unclear"})
    if full_count >= len(assessments) * 0.65 and unknown_count <= 1:
        confidence = "high"
    elif unknown_count <= len(assessments) * 0.45:
        confidence = "medium"
    else:
        confidence = "low"
    rationale = (
        f"Расчёт: обязательные требования дают до 1 балла, плюсы до 0.5; "
        f"полное покрытие={full_count}, пробелы/неясно={unknown_count}."
    )
    return FitResult(score, verdict, confidence, rationale)


def build_evidence_pack(
    *,
    vacancy_id: str,
    company: str,
    position: str,
    language: str,
    target_mode: str,
    selected_resume: str,
    selected_resume_text: str,
    selected_profile: RoleProfile,
    ranked_candidates: list[RoleCandidate],
    role_diagnostics: list[str],
    override_note: str,
    requirements: list[str],
    assessments: list[RequirementAssessment],
    fit: FitResult,
    master_text: str,
    raw_source: str,
) -> dict[str, Any]:
    return {
        "vacancy_id": vacancy_id,
        "company": company,
        "position": position,
        "language": language,
        "target_mode": target_mode,
        "selected_resume": selected_resume,
        "selected_profile": asdict_without_path(selected_profile),
        "role_candidates": [
            {
                "role_id": candidate.role_id,
                "score": candidate.score,
                "rationale": candidate.rationale,
            }
            for candidate in ranked_candidates
        ],
        "role_diagnostics": role_diagnostics,
        "override_note": override_note,
        "requirements": [split_requirement_priority(item)[1] for item in requirements],
        "assessments": [assessment_to_dict(item) for item in assessments],
        "fit": asdict(fit),
        "resume_highlights": extract_resume_highlights(selected_resume_text, limit=8),
        "master_available": bool(master_text.strip()),
        "forbidden_claims": build_forbidden_claims(assessments, selected_profile),
        "raw_source_excerpt": raw_source[:3000],
    }


def asdict_without_path(profile: RoleProfile) -> dict[str, Any]:
    payload = asdict(profile)
    payload["path"] = str(profile.path)
    return payload


def assessment_to_dict(item: RequirementAssessment) -> dict[str, str]:
    return {
        "requirement": item.requirement,
        "priority": item.priority,
        "priority_ru": RU_PRIORITY.get(item.priority, item.priority),
        "coverage": item.coverage,
        "coverage_ru": RU_COVERAGE.get(item.coverage, item.coverage),
        "selected_evidence": item.selected_evidence,
        "master_evidence": item.master_evidence,
        "notes": item.notes,
        "action": item.action,
    }


def build_forbidden_claims(assessments: list[RequirementAssessment], profile: RoleProfile) -> list[str]:
    claims = [item.requirement for item in assessments if item.coverage == "none"]
    claims.extend(profile.risky_claims)
    return unique_nonempty(claims)[:8]


def build_llm_provider(name: str) -> LLMProvider:
    normalized = (name or "openai").strip().lower()
    if normalized == "fake":
        return FakeLLMProvider()
    if normalized == "openai":
        return OpenAICompatibleProvider()
    raise AnalyzeVacancyError(f"Unsupported llm_provider '{name}'. Supported providers: openai, fake.")


def validate_llm_package(payload: dict[str, Any]) -> dict[str, Any]:
    required = [
        "why_this_resume",
        "why_not_others",
        "strengths",
        "gaps",
        "positioning",
        "final_recommendation",
        "cover_letter_standard",
        "cover_letter_short",
        "adaptation_overview",
        "temp_signals",
        "perm_signals",
        "open_questions",
        "profile_updates",
        "competency_updates",
        "experience_updates",
    ]
    missing = [key for key in required if key not in payload]
    if missing:
        raise AnalyzeVacancyError(f"LLM response is missing required keys: {', '.join(missing)}.")
    normalized = dict(payload)
    for key in required:
        if key in {"cover_letter_standard", "cover_letter_short", "positioning", "final_recommendation", "adaptation_overview"}:
            normalized[key] = str(normalized[key]).strip()
        else:
            normalized[key] = normalize_list(normalized[key])
    return normalized


def build_deterministic_llm_package(evidence_pack: dict[str, Any]) -> dict[str, Any]:
    selected_resume = evidence_pack["selected_resume"]
    company = evidence_pack.get("company") or "компании"
    position = evidence_pack.get("position") or "целевой роли"
    assessments = evidence_pack["assessments"]
    full = [item for item in assessments if item["coverage"] == "full"]
    partial = [item for item in assessments if item["coverage"] == "partial"]
    gaps = [item for item in assessments if item["coverage"] in {"none", "unclear"}]
    candidate_rows = evidence_pack.get("role_candidates", [])
    alternatives = [
        f"{row['role_id']}: слабее по совокупному score ({row['score']}) и role rationale: {row['rationale']}"
        for row in candidate_rows
        if row["role_id"] != selected_resume
    ][:4]
    strengths = [
        f"{item['requirement']} - {item['selected_evidence'] or item['master_evidence']}"
        for item in full[:5]
    ] or [f"`{selected_resume}` даёт наиболее релевантный подтверждённый контур для роли."]
    gap_items = [
        f"{item['requirement']} - {item['notes']}"
        for item in (gaps + partial)[:5]
    ]
    first_strength = trim_signal(strengths[0])
    first_gap = trim_signal(gap_items[0]) if gap_items else "часть требований нужно уточнить по фактам"
    fit = evidence_pack["fit"]
    cover_standard = (
        f"Здравствуйте.\n\n"
        f"Рассматриваю роль {position}, потому что она близка к моему опыту управления инженерными командами, "
        f"delivery и развитием критичных систем. В качестве основной версии резюме я бы использовал {selected_resume}: "
        f"она лучше всего показывает тот контур, который важен для этой вакансии.\n\n"
        f"Ключевой релевантный аргумент: {first_strength}. Это даёт рабочую основу для разговора о задачах {company}, "
        f"особенно там, где важны предсказуемость поставки, качество инженерных решений и управляемость нескольких команд.\n\n"
        f"Отдельные зоны стоит обсуждать аккуратно: {first_gap}. Я не стал бы дорисовывать неподтверждённый опыт, "
        f"а показал бы смежные кейсы и готовность быстро закрыть контекст.\n\n"
        f"Буду рад пообщаться по вакансии и ответить на ваши вопросы."
    )
    cover_short = (
        f"Здравствуйте. Мне интересна роль {position}: по содержанию она близка к моему опыту управления инженерными "
        f"командами, delivery и развитием критичных систем. Для отклика я бы выбрал резюме {selected_resume}, потому что "
        f"оно лучше всего показывает релевантный управленческий и инженерный контур.\n\n"
        f"Главный аргумент для первого контакта: {first_strength}. Спорные зоны лучше обозначить честно и связать со "
        f"смежным подтверждённым опытом. Буду рад обсудить вакансию."
    )
    profile_updates = [
        f"| Short Summary | {selected_resume}.md :: profile | Руководитель инженерной функции для роли {position}: {first_strength} | TEMP | selected resume / MASTER | Не добавлять неподтверждённый домен или стек. |",
        f"| Extended Summary | {selected_resume}.md :: profile | Расширить профиль вокруг multi-team leadership, delivery, architecture/reliability и измеримых результатов под контекст {company}. | TEMP | selected resume / MASTER | Держать факты в границах evidence matrix. |",
    ]
    competency_updates = [
        f"| Поднять выше | {selected_resume}.md :: skills | {item['requirement']} | TEMP | {item['selected_evidence'] or item['master_evidence']} | Только если формулировка уже подтверждена. |"
        for item in (full + partial)[:5]
    ]
    experience_updates = [
        f"| {item['selected_evidence'] or 'Нужен исходный bullet'} | {rewrite_experience_bullet(item, company)} | TEMP | {item['selected_evidence'] or item['master_evidence']} | Не добавлять новый факт, только переупаковать подтверждённый. |"
        for item in (full + partial)[:6]
    ]
    return {
        "why_this_resume": [
            f"`{selected_resume}` набирает лучший совокупный score среди доступных role profiles.",
            f"Fit score: {fit['score']}%; вердикт: {fit['verdict']}; уверенность: {fit['confidence']}.",
            f"Главный доказательный сигнал: {first_strength}.",
        ],
        "why_not_others": alternatives or ["Ближайшие альтернативы не дали более сильного покрытия по must-have требованиям."],
        "strengths": strengths,
        "gaps": gap_items or ["Критичных gaps не найдено, но формулировки нужно держать в рамках подтверждённых фактов."],
        "positioning": (
            f"Для этой вакансии кандидат выглядит как {selected_resume}-профиль с сильной опорой на engineering leadership, "
            f"delivery и управление изменениями. Это не означает идеальный доменный match, но даёт убедимую основу для отклика."
        ),
        "final_recommendation": f"Apply with caveats: score {fit['score']}%, {fit['verdict']}.",
        "cover_letter_standard": cover_standard,
        "cover_letter_short": cover_short,
        "adaptation_overview": (
            "В `adoptions.md` переданы draft-правки для summary, skills и experience. "
            "Все спорные или неподтверждённые пункты помечены как NEW DATA NEEDED или factual boundary."
        ),
        "temp_signals": strengths[:4],
        "perm_signals": [item for item in strengths[:3] if "не найдено" not in item.lower()],
        "open_questions": [item["requirement"] for item in gaps[:4]] or ["Уточнить, какие требования являются решающими для shortlist."],
        "profile_updates": profile_updates,
        "competency_updates": competency_updates or ["| Проверить | selected resume :: skills | Поднять наиболее релевантные компетенции из матрицы требований. | TEMP | analysis matrix | Не добавлять новые claims. |"],
        "experience_updates": experience_updates or ["| Нужен исходный bullet | Переписать релевантный bullet после подтверждения факта. | NEW DATA NEEDED | analysis matrix | Нельзя добавлять без evidence. |"],
    }


def rewrite_experience_bullet(item: dict[str, str], company: str) -> str:
    evidence = item.get("selected_evidence") or item.get("master_evidence") or ""
    requirement = item.get("requirement", "требование роли")
    if not evidence:
        return f"Добавить подтверждённый пример по теме: {requirement}"
    return f"{trim_signal(evidence)}; в контексте отклика подсветить связь с требованием: {requirement}"


def render_analysis(*, evidence_pack: dict[str, Any], analysis_package: dict[str, Any]) -> str:
    fit = evidence_pack["fit"]
    selected_resume = evidence_pack["selected_resume"]
    lines = [
        "# Анализ вакансии",
        "",
        "## 1. Анализ соответствия и выбор резюме",
        "",
        "### Сводка",
        "",
        f"- ID вакансии: {evidence_pack['vacancy_id']}",
        f"- Компания: {evidence_pack.get('company') or 'нет данных'}",
        f"- Позиция: {evidence_pack.get('position') or 'нет данных'}",
        f"- Выбранное резюме: {selected_resume}",
        f"- Fit score: {fit['score']}%",
        f"- Вердикт: {fit['verdict']}",
        f"- Уверенность: {RU_CONFIDENCE.get(fit['confidence'], fit['confidence'])}",
        f"- Методика: {fit['rationale']}",
    ]
    if evidence_pack.get("override_note"):
        lines.append(f"- Override: {evidence_pack['override_note']}")
    if evidence_pack.get("role_diagnostics"):
        lines.append(f"- Диагностика ролей: {'; '.join(evidence_pack['role_diagnostics'])}")

    lines.extend(["", "### Почему это резюме", "", *format_bullets(analysis_package["why_this_resume"])])
    lines.extend(["", "### Почему не другие", "", *format_bullets(analysis_package["why_not_others"])])
    lines.extend(
        [
            "",
            "### Матрица требований",
            "",
            "| Требование | Приоритет | Evidence in selected CV | Evidence in MASTER | Покрытие | Action |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for item in evidence_pack["assessments"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    escape_table(item["requirement"]),
                    escape_table(item["priority_ru"]),
                    escape_table(item["selected_evidence"] or "—"),
                    escape_table(item["master_evidence"] or "—"),
                    escape_table(item["coverage_ru"]),
                    escape_table(item["action"]),
                ]
            )
            + " |"
        )
    lines.extend(["", "### Сильные стороны", "", *format_bullets(analysis_package["strengths"])])
    lines.extend(["", "### Пробелы и риски", "", *format_bullets(analysis_package["gaps"])])
    lines.extend(["", "### Позиционирование", "", analysis_package["positioning"]])
    lines.extend(["", "### Итоговая рекомендация", "", analysis_package["final_recommendation"]])
    lines.extend(
        [
            "",
            "## 2. Сопроводительное письмо",
            "",
            "### Standard version",
            "",
            analysis_package["cover_letter_standard"],
            "",
            "### Short version",
            "",
            analysis_package["cover_letter_short"],
            "",
            "## 3. Входные данные для адаптации резюме",
            "",
            analysis_package["adaptation_overview"],
            "",
            "### Что требует подтверждения",
            "",
            *format_bullets(analysis_package["open_questions"]),
            "",
            "### Что нельзя добавлять как факт",
            "",
            *format_bullets(evidence_pack["forbidden_claims"]),
            "",
        ]
    )
    return "\n".join(lines)


def render_adoptions(*, vacancy_id: str, selected_resume: str, analysis_package: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Адаптации по вакансии",
            "",
            f"- ID вакансии: {vacancy_id}",
            f"- Выбранное резюме: {selected_resume}",
            "",
            "## Временные сигналы",
            "",
            *format_bullets(analysis_package["temp_signals"]),
            "",
            "## Кандидаты в постоянные сигналы",
            "",
            *format_bullets(analysis_package["perm_signals"]),
            "",
            "## Открытые вопросы",
            "",
            *format_bullets(analysis_package["open_questions"]),
            "",
            "## Общие рекомендации по добавлению из MASTER в выбранную ролевую версию",
            "",
            "- Переносить только факты, подтверждённые в `MASTER` или выбранном ролевом резюме.",
            "- Спорные требования оставлять в `NEW DATA NEEDED`, пока не появится подтверждение.",
            "",
            "## Обновление раздела `О себе (профиль)`",
            "",
            "| Change | Target | Draft | Status | Evidence | Factual Boundary |",
            "| --- | --- | --- | --- | --- | --- |",
            *format_table_lines(analysis_package["profile_updates"], 6),
            "",
            "## Обновление раздела `Ключевые компетенции`",
            "",
            "| Change | Target | Draft | Status | Evidence | Factual Boundary |",
            "| --- | --- | --- | --- | --- | --- |",
            *format_table_lines(analysis_package["competency_updates"], 6),
            "",
            "## Обновление раздела `Опыт работы`",
            "",
            "| Before | After | Status | Evidence | Factual Boundary |",
            "| --- | --- | --- | --- | --- |",
            *format_table_lines(analysis_package["experience_updates"], 5),
            "",
        ]
    )


def format_table_lines(items: list[str], columns: int) -> list[str]:
    if not items:
        return ["| " + " | ".join([""] * columns) + " |"]
    result: list[str] = []
    for item in items:
        stripped = item.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            result.append(stripped)
            continue
        cells = [stripped] + [""] * (columns - 1)
        result.append("| " + " | ".join(escape_table(cell) for cell in cells[:columns]) + " |")
    return result


def extract_resume_highlights(resume_text: str, limit: int) -> list[str]:
    items: list[str] = []
    for line in resume_text.splitlines():
        cleaned = trim_markdown_bullet(line.strip())
        lower = cleaned.lower()
        if len(cleaned) < 30:
            continue
        if any(marker in lower for marker in ("руковод", "управ", "lead time", "flow efficiency", "deployment", "архитект", "команд")):
            items.append(cleaned)
    return unique_nonempty(items)[:limit]


def read_optional(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def normalize_language(value: str) -> str:
    normalized = value.strip().lower()
    if normalized.startswith("en"):
        return "en"
    if normalized.startswith("es"):
        return "es"
    return "ru"


def dedupe_paths(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        result.append(path)
    return result


def extract_raw_source(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    for marker in ("## Исходный текст", "## Raw Text"):
        if marker in text:
            return text.split(marker, maxsplit=1)[1].strip()
    return text.strip()


def extract_section_bullets(markdown: str, heading: str) -> list[str]:
    if heading not in markdown:
        return []
    section = markdown.split(heading, maxsplit=1)[1]
    match = re.search(r"\n##\s", section)
    if match:
        section = section[: match.start()]
    items: list[str] = []
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if line.startswith("- "):
            items.append(trim_markdown_bullet(line))
    return unique_nonempty(items)


def extract_role_section_bullets(markdown: str, *headings: str) -> list[str]:
    for heading in headings:
        items = extract_section_bullets(markdown, heading)
        if items:
            return items
    return []


def normalize_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [line.strip("- ").strip() for line in value.splitlines() if line.strip("- ").strip()]
    return [str(value).strip()] if value else []


def format_bullets(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] or ["- "]


def trim_markdown_bullet(value: str) -> str:
    cleaned = re.sub(r"^[\-\*\d\.\)\s]+", "", value.strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip().rstrip(".")


def trim_signal(value: str) -> str:
    return trim_markdown_bullet(value)


def unique_nonempty(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        cleaned = trim_signal(str(item))
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def escape_table(value: str) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def choose_resume(*, position: str, source_text: str) -> str:
    combined = f"{position}\n{source_text}".lower()
    if "head of engineering" in combined or "engineering organization" in combined:
        return "HoE"
    if "head of development" in combined or "руководитель разработки" in combined:
        return "HoD"
    if "cto" in combined or "технический директор" in combined:
        return "CTO"
    if "cio" in combined or "директор по ит" in combined:
        return "CIO"
    return "EM"
