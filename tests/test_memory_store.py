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
        self.assertIn("ingest-vacancy", project_memory["workflow_catalog"])
        self.assertIn("analyze-vacancy", project_memory["workflow_catalog"])

    def test_bootstrap_backfills_new_project_catalog_entries(self) -> None:
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
        self.assertEqual(project_memory["workflow_catalog"], ["bootstrap", "ingest-vacancy", "analyze-vacancy"])
        self.assertEqual(project_memory["role_resumes"], ["CIO", "CTO", "HoE", "HoD", "EM"])
        self.assertEqual(project_memory["contact_regions"], ["RU", "KZ", "EU"])


if __name__ == "__main__":
    unittest.main()
