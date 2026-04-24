from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkspaceLayout:
    root: Path

    @property
    def vacancies_dir(self) -> Path:
        return self.root / "vacancies"

    @property
    def adoptions_dir(self) -> Path:
        return self.root / "adoptions"

    @property
    def knowledge_dir(self) -> Path:
        return self.root / "knowledge"

    @property
    def profile_dir(self) -> Path:
        return self.root / "profile"

    @property
    def resumes_dir(self) -> Path:
        return self.root / "resumes"

    @property
    def agent_memory_dir(self) -> Path:
        return self.root / "agent_memory"

    @property
    def runtime_memory_dir(self) -> Path:
        return self.agent_memory_dir / "runtime"

    @property
    def config_dir(self) -> Path:
        return self.agent_memory_dir / "config"

    @property
    def workflow_specs_dir(self) -> Path:
        return self.agent_memory_dir / "workflows"

    @property
    def prompts_dir(self) -> Path:
        return self.agent_memory_dir / "prompts"

    @property
    def schema_dir(self) -> Path:
        return self.agent_memory_dir / "schemas"

    def vacancy_dir(self, vacancy_id: str) -> Path:
        return self.vacancies_dir / vacancy_id

    def bootstrap(self) -> list[Path]:
        directories = [
            self.vacancies_dir,
            self.adoptions_dir / "inbox",
            self.adoptions_dir / "accepted",
            self.adoptions_dir / "questions",
            self.knowledge_dir / "roles",
            self.knowledge_dir / "company_signals",
            self.profile_dir,
            self.config_dir,
            self.workflow_specs_dir,
            self.prompts_dir / "analyze-vacancy",
            self.schema_dir,
            self.runtime_memory_dir,
        ]
        created: list[Path] = []
        for directory in directories:
            if not directory.exists():
                created.append(directory)
            directory.mkdir(parents=True, exist_ok=True)
        return created

