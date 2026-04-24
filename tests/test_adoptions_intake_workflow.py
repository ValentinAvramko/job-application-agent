from __future__ import annotations
import json
import sys
import uuid
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from application_agent.memory.store import JsonMemoryStore
from application_agent.workspace import WorkspaceLayout
from application_agent.workflows.analyze_vacancy import AnalyzeVacancyRequest, AnalyzeVacancyWorkflow
from application_agent.workflows.ingest_vacancy import IngestVacancyRequest, IngestVacancyWorkflow
from application_agent.workflows.intake_adoptions import IntakeAdoptionsRequest, IntakeAdoptionsWorkflow

class TestIntakeAdoptionsWorkflow:

    def test_intake_adoptions_creates_inbox_and_questions_without_downstream_side_effects(self) -> None:
        workspace_dir, layout, store = build_workspace('intake-adoptions')
        write_resume(workspace_dir, 'HoD', ['# HoD Resume', '', '## О себе (профиль)', '', 'Руковожу инженерными командами и выстраиваю delivery-процессы в критичных бизнес-системах.', '', '## Опыт работы', '', '- Руководил несколькими командами разработки через лидов и улучшал предсказуемость поставки.', '- Сократил срок вывода изменений в работу и усилил взаимодействие с бизнесом.', '- Настраивал архитектурные решения и платформенные контуры.'])
        accepted_master = layout.adoptions_dir / 'accepted' / 'MASTER.md'
        knowledge_role = layout.knowledge_dir / 'roles' / 'HoD.md'
        resume_master = layout.resumes_dir / 'MASTER.md'
        accepted_master.write_text('# Accepted\n\n- stable\n', encoding='utf-8', newline='\n')
        knowledge_role.write_text('# HoD Signals\n\n- stable\n', encoding='utf-8', newline='\n')
        resume_master.write_text('# MASTER Resume\n\n- stable\n', encoding='utf-8', newline='\n')
        accepted_before = accepted_master.read_text(encoding='utf-8')
        knowledge_before = knowledge_role.read_text(encoding='utf-8')
        resume_before = resume_master.read_text(encoding='utf-8')
        vacancy_id = seed_analyzed_vacancy(layout=layout, store=store)
        workflow = IntakeAdoptionsWorkflow()
        result = workflow.run(layout=layout, store=store, request=IntakeAdoptionsRequest(vacancy_id=vacancy_id))
        inbox_path = layout.adoptions_dir / 'inbox' / f'{vacancy_id}.md'
        questions_path = layout.adoptions_dir / 'questions' / 'open.md'
        inbox_text = inbox_path.read_text(encoding='utf-8')
        questions_text = questions_path.read_text(encoding='utf-8')
        task_memory = json.loads(store.task_memory_path.read_text(encoding='utf-8'))
        workflow_runs = json.loads(store.workflow_runs_path.read_text(encoding='utf-8'))
        assert result.status == 'completed'
        assert '# Adoptions Inbox' in inbox_text
        assert f'- Vacancy ID: {vacancy_id}' in inbox_text
        assert '- Company: ПримерТех' in inbox_text
        assert '- Position: Руководитель разработки' in inbox_text
        assert '- Selected Resume: HoD' in inbox_text
        assert '## TEMP' in inbox_text
        assert '## PERM' in inbox_text
        assert '## NEW DATA NEEDED' in inbox_text
        assert 'Change: Short Summary' in inbox_text
        assert 'Factual Boundary:' in inbox_text
        assert '## Pending' in questions_text
        assert vacancy_id in questions_text
        assert 'pending' in questions_text
        assert task_memory['active_workflow'] == 'intake-adoptions'
        assert task_memory['active_vacancy_id'] == vacancy_id
        assert workflow_runs[-1]['workflow'] == 'intake-adoptions'
        assert accepted_master.read_text(encoding='utf-8') == accepted_before
        assert knowledge_role.read_text(encoding='utf-8') == knowledge_before
        assert resume_master.read_text(encoding='utf-8') == resume_before

    def test_intake_adoptions_is_idempotent_for_inbox_and_pending_questions(self) -> None:
        workspace_dir, layout, store = build_workspace('intake-adoptions-idempotent')
        write_resume(workspace_dir, 'HoD', ['# HoD Resume', '', '## О себе (профиль)', '', 'Руковожу командами разработки и улучшаю delivery-процессы.', '', '## Опыт работы', '', '- Руководил командой разработки и выстраивал процессы поставки.', '- Улучшал архитектурные решения и взаимодействие с бизнесом.'])
        vacancy_id = seed_analyzed_vacancy(layout=layout, store=store)
        workflow = IntakeAdoptionsWorkflow()
        workflow.run(layout=layout, store=store, request=IntakeAdoptionsRequest(vacancy_id=vacancy_id))
        inbox_path = layout.adoptions_dir / 'inbox' / f'{vacancy_id}.md'
        questions_path = layout.adoptions_dir / 'questions' / 'open.md'
        inbox_first = inbox_path.read_text(encoding='utf-8')
        questions_first = questions_path.read_text(encoding='utf-8')
        workflow.run(layout=layout, store=store, request=IntakeAdoptionsRequest(vacancy_id=vacancy_id))
        inbox_second = inbox_path.read_text(encoding='utf-8')
        questions_second = questions_path.read_text(encoding='utf-8')
        assert inbox_first == inbox_second
        assert questions_first == questions_second
        assert questions_second.count(vacancy_id) >= 1

