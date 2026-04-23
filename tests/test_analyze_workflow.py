from __future__ import annotations
import pytest
import json
import sys
import uuid
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from application_agent.memory.store import JsonMemoryStore
from application_agent.workspace import WorkspaceLayout
from application_agent.workflows.analyze_vacancy import AnalyzeVacancyRequest
from application_agent.workflows.ingest_vacancy import IngestVacancyRequest
from application_agent.workflows.registry import build_default_registry

class TestAnalyzeWorkflow:

    def test_analyze_updates_vacancy_files_and_memory(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / '.tmp-tests'
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f'analyze-workflow-{uuid.uuid4().hex}'
        workspace_dir.mkdir(parents=True, exist_ok=True)
        layout = WorkspaceLayout(workspace_dir)
        layout.bootstrap()
        store = JsonMemoryStore(layout)
        store.bootstrap()
        resumes_dir = workspace_dir / 'resumes'
        resumes_dir.mkdir(parents=True, exist_ok=True)
        (resumes_dir / 'HoD.md').write_text('\n'.join(['# HoD Resume', '- Руководил командами разработки и развивал лидов.', '- Выстраивал процессы поставки, декомпозиции и кросс-функционального взаимодействия.', '- Улучшал архитектурные решения и стабильность ключевых сервисов.', '']), encoding='utf-8', newline='\n')
        registry = build_default_registry()
        ingest = registry.get('ingest-vacancy')
        analyze = registry.get('analyze-vacancy')
        with patch('application_agent.workflows.ingest_vacancy.validate_response_monitoring_workbook', return_value=None), patch('application_agent.workflows.ingest_vacancy.append_ingest_record', return_value=3):
            ingest.run(layout=layout, store=store, request=IngestVacancyRequest(company='ПримерТех', position='Руководитель разработки', source_text='\n'.join(['Чем предстоит заниматься:', '- Руководить командой разработки и развивать тимлидов.', '- Улучшать процессы планирования, декомпозиции и поставки.', '- Участвовать в архитектурных решениях и повышении надежности сервисов.'])))
        vacancy_id = store.load_task_memory().active_vacancy_id
        assert vacancy_id is not None
        result = analyze.run(layout=layout, store=store, request=AnalyzeVacancyRequest(vacancy_id=vacancy_id))
        assert result.status == 'completed'
        analysis_path = layout.vacancy_dir(vacancy_id) / 'analysis.md'
        meta_path = layout.vacancy_dir(vacancy_id) / 'meta.yml'
        adoptions_path = layout.vacancy_dir(vacancy_id) / 'adoptions.md'
        analysis_text = analysis_path.read_text(encoding='utf-8')
        meta_text = meta_path.read_text(encoding='utf-8')
        adoptions_text = adoptions_path.read_text(encoding='utf-8')
        task_memory = json.loads(store.task_memory_path.read_text(encoding='utf-8'))
        workflow_runs = json.loads(store.workflow_runs_path.read_text(encoding='utf-8'))
        assert 'Выбранное резюме: HoD' in analysis_text
        assert '## Сводка' in analysis_text
        assert '## Матрица требований' in analysis_text
        assert 'status: analyzed' in meta_text
        assert 'selected_resume: HoD' in meta_text
        assert 'Кандидаты в постоянные сигналы' in adoptions_text
        assert 'Общие рекомендации по добавлению из MASTER в выбранную ролевую версию' in adoptions_text
        assert 'Обновление раздела `О себе (профиль)`' in adoptions_text
        assert 'Обновление раздела `Ключевые компетенции`' in adoptions_text
        assert 'Обновление раздела `Опыт работы`' in adoptions_text
        assert task_memory['active_workflow'] == 'analyze-vacancy'
        assert len(workflow_runs) == 2

    def test_analyze_reports_stale_vacancy_reference(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / '.tmp-tests'
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f'analyze-missing-vacancy-{uuid.uuid4().hex}'
        workspace_dir.mkdir(parents=True, exist_ok=True)
        layout = WorkspaceLayout(workspace_dir)
        layout.bootstrap()
        store = JsonMemoryStore(layout)
        store.bootstrap()
        analyze = build_default_registry().get('analyze-vacancy')
        with pytest.raises(FileNotFoundError, match='Runtime memory or the provided vacancy_id is stale'):
            analyze.run(layout=layout, store=store, request=AnalyzeVacancyRequest(vacancy_id='20260421-missing-role'))
