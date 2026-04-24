from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from application_agent.memory.store import JsonMemoryStore
from application_agent.workspace import WorkspaceLayout
from application_agent.workflows import ingest_vacancy
from application_agent.workflows.analyze_vacancy import (
    AnalyzeVacancyError,
    AnalyzeVacancyRequest,
    AnalyzeVacancyWorkflow,
    RequirementAssessment,
    compute_fit_result,
)
from application_agent.workflows.ingest_vacancy import IngestVacancyRequest
from application_agent.workflows.registry import build_default_registry


def test_analyze_creates_rich_package_and_selects_hoe_for_fintehrobot(monkeypatch: pytest.MonkeyPatch) -> None:
    _, layout, store = build_workspace("analyze-workflow")
    seed_role_profile(layout, "HoD", ["руководитель разработки", "delivery", "тимлиды"], ["java", "kotlin"])
    seed_role_profile(layout, "HoE", ["engineering organization", "платформа", "DORA", "30 engineers"], ["kubernetes", "kafka"])
    seed_resume(
        layout,
        "HoD",
        [
            "# HoD Resume",
            "- Руководил командами разработки и развивал тимлидов.",
            "- Улучшал процессы поставки и архитектурные решения.",
        ],
    )
    seed_resume(
        layout,
        "HoE",
        [
            "# HoE Resume",
            "- Руководил engineering organization 35+ инженеров через лидов и отвечал за delivery critical systems.",
            "- Внедрял DORA metrics, сокращал lead time и улучшал deployment frequency.",
            "- Работал с платформенным контуром: Kubernetes, Kafka, PostgreSQL, observability и reliability.",
        ],
    )
    seed_resume(layout, "MASTER", ["# MASTER", "- Подтверждён опыт с Java/Kotlin, Kafka, PostgreSQL, Docker/Kubernetes и Grafana/Kibana."])
    vacancy_id = ingest_vacancy_fixture(
        layout=layout,
        store=store,
        monkeypatch=monkeypatch,
        company="Финтехробот",
        position="Head of Development / Руководитель разработки",
        source_text="\n".join(
            [
                "Обязательно:",
                "- Управлять инженерной организацией 30+ разработчиков через тимлидов.",
                "- Улучшать DORA metrics, lead time, deployment frequency и reliability.",
                "- Разбираться в Java/Kotlin, Kafka, PostgreSQL, Docker/Kubernetes, Grafana/Kibana.",
                "Будет плюсом:",
                "- Опыт платформенной разработки и observability.",
            ]
        ),
    )

    result = AnalyzeVacancyWorkflow().run(
        layout=layout,
        store=store,
        request=AnalyzeVacancyRequest(vacancy_id=vacancy_id, llm_provider="fake", llm_model="test"),
    )

    analysis_path = layout.vacancy_dir(vacancy_id) / "analysis.md"
    adoptions_path = layout.vacancy_dir(vacancy_id) / "adoptions.md"
    meta_path = layout.vacancy_dir(vacancy_id) / "meta.yml"
    analysis_text = analysis_path.read_text(encoding="utf-8")
    adoptions_text = adoptions_path.read_text(encoding="utf-8")
    meta_text = meta_path.read_text(encoding="utf-8")
    task_memory = json.loads(store.task_memory_path.read_text(encoding="utf-8"))
    workflow_runs = json.loads(store.workflow_runs_path.read_text(encoding="utf-8"))

    assert result.status == "completed"
    assert "Выбранное резюме: HoE" in analysis_text
    assert "## 1. Анализ соответствия и выбор резюме" in analysis_text
    assert "## 2. Сопроводительное письмо" in analysis_text
    assert "## 3. Входные данные для адаптации резюме" in analysis_text
    assert "Fit score:" in analysis_text
    assert "Уверенность:" in analysis_text
    assert "Полное" in analysis_text or "Частичное" in analysis_text
    assert "### Почему это резюме" in analysis_text
    assert "### Почему не другие" in analysis_text
    assert "### Позиционирование" in analysis_text
    assert "Standard version" in analysis_text
    assert "Short version" in analysis_text
    assert "selected_resume: HoE" in meta_text
    assert "llm_provider: fake" in meta_text
    assert "## Обновление раздела `О себе (профиль)`" in adoptions_text
    assert "## Обновление раздела `Ключевые компетенции`" in adoptions_text
    assert "## Обновление раздела `Опыт работы`" in adoptions_text
    assert "| Before | After | Status | Evidence | Factual Boundary |" in adoptions_text
    assert "TEMP" in adoptions_text
    assert task_memory["active_workflow"] == "analyze-vacancy"
    assert workflow_runs[-1]["workflow"] == "analyze-vacancy"