def seed_analyzed_vacancy(*, layout: WorkspaceLayout, store: JsonMemoryStore) -> str:
    ingest = IngestVacancyWorkflow()
    analyze = AnalyzeVacancyWorkflow()
    role_path = layout.knowledge_dir / 'roles' / 'HoD.md'
    if not role_path.exists():
        role_path.write_text('\n'.join(['# HoD', '', '- Role: HoD', '', '## Positioning Signals', '- head of development', '- delivery', '', '## Strong Evidence Patterns', '- engineering leadership', '', '## Safe Emphasis Areas', '- confirmed leadership evidence', '', '## Risky Claims', '- unsupported domain claims', '', '## Frequent ATS Terms', '- architecture', '- delivery', '', '## Notes From Processed Vacancies', '- fixture']) + '\n', encoding='utf-8', newline='\n')
    with patch('application_agent.workflows.ingest_vacancy.validate_response_monitoring_workbook', return_value=None), patch('application_agent.workflows.ingest_vacancy.append_ingest_record', return_value=13):
        ingest.run(layout=layout, store=store, request=IngestVacancyRequest(company='ПримерТех', position='Руководитель разработки', source_text='\n'.join(['Чем предстоит заниматься:', '- Руководить несколькими командами разработки.', '- Улучшать delivery, процессы и архитектурные решения.', '- Плотно взаимодействовать с бизнесом и смежными подразделениями.'])))
    vacancy_id = store.load_task_memory().active_vacancy_id
    if not vacancy_id:
        raise AssertionError('Expected active vacancy id after ingest.')
    analyze.run(layout=layout, store=store, request=AnalyzeVacancyRequest(vacancy_id=vacancy_id, llm_provider='fake', llm_model='test'))
    return vacancy_id

def build_workspace(prefix: str) -> tuple[Path, WorkspaceLayout, JsonMemoryStore]:
    temp_root = Path(__file__).resolve().parents[1] / '.tmp-tests'
    temp_root.mkdir(exist_ok=True)
    workspace_dir = temp_root / f'{prefix}-{uuid.uuid4().hex}'
    workspace_dir.mkdir(parents=True, exist_ok=True)
    layout = WorkspaceLayout(workspace_dir)
    layout.bootstrap()
    store = JsonMemoryStore(layout)
    store.bootstrap()
    return (workspace_dir, layout, store)

def write_resume(workspace_dir: Path, role: str, lines: list[str]) -> None:
    resumes_dir = workspace_dir / 'resumes'
    resumes_dir.mkdir(parents=True, exist_ok=True)
    (resumes_dir / f'{role}.md').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
