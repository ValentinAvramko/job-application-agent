from __future__ import annotations

import json
from dataclasses import fields
from datetime import datetime, timezone
from pathlib import Path

from application_agent.config import CONTACT_REGIONS, ROLE_RESUMES, WORKFLOW_CATALOG
from application_agent.memory.models import ProjectMemory, TaskMemory, UserMemory, WorkflowRun
from application_agent.workspace import WorkspaceLayout


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class JsonMemoryStore:
    def __init__(self, layout: WorkspaceLayout) -> None:
        self.layout = layout
        self.layout.runtime_memory_dir.mkdir(parents=True, exist_ok=True)

    @property
    def task_memory_path(self) -> Path:
        return self.layout.runtime_memory_dir / "task-memory.json"

    @property
    def project_memory_path(self) -> Path:
        return self.layout.runtime_memory_dir / "project-memory.json"

    @property
    def user_memory_path(self) -> Path:
        return self.layout.runtime_memory_dir / "user-memory.json"

    @property
    def workflow_runs_path(self) -> Path:
        return self.layout.runtime_memory_dir / "workflow-runs.json"

    def bootstrap(self) -> None:
        now = utc_now_iso()
        self._write_if_missing(self.task_memory_path, TaskMemory(updated_at=now).to_dict())
        self._write_if_missing(
            self.project_memory_path,
            ProjectMemory(
                workflow_catalog=list(WORKFLOW_CATALOG),
                role_resumes=list(ROLE_RESUMES),
                contact_regions=list(CONTACT_REGIONS),
                last_updated=now,
            ).to_dict(),
        )
        self._write_if_missing(self.user_memory_path, UserMemory(last_updated=now).to_dict())
        self._write_if_missing(self.workflow_runs_path, [])
        self._sync_project_memory_defaults(now)

    def load_task_memory(self) -> TaskMemory:
        self.bootstrap()
        return self._load_dataclass(self.task_memory_path, TaskMemory)

    def load_project_memory(self) -> ProjectMemory:
        self.bootstrap()
        return self._load_dataclass(self.project_memory_path, ProjectMemory)

    def load_user_memory(self) -> UserMemory:
        self.bootstrap()
        return self._load_dataclass(self.user_memory_path, UserMemory)

    def load_workflow_runs(self) -> list[dict[str, object]]:
        self.bootstrap()
        with self.workflow_runs_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def remember_task(self, workflow: str, vacancy_id: str | None, artifacts: list[str]) -> None:
        task_memory = TaskMemory(
            active_workflow=workflow,
            active_vacancy_id=vacancy_id,
            active_artifacts=artifacts,
            updated_at=utc_now_iso(),
        )
        self._write_json(self.task_memory_path, task_memory.to_dict())

    def append_run(self, workflow_run: WorkflowRun) -> None:
        workflow_runs = self.load_workflow_runs()
        workflow_runs.append(workflow_run.to_dict())
        self._write_json(self.workflow_runs_path, workflow_runs)

    def snapshot(self) -> dict[str, object]:
        task_memory = self.load_task_memory()
        workflow_runs = self.load_workflow_runs()
        return {
            "task_memory": task_memory.to_dict(),
            "project_memory": self.load_project_memory().to_dict(),
            "user_memory": self.load_user_memory().to_dict(),
            "workflow_runs": workflow_runs,
            "reconciliation": self.build_reconciliation_report(task_memory, workflow_runs),
        }

    def build_reconciliation_report(
        self, task_memory: TaskMemory | None = None, workflow_runs: list[dict[str, object]] | None = None
    ) -> dict[str, object]:
        task_memory = task_memory or self.load_task_memory()
        workflow_runs = workflow_runs or self.load_workflow_runs()

        active_vacancy_id = task_memory.active_vacancy_id
        vacancy_dir_exists = bool(active_vacancy_id) and self.layout.vacancy_dir(active_vacancy_id).exists()
        missing_task_artifacts = self._missing_paths(task_memory.active_artifacts)

        if not active_vacancy_id and not task_memory.active_artifacts:
            task_status = "empty"
        elif vacancy_dir_exists and not missing_task_artifacts:
            task_status = "ok"
        else:
            task_status = "stale"

        stale_runs: list[dict[str, object]] = []
        for run in workflow_runs:
            artifacts = run.get("artifacts")
            if not isinstance(artifacts, list):
                continue

            missing_artifacts = self._missing_paths(artifacts)
            if not missing_artifacts:
                continue

            stale_runs.append(
                {
                    "workflow": run.get("workflow"),
                    "completed_at": run.get("completed_at"),
                    "missing_artifacts": missing_artifacts,
                }
            )

        return {
            "task_memory": {
                "status": task_status,
                "active_vacancy_id": active_vacancy_id,
                "vacancy_dir_exists": vacancy_dir_exists,
                "missing_artifacts": missing_task_artifacts,
            },
            "workflow_runs": {
                "stale_run_count": len(stale_runs),
                "runs_with_missing_artifacts": stale_runs,
            },
        }

    def _load_dataclass(self, path: Path, model_cls):
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        allowed_keys = {field.name for field in fields(model_cls)}
        filtered = {key: value for key, value in payload.items() if key in allowed_keys}
        return model_cls(**filtered)

    def _write_if_missing(self, path: Path, payload: object) -> None:
        if not path.exists():
            self._write_json(path, payload)

    def _sync_project_memory_defaults(self, now: str) -> None:
        with self.project_memory_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        changed = False
        changed |= self._sync_exact_ordered_list(payload, "workflow_catalog", WORKFLOW_CATALOG)
        changed |= self._merge_ordered_defaults(payload, "role_resumes", ROLE_RESUMES)
        changed |= self._merge_ordered_defaults(payload, "contact_regions", CONTACT_REGIONS)

        if changed:
            payload["last_updated"] = now
            self._write_json(self.project_memory_path, payload)

    def _merge_ordered_defaults(self, payload: dict[str, object], key: str, defaults: tuple[str, ...]) -> bool:
        values = payload.get(key)
        if not isinstance(values, list):
            payload[key] = list(defaults)
            return True

        changed = False
        for item in defaults:
            if item not in values:
                values.append(item)
                changed = True
        return changed

    def _sync_exact_ordered_list(self, payload: dict[str, object], key: str, defaults: tuple[str, ...]) -> bool:
        target = list(defaults)
        values = payload.get(key)
        if values == target:
            return False
        payload[key] = target
        return True

    def _write_json(self, path: Path, payload: object) -> None:
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

    def _missing_paths(self, paths: list[object]) -> list[str]:
        missing: list[str] = []
        for value in paths:
            if not isinstance(value, str):
                continue
            if not Path(value).exists():
                missing.append(value)
        return missing

