from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from application_agent.memory.store import JsonMemoryStore
from application_agent.workspace import WorkspaceLayout


@dataclass
class WorkflowResult:
    workflow: str
    status: str
    summary: str
    artifacts: list[str] = field(default_factory=list)


class Workflow(Protocol):
    name: str
    description: str

    def run(self, *, layout: WorkspaceLayout, store: JsonMemoryStore, **kwargs) -> WorkflowResult:
        ...

