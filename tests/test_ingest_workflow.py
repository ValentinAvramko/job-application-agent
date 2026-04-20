from __future__ import annotations

import json
import sys
import unittest
import uuid
from datetime import date
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from application_agent.memory.store import JsonMemoryStore
from application_agent.workspace import WorkspaceLayout
from application_agent.workflows.ingest_vacancy import (
    IngestVacancyRequest,
    VacancySourceDetails,
    build_vacancy_id,
    parse_generic_vacancy_page,
    parse_hh_vacancy_payload,
)
from application_agent.workflows.registry import build_default_registry


class IngestWorkflowTests(unittest.TestCase):
    def test_ingest_creates_vacancy_scaffold_and_memory(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f"ingest-workflow-{uuid.uuid4().hex}"
        workspace_dir.mkdir(parents=True, exist_ok=True)

        layout = WorkspaceLayout(workspace_dir)
        layout.bootstrap()
        store = JsonMemoryStore(layout)
        store.bootstrap()
        workflow = build_default_registry().get("ingest-vacancy")

        result = workflow.run(
            layout=layout,
            store=store,
            request=IngestVacancyRequest(
                company="Citix",
                position="CIO",
                source_text="Platform strategy and team leadership.",
            ),
        )

        self.assertEqual(result.status, "completed")
        self.assertEqual(len(result.artifacts), 4)

        task_memory = json.loads(store.task_memory_path.read_text(encoding="utf-8"))
        self.assertEqual(task_memory["active_workflow"], "ingest-vacancy")
        self.assertTrue(task_memory["active_vacancy_id"].startswith("20"))

    def test_build_vacancy_id_transliterates_cyrillic(self) -> None:
        vacancy_id = build_vacancy_id(
            day=date(2026, 4, 20),
            company="\u0422\u0435\u0441\u0442\u043e\u0432\u0430\u044f \u041a\u043e\u043c\u043f\u0430\u043d\u0438\u044f",
            position="\u0420\u0443\u043a\u043e\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u044c \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0438",
        )
        self.assertEqual(vacancy_id, "20260420-testovaya-kompaniya-rukovoditel-razrabotki")

    def test_ingest_can_fill_company_position_and_text_from_source_url(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f"ingest-workflow-{uuid.uuid4().hex}"
        workspace_dir.mkdir(parents=True, exist_ok=True)

        layout = WorkspaceLayout(workspace_dir)
        layout.bootstrap()
        store = JsonMemoryStore(layout)
        store.bootstrap()
        workflow = build_default_registry().get("ingest-vacancy")

        with patch(
            "application_agent.workflows.ingest_vacancy.fetch_source_details",
            return_value=VacancySourceDetails(
                company="\u0424\u0438\u043d\u0442\u0435\u0445\u0440\u043e\u0431\u043e\u0442",
                position="Head of Development / \u0420\u0443\u043a\u043e\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u044c \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0438",
                source_text="\u0420\u0443\u043a\u043e\u0432\u043e\u0434\u0438\u0442\u044c \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u043e\u0439, delivery \u0438 \u0430\u0440\u0445\u0438\u0442\u0435\u043a\u0442\u0443\u0440\u043e\u0439.",
            ),
        ):
            result = workflow.run(
                layout=layout,
                store=store,
                request=IngestVacancyRequest(source_url="https://hh.ru/vacancy/132114761"),
            )

        vacancy_id = store.load_task_memory().active_vacancy_id
        self.assertEqual(result.status, "completed")
        self.assertIsNotNone(vacancy_id)

        vacancy_dir = layout.vacancy_dir(vacancy_id)
        meta_text = (vacancy_dir / "meta.yml").read_text(encoding="utf-8")
        source_text = (vacancy_dir / "source.md").read_text(encoding="utf-8")

        self.assertIn("company: \u0424\u0438\u043d\u0442\u0435\u0445\u0440\u043e\u0431\u043e\u0442", meta_text)
        self.assertIn(
            "position: Head of Development / \u0420\u0443\u043a\u043e\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u044c \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0438",
            meta_text,
        )
        self.assertIn(
            "\u0420\u0443\u043a\u043e\u0432\u043e\u0434\u0438\u0442\u044c \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u043e\u0439, delivery \u0438 \u0430\u0440\u0445\u0438\u0442\u0435\u043a\u0442\u0443\u0440\u043e\u0439.",
            source_text,
        )

    def test_parse_hh_vacancy_payload_extracts_fields(self) -> None:
        payload = json.dumps(
            {
                "name": "Head of Development / \u0420\u0443\u043a\u043e\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u044c \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0438",
                "employer": {"name": "\u0424\u0438\u043d\u0442\u0435\u0445\u0440\u043e\u0431\u043e\u0442"},
                "description": "<p>\u041d\u0443\u0436\u043d\u043e \u0440\u0443\u043a\u043e\u0432\u043e\u0434\u0438\u0442\u044c \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u043e\u0439.</p><ul><li>\u0423\u043b\u0443\u0447\u0448\u0430\u0442\u044c delivery</li></ul>",
                "language": "ru",
            },
            ensure_ascii=False,
        )

        details = parse_hh_vacancy_payload(payload)

        self.assertEqual(details.company, "\u0424\u0438\u043d\u0442\u0435\u0445\u0440\u043e\u0431\u043e\u0442")
        self.assertEqual(
            details.position,
            "Head of Development / \u0420\u0443\u043a\u043e\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u044c \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0438",
        )
        self.assertIn("\u041d\u0443\u0436\u043d\u043e \u0440\u0443\u043a\u043e\u0432\u043e\u0434\u0438\u0442\u044c \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u043e\u0439.", details.source_text)
        self.assertIn("\u0423\u043b\u0443\u0447\u0448\u0430\u0442\u044c delivery", details.source_text)
        self.assertEqual(details.language, "ru")

    def test_parse_generic_vacancy_page_uses_structured_data(self) -> None:
        html = """
        <html lang="ru">
          <head>
            <title>\u0412\u0430\u043a\u0430\u043d\u0441\u0438\u044f Head of Development \u0432 \u043a\u043e\u043c\u043f\u0430\u043d\u0438\u0438 \u0424\u0438\u043d\u0442\u0435\u0445\u0440\u043e\u0431\u043e\u0442</title>
            <meta property="og:title" content="\u0412\u0430\u043a\u0430\u043d\u0441\u0438\u044f Head of Development \u0432 \u043a\u043e\u043c\u043f\u0430\u043d\u0438\u0438 \u0424\u0438\u043d\u0442\u0435\u0445\u0440\u043e\u0431\u043e\u0442" />
            <script type="application/ld+json">
              {
                "@context": "https://schema.org",
                "@type": "JobPosting",
                "title": "Head of Development",
                "description": "<p>\u0423\u043f\u0440\u0430\u0432\u043b\u044f\u0442\u044c \u043a\u043e\u043c\u0430\u043d\u0434\u043e\u0439 \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0438 \u0438 delivery.</p>",
                "hiringOrganization": {"@type": "Organization", "name": "\u0424\u0438\u043d\u0442\u0435\u0445\u0440\u043e\u0431\u043e\u0442"}
              }
            </script>
          </head>
          <body>
            <h1>Head of Development</h1>
          </body>
        </html>
        """

        details = parse_generic_vacancy_page(html)

        self.assertEqual(details.company, "\u0424\u0438\u043d\u0442\u0435\u0445\u0440\u043e\u0431\u043e\u0442")
        self.assertEqual(details.position, "Head of Development")
        self.assertIn("\u0423\u043f\u0440\u0430\u0432\u043b\u044f\u0442\u044c \u043a\u043e\u043c\u0430\u043d\u0434\u043e\u0439 \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0438 \u0438 delivery.", details.source_text)
        self.assertEqual(details.language, "ru")


if __name__ == "__main__":
    unittest.main()