def test_manual_selected_resume_override_is_marked(monkeypatch: pytest.MonkeyPatch) -> None:
    _, layout, store = build_workspace("analyze-override")
    seed_role_profile(layout, "HoD", ["head of development"], ["delivery"])
    seed_role_profile(layout, "HoE", ["engineering organization"], ["DORA"])
    seed_resume(layout, "HoD", ["# HoD", "- Руководил командами разработки и delivery."])
    seed_resume(layout, "HoE", ["# HoE", "- Руководил engineering organization и DORA improvements."])
    vacancy_id = ingest_vacancy_fixture(
        layout=layout,
        store=store,
        monkeypatch=monkeypatch,
        company="Example",
        position="Head of Engineering",
        source_text="- Lead engineering organization and improve DORA metrics.",
    )

    AnalyzeVacancyWorkflow().run(
        layout=layout,
        store=store,
        request=AnalyzeVacancyRequest(
            vacancy_id=vacancy_id,
            selected_resume="HoD",
            llm_provider="fake",
            llm_model="test",
        ),
    )

    analysis_text = (layout.vacancy_dir(vacancy_id) / "analysis.md").read_text(encoding="utf-8")
    assert "Выбранное резюме: HoD" in analysis_text
    assert "--selected-resume HoD" in analysis_text


def test_role_without_matching_resume_is_excluded_and_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    _, layout, store = build_workspace("analyze-role-diagnostics")
    seed_role_profile(layout, "HoD", ["head of development"], ["delivery"])
    seed_role_profile(layout, "CTO", ["technology strategy"], ["architecture"])
    seed_resume(layout, "HoD", ["# HoD", "- Руководил разработкой и delivery."])
    vacancy_id = ingest_vacancy_fixture(
        layout=layout,
        store=store,
        monkeypatch=monkeypatch,
        company="Example",
        position="Head of Development",
        source_text="- Improve delivery and engineering management.",
    )

    AnalyzeVacancyWorkflow().run(
        layout=layout,
        store=store,
        request=AnalyzeVacancyRequest(vacancy_id=vacancy_id, llm_provider="fake", llm_model="test"),
    )

    analysis_text = (layout.vacancy_dir(vacancy_id) / "analysis.md").read_text(encoding="utf-8")
    assert "resumes/CTO.md" in analysis_text


def test_missing_role_profiles_fail_with_actionable_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _, layout, store = build_workspace("analyze-no-roles")
    seed_resume(layout, "HoD", ["# HoD", "- Руководил разработкой."])
    vacancy_id = ingest_vacancy_fixture(
        layout=layout,
        store=store,
        monkeypatch=monkeypatch,
        company="Example",
        position="Head of Development",
        source_text="- Lead engineering teams.",
    )

    with pytest.raises(AnalyzeVacancyError, match="knowledge/roles/"):
        AnalyzeVacancyWorkflow().run(layout=layout, store=store, request=AnalyzeVacancyRequest(vacancy_id=vacancy_id))


