from __future__ import annotations

from application_agent.workflows.analyze_vacancy import AnalyzeVacancyWorkflow
from application_agent.workflows.ingest_vacancy import IngestVacancyWorkflow
from application_agent.workflows.intake_adoptions import IntakeAdoptionsWorkflow
from application_agent.workflows.prepare_screening import PrepareScreeningWorkflow


class WorkflowRegistry:
    def __init__(self) -> None:
        self._workflows: dict[str, object] = {}

    def register(self, workflow: object) -> None:
        name = getattr(workflow, "name")
        self._workflows[name] = workflow

    def get(self, name: str) -> object:
        try:
            return self._workflows[name]
        except KeyError as exc:
            known = ", ".join(sorted(self._workflows))
            raise KeyError(f"Unknown workflow '{name}'. Known workflows: {known}") from exc

    def items(self) -> list[tuple[str, object]]:
        return sorted(self._workflows.items(), key=lambda item: item[0])


def build_default_registry() -> WorkflowRegistry:
    registry = WorkflowRegistry()
    registry.register(AnalyzeVacancyWorkflow())
    registry.register(IngestVacancyWorkflow())
    registry.register(IntakeAdoptionsWorkflow())
    registry.register(PrepareScreeningWorkflow())
    return registry
