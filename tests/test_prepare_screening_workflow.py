from __future__ import annotations

import json
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from application_agent.memory.store import JsonMemoryStore
from application_agent.workspace import WorkspaceLayout
from application_agent.workflows.analyze_vacancy import AnalyzeVacancyRequest
from application_agent.workflows.ingest_vacancy import IngestVacancyRequest, IngestVacancyWorkflow
from application_agent.workflows.prepare_screening import PrepareScreeningRequest, PrepareScreeningWorkflow


class PrepareScreeningWorkflowTests(unittest.TestCase):
    def test_prepare_screening_creates_artifact_and_updates_memory(self) -> None:
        workspace_dir, layout, store = build_workspace("prepare-screening")
        write_resume(
            workspace_dir,
            "HoD",
            [
                "# HoD Resume",
                "",
                "## О себе (профиль)",
                "",
                "Руковожу инженерными командами и выстраиваю delivery-процессы в критичных бизнес-системах.",
                "",
                "## Опыт работы",
                "",
                "- Руководил четырьмя командами разработки через лидов и улучшил предсказуемость поставки.",
                "- Сократил срок вывода изменений в работу на 30% и выстроил взаимодействие с бизнесом.",
                "- Настраивал архитектурные решения и развитие платформенных контуров.",
            ],
        )

        ingest = IngestVacancyWorkflow()
        prepare = PrepareScreeningWorkflow()

        with patch("application_agent.workflows.ingest_vacancy.append_ingest_record", return_value=7):
            ingest.run(
                layout=layout,
                store=store,
                request=IngestVacancyRequest(
                    company="ПримерТех",
                    position="Руководитель разработки",
                    source_text="\n".join(
                        [
                            "Чем предстоит заниматься:",
                            "- Руководить несколькими командами разработки.",
                            "- Улучшать delivery, процессы и архитектурные решения.",
                            "- Плотно взаимодействовать с бизнесом и смежными подразделениями.",
                        ]
                    ),
                ),
            )

        vacancy_id = store.load_task_memory().active_vacancy_id
        self.assertIsNotNone(vacancy_id)

        from application_agent.workflows.analyze_vacancy import AnalyzeVacancyWorkflow

        AnalyzeVacancyWorkflow().run(
            layout=layout,
            store=store,
            request=AnalyzeVacancyRequest(vacancy_id=vacancy_id),
        )

        result = prepare.run(
            layout=layout,
            store=store,
            request=PrepareScreeningRequest(vacancy_id=vacancy_id or ""),
        )

        screening_path = layout.vacancy_dir(vacancy_id or "") / "screening.md"
        meta_path = layout.vacancy_dir(vacancy_id or "") / "meta.yml"
        screening_text = screening_path.read_text(encoding="utf-8")
        meta_text = meta_path.read_text(encoding="utf-8")
        task_memory = json.loads(store.task_memory_path.read_text(encoding="utf-8"))
        workflow_runs = json.loads(store.workflow_runs_path.read_text(encoding="utf-8"))

        self.assertEqual(result.status, "completed")
        self.assertIn("## Паспорт", screening_text)
        self.assertIn("## Мини-сценарий самопрезентации", screening_text)
        self.assertIn("## Сценарий разговора", screening_text)
        self.assertIn("## Вероятные вопросы на screening", screening_text)
        self.assertIn("Выбранное резюме: HoD", screening_text)
        self.assertIn("status: screening_prepared", meta_text)
        self.assertIn("selected_resume: HoD", meta_text)
        self.assertEqual(task_memory["active_workflow"], "prepare-screening")
        self.assertEqual(len(workflow_runs), 3)
        self.assertEqual(workflow_runs[-1]["workflow"], "prepare-screening")

    def test_prepare_screening_works_with_placeholder_analysis(self) -> None:
        workspace_dir, layout, store = build_workspace("prepare-screening-placeholder")
        write_resume(
            workspace_dir,
            "HoD",
            [
                "# HoD Resume",
                "",
                "## О себе (профиль)",
                "",
                "Управляю командами разработки и улучшаю процессы поставки.",
                "",
                "## Опыт работы",
                "",
                "- Руководил командой разработки и выстраивал процессы планирования.",
                "- Улучшал надёжность сервисов и взаимодействие с бизнесом.",
            ],
        )

        with patch("application_agent.workflows.ingest_vacancy.append_ingest_record", return_value=11):
            IngestVacancyWorkflow().run(
                layout=layout,
                store=store,
                request=IngestVacancyRequest(
                    company="Финтехробот",
                    position="Head of Development",
                    source_text="\n".join(
                        [
                            "What makes you a great fit:",
                            "- Lead multiple engineering teams and improve delivery processes.",
                            "- Partner with product and operations.",
                        ]
                    ),
                ),
            )

        vacancy_id = store.load_task_memory().active_vacancy_id
        self.assertIsNotNone(vacancy_id)

        result = PrepareScreeningWorkflow().run(
            layout=layout,
            store=store,
            request=PrepareScreeningRequest(vacancy_id=vacancy_id or "", preparation_depth="deep"),
        )

        screening_text = (layout.vacancy_dir(vacancy_id or "") / "screening.md").read_text(encoding="utf-8")

        self.assertEqual(result.status, "completed")
        self.assertIn("Выбранное резюме: HoD", screening_text)
        self.assertIn("Глубина подготовки: deep", screening_text)
        self.assertIn("Что стоит подсветить", screening_text)
        self.assertIn("Что спросить в ответ", screening_text)

    def test_prepare_screening_reports_incomplete_vacancy(self) -> None:
        _, layout, store = build_workspace("prepare-screening-missing")

        with self.assertRaisesRegex(
            FileNotFoundError,
            "Runtime memory or the provided vacancy_id is stale",
        ):
            PrepareScreeningWorkflow().run(
                layout=layout,
                store=store,
                request=PrepareScreeningRequest(vacancy_id="20260421-missing-role"),
            )


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


def write_resume(workspace_dir: Path, role: str, lines: list[str]) -> None:
    cv_dir = workspace_dir / "CV"
    cv_dir.mkdir(parents=True, exist_ok=True)
    (cv_dir / f"{role}.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    unittest.main()