def test_missing_real_llm_config_fails_after_evidence_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    _, layout, store = build_workspace("analyze-openai-missing")
    seed_role_profile(layout, "HoD", ["head of development"], ["delivery"])
    seed_resume(layout, "HoD", ["# HoD", "- Руководил разработкой и delivery."])
    vacancy_id = ingest_vacancy_fixture(
        layout=layout,
        store=store,
        monkeypatch=monkeypatch,
        company="Example",
        position="Head of Development",
        source_text="- Lead engineering teams and improve delivery.",
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("APPLICATION_AGENT_LLM_MODEL", raising=False)

    with pytest.raises(AnalyzeVacancyError, match="OPENAI_API_KEY"):
        AnalyzeVacancyWorkflow().run(
            layout=layout,
            store=store,
            request=AnalyzeVacancyRequest(vacancy_id=vacancy_id, llm_provider="openai", llm_model="gpt-test"),
        )


def test_scoring_methodology_is_explainable_and_russian_terms_are_stable() -> None:
    assessments = [
        RequirementAssessment("[must] A", "A", "must", "evidence", "full", "ok"),
        RequirementAssessment("[must] B", "B", "must", "evidence", "partial", "partial"),
        RequirementAssessment("[nice] C", "C", "nice", "missing", "none", "gap"),
    ]

    fit = compute_fit_result(assessments)

    assert fit.score == 60
    assert "обязательные требования" in fit.rationale
    assert "плюсы" in fit.rationale


def test_analyze_reports_stale_vacancy_reference() -> None:
    _, layout, store = build_workspace("analyze-missing-vacancy")
    analyze = build_default_registry().get("analyze-vacancy")

    with pytest.raises(FileNotFoundError, match="Runtime memory or the provided vacancy_id is stale"):
        analyze.run(layout=layout, store=store, request=AnalyzeVacancyRequest(vacancy_id="20260421-missing-role"))


def ingest_vacancy_fixture(
    *,
    layout: WorkspaceLayout,
    store: JsonMemoryStore,
    monkeypatch: pytest.MonkeyPatch,
    company: str,
    position: str,
    source_text: str,
) -> str:
    monkeypatch.setattr(ingest_vacancy, "validate_response_monitoring_workbook", lambda _layout: None)
    monkeypatch.setattr(ingest_vacancy, "append_ingest_record", lambda *_args, **_kwargs: 1)
    build_default_registry().get("ingest-vacancy").run(
        layout=layout,
        store=store,
        request=IngestVacancyRequest(company=company, position=position, source_text=source_text, language="ru"),
    )
    vacancy_id = store.load_task_memory().active_vacancy_id
    assert vacancy_id is not None
    return vacancy_id


def build_workspace(prefix: str) -> tuple[Path, WorkspaceLayout, JsonMemoryStore]:
    temp_root = Path(__file__).resolve().parents[1] / ".tmp-tests"
    temp_root.mkdir(exist_ok=True)
    workspace_dir = temp_root / f"{prefix}-{uuid.uuid4().hex}"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    layout = WorkspaceLayout(workspace_dir)
    layout.bootstrap()
    store = JsonMemoryStore(layout)
    store.bootstrap()
    return workspace_dir, layout, store


def seed_role_profile(layout: WorkspaceLayout, role_id: str, signals: list[str], ats_terms: list[str]) -> None:
    role_path = layout.knowledge_dir / "roles" / f"{role_id}.md"
    role_path.parent.mkdir(parents=True, exist_ok=True)
    role_path.write_text(
        "\n".join(
            [
                f"# {role_id}",
                "",
                f"- Role: {role_id}",
                "",
                "## Positioning Signals",
                *[f"- {item}" for item in signals],
                "",
                "## Strong Evidence Patterns",
                "- measurable engineering leadership",
                "",
                "## Safe Emphasis Areas",
                "- confirmed leadership and delivery evidence",
                "",
                "## Risky Claims",
                "- неподтверждённый доменный опыт",
                "",
                "## Frequent ATS Terms",
                *[f"- {item}" for item in ats_terms],
                "",
                "## Notes From Processed Vacancies",
                "- test fixture",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )


def seed_resume(layout: WorkspaceLayout, role_id: str, lines: list[str]) -> None:
    layout.resumes_dir.mkdir(parents=True, exist_ok=True)
    (layout.resumes_dir / f"{role_id}.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
