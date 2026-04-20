from __future__ import annotations

import json
import sys
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from application_agent.memory.store import JsonMemoryStore
from application_agent.workspace import WorkspaceLayout
from application_agent.workflows.analyze_vacancy import AnalyzeVacancyRequest
from application_agent.workflows.ingest_vacancy import IngestVacancyRequest
from application_agent.workflows.registry import build_default_registry


class AnalyzeWorkflowTests(unittest.TestCase):
    def test_analyze_updates_vacancy_files_and_memory(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f"analyze-workflow-{uuid.uuid4().hex}"
        workspace_dir.mkdir(parents=True, exist_ok=True)

        layout = WorkspaceLayout(workspace_dir)
        layout.bootstrap()
        store = JsonMemoryStore(layout)
        store.bootstrap()

        cv_dir = workspace_dir / "CV"
        cv_dir.mkdir(parents=True, exist_ok=True)
        (cv_dir / "HoE.md").write_text(
            "\n".join(
                [
                    "# HoE Resume",
                    "- Led engineering teams across platform and delivery domains.",
                    "- Built platform strategy, architecture review, and cross-functional execution model.",
                    "- Scaled managers and senior engineers in a multi-team environment.",
                    "",
                ]
            ),
            encoding="utf-8",
            newline="\n",
        )

        registry = build_default_registry()
        ingest = registry.get("ingest-vacancy")
        analyze = registry.get("analyze-vacancy")

        ingest.run(
            layout=layout,
            store=store,
            request=IngestVacancyRequest(
                company="TaxDome",
                position="VP of Engineering",
                source_text="\n".join(
                    [
                        "Responsibilities:",
                        "- Lead multiple engineering teams and managers.",
                        "- Drive platform strategy, architecture decisions, and delivery execution.",
                        "- Partner with product and operations on company-wide priorities.",
                    ]
                ),
            ),
        )

        vacancy_id = store.load_task_memory().active_vacancy_id
        self.assertIsNotNone(vacancy_id)

        result = analyze.run(
            layout=layout,
            store=store,
            request=AnalyzeVacancyRequest(vacancy_id=vacancy_id),
        )

        self.assertEqual(result.status, "completed")

        analysis_path = layout.vacancy_dir(vacancy_id) / "analysis.md"
        meta_path = layout.vacancy_dir(vacancy_id) / "meta.yml"
        adoptions_path = layout.vacancy_dir(vacancy_id) / "adoptions.md"

        analysis_text = analysis_path.read_text(encoding="utf-8")
        meta_text = meta_path.read_text(encoding="utf-8")
        adoptions_text = adoptions_path.read_text(encoding="utf-8")
        task_memory = json.loads(store.task_memory_path.read_text(encoding="utf-8"))
        workflow_runs = json.loads(store.workflow_runs_path.read_text(encoding="utf-8"))

        self.assertIn("Selected Resume: HoE", analysis_text)
        self.assertIn("status: analyzed", meta_text)
        self.assertIn("selected_resume: HoE", meta_text)
        self.assertIn("Permanent Candidates", adoptions_text)
        self.assertEqual(task_memory["active_workflow"], "analyze-vacancy")
        self.assertEqual(len(workflow_runs), 2)


if __name__ == "__main__":
    unittest.main()
