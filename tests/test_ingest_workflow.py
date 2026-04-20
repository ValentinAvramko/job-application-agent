from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from application_agent.memory.store import JsonMemoryStore
from application_agent.workspace import WorkspaceLayout
from application_agent.workflows.ingest_vacancy import IngestVacancyRequest, build_vacancy_id
from application_agent.workflows.registry import build_default_registry


class IngestWorkflowTests(unittest.TestCase):
    def test_ingest_creates_vacancy_scaffold_and_memory(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as tmpdir:
            layout = WorkspaceLayout(Path(tmpdir))
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
            company="Тестовая Компания",
            position="Руководитель разработки",
        )
        self.assertEqual(vacancy_id, "20260420-testovaya-kompaniya-rukovoditel-razrabotki")


if __name__ == "__main__":
    unittest.main()
