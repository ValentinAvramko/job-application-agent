from __future__ import annotations

import json
import sys
import unittest
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from application_agent.memory.store import JsonMemoryStore
from application_agent.workspace import WorkspaceLayout


class MemoryStoreTests(unittest.TestCase):
    def test_bootstrap_creates_runtime_files(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f"memory-store-{uuid.uuid4().hex}"
        workspace_dir.mkdir(parents=True, exist_ok=True)

        layout = WorkspaceLayout(workspace_dir)
        layout.bootstrap()
        store = JsonMemoryStore(layout)
        store.bootstrap()

        self.assertTrue(store.task_memory_path.exists())
        self.assertTrue(store.project_memory_path.exists())
        self.assertTrue(store.user_memory_path.exists())
        self.assertTrue(store.workflow_runs_path.exists())

        project_memory = json.loads(store.project_memory_path.read_text(encoding="utf-8"))
        self.assertNotIn("bootstrap", project_memory["workflow_catalog"])
        self.assertIn("ingest-vacancy", project_memory["workflow_catalog"])
        self.assertIn("analyze-vacancy", project_memory["workflow_catalog"])
        self.assertIn("prepare-screening", project_memory["workflow_catalog"])
        self.assertIn("intake-adoptions", project_memory["workflow_catalog"])
        self.assertIn("rebuild-master", project_memory["workflow_catalog"])
        self.assertIn("rebuild-role-resume", project_memory["workflow_catalog"])
        self.assertIn("build-linkedin", project_memory["workflow_catalog"])

    def test_bootstrap_rewrites_workflow_catalog_to_runtime_defaults(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f"memory-store-upgrade-{uuid.uuid4().hex}"
        workspace_dir.mkdir(parents=True, exist_ok=True)

        layout = WorkspaceLayout(workspace_dir)
        layout.bootstrap()
        store = JsonMemoryStore(layout)
        store.bootstrap()

        legacy_payload = {
            "workflow_catalog": ["bootstrap", "ingest-vacancy"],
            "role_resumes": ["CIO"],
            "contact_regions": ["RU"],
            "last_updated": "2026-04-20T00:00:00+00:00",
        }
        store.project_memory_path.write_text(json.dumps(legacy_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        store.bootstrap()

        project_memory = json.loads(store.project_memory_path.read_text(encoding="utf-8"))
        self.assertEqual(
            project_memory["workflow_catalog"],
            [
                "ingest-vacancy",
                "analyze-vacancy",
                "prepare-screening",
                "intake-adoptions",
                "rebuild-master",
                "rebuild-role-resume",
                "build-linkedin",
            ],
        )
        self.assertEqual(project_memory["role_resumes"], ["CIO", "CTO", "HoE", "HoD", "EM"])
        self.assertEqual(project_memory["contact_regions"], ["RU", "KZ", "EU"])

    def test_snapshot_reports_stale_runtime_references(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f"memory-store-reconcile-{uuid.uuid4().hex}"
        workspace_dir.mkdir(parents=True, exist_ok=True)

        layout = WorkspaceLayout(workspace_dir)
        layout.bootstrap()
        store = JsonMemoryStore(layout)
        store.bootstrap()

        missing_artifact = str(layout.vacancy_dir("20260421-missing-role") / "meta.yml")
        store.task_memory_path.write_text(
            json.dumps(
                {
                    "active_workflow": "ingest-vacancy",
                    "active_vacancy_id": "20260421-missing-role",
                    "active_artifacts": [missing_artifact],
                    "updated_at": "2026-04-21T00:00:00+00:00",
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        store.workflow_runs_path.write_text(
            json.dumps(
                [
                    {
                        "workflow": "ingest-vacancy",
                        "status": "completed",
                        "started_at": "2026-04-21T00:00:00+00:00",
                        "completed_at": "2026-04-21T00:00:01+00:00",
                        "artifacts": [missing_artifact],
                        "summary": "Created vacancy scaffold.",
                    }
                ],
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        snapshot = store.snapshot()

        self.assertEqual(snapshot["reconciliation"]["task_memory"]["status"], "stale")
        self.assertFalse(snapshot["reconciliation"]["task_memory"]["vacancy_dir_exists"])
        self.assertEqual(snapshot["reconciliation"]["task_memory"]["missing_artifacts"], [missing_artifact])
        self.assertEqual(snapshot["reconciliation"]["workflow_runs"]["stale_run_count"], 1)
        self.assertEqual(
            snapshot["reconciliation"]["workflow_runs"]["runs_with_missing_artifacts"][0]["missing_artifacts"],
            [missing_artifact],
        )


if __name__ == "__main__":
    unittest.main()
