from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class TaskMemory:
    active_workflow: str | None = None
    active_vacancy_id: str | None = None
    active_artifacts: list[str] = field(default_factory=list)
    updated_at: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class ProjectMemory:
    workflow_catalog: list[str] = field(default_factory=list)
    role_resumes: list[str] = field(default_factory=list)
    contact_regions: list[str] = field(default_factory=list)
    last_updated: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class UserMemory:
    confirmed_facts: list[str] = field(default_factory=list)
    preferences: dict[str, object] = field(default_factory=dict)
    last_updated: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class WorkflowRun:
    workflow: str
    status: str
    started_at: str
    completed_at: str
    artifacts: list[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

