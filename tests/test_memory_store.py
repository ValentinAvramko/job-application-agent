from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from application_agent.memory.store import JsonMemoryStore
from application_agent.workspace import WorkspaceLayout


class MemoryStoreTests(unittest.TestCase):
    def test_bootstrap_creates_runtime_files(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=temp_root) as tmpdir:
            layout = WorkspaceLayout(Path(tmpdir))
            layout.bootstrap()
            store = JsonMemoryStore(layout)
            store.bootstrap()

            self.assertTrue(store.task_memory_path.exists())
            self.assertTrue(store.project_memory_path.exists())
            self.assertTrue(store.user_memory_path.exists())
            self.assertTrue(store.workflow_runs_path.exists())

            project_memory = json.loads(store.project_memory_path.read_text(encoding="utf-8"))
            self.assertIn("ingest-vacancy", project_memory["workflow_catalog"])


if __name__ == "__main__":
    unittest.main()
