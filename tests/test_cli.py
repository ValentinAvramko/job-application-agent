from __future__ import annotations
import io
import json
import sys
import uuid
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from application_agent.cli import main
from application_agent.workflows.base import WorkflowResult

class _FakeRegistry:

    def __init__(self, result: WorkflowResult) -> None:
        self._result = result
        self.requested: list[str] = []
        self.last_run_kwargs: dict[str, object] = {}

    def get(self, name: str):
        self.requested.append(name)

        registry = self

        class _FakeWorkflow:

            def __init__(self, result: WorkflowResult) -> None:
                self._result = result

            def run(self, **kwargs: object) -> WorkflowResult:
                registry.last_run_kwargs = kwargs
                return self._result
        return _FakeWorkflow(self._result)

class TestCli:

    def test_list_workflows_excludes_bootstrap_setup_command(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / '.tmp-tests'
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f'cli-list-{uuid.uuid4().hex}'
        workspace_dir.mkdir(parents=True, exist_ok=True)
        stdout = io.StringIO()
        with patch.object(sys, 'argv', ['run_agent.py', '--root', str(workspace_dir), 'list-workflows']), patch('sys.stdout', new=stdout):
            exit_code = main()
        assert exit_code == 0
        payload = json.loads(stdout.getvalue())
        assert [item['name'] for item in payload] == ['analyze-vacancy', 'build-linkedin', 'export-resume-pdf', 'ingest-vacancy', 'intake-adoptions', 'prepare-screening', 'rebuild-master', 'rebuild-role-resume']

    def test_ingest_cli_returns_workflow_result_without_git_publication_suffix(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / '.tmp-tests'
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f'cli-ingest-{uuid.uuid4().hex}'
        workspace_dir.mkdir(parents=True, exist_ok=True)
        result = WorkflowResult(workflow='ingest-vacancy', status='completed', summary='Создан каркас вакансии 20260421-example-role.', artifacts=[str(workspace_dir / 'vacancies' / '20260421-example-role' / 'meta.yml')])
        registry = _FakeRegistry(result)
        stdout = io.StringIO()
        with patch('application_agent.cli.build_default_registry', return_value=registry), patch.object(sys, 'argv', ['run_agent.py', '--root', str(workspace_dir), 'ingest-vacancy', '--company', 'Example', '--position', 'Role', '--source-text', 'Example vacancy text']), patch('sys.stdout', new=stdout):
            exit_code = main()
        assert exit_code == 0
        assert registry.requested == ['ingest-vacancy']
        payload = json.loads(stdout.getvalue())
        assert payload['summary'] == 'Создан каркас вакансии 20260421-example-role.'
        assert 'git commit' not in payload['summary']
        assert 'git push' not in payload['summary']

    def test_prepare_screening_cli_routes_to_prepare_workflow(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / '.tmp-tests'
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f'cli-prepare-{uuid.uuid4().hex}'
        workspace_dir.mkdir(parents=True, exist_ok=True)
        result = WorkflowResult(workflow='prepare-screening', status='completed', summary='Prepared screening package for vacancy 20260421-example-role.', artifacts=[str(workspace_dir / 'vacancies' / '20260421-example-role' / 'screening.md')])
        registry = _FakeRegistry(result)
        stdout = io.StringIO()
        with patch('application_agent.cli.build_default_registry', return_value=registry), patch.object(sys, 'argv', ['run_agent.py', '--root', str(workspace_dir), 'prepare-screening', '--vacancy-id', '20260421-example-role', '--selected-resume', 'CTO', '--output-language', 'ru', '--preparation-depth', 'deep']), patch('sys.stdout', new=stdout):
            exit_code = main()
        assert exit_code == 0
        assert registry.requested == ['prepare-screening']
        payload = json.loads(stdout.getvalue())
        assert payload['workflow'] == 'prepare-screening'
        assert 'screening' in payload['summary']

    def test_analyze_cli_passes_llm_options_and_manual_resume_override(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / '.tmp-tests'
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f'cli-analyze-{uuid.uuid4().hex}'
        workspace_dir.mkdir(parents=True, exist_ok=True)
        result = WorkflowResult(workflow='analyze-vacancy', status='completed', summary='Analyzed vacancy.', artifacts=[str(workspace_dir / 'vacancies' / 'v' / 'analysis.md')])
        registry = _FakeRegistry(result)
        stdout = io.StringIO()
        with patch('application_agent.cli.build_default_registry', return_value=registry), patch.object(sys, 'argv', ['job-application-agent.py', '--root', str(workspace_dir), 'analyze-vacancy', '--vacancy-id', '20260424-example', '--selected-resume', 'HoE', '--llm-provider', 'fake', '--llm-model', 'test-model', '--llm-temperature', '0.1', '--llm-reasoning-effort', 'low', '--llm-reasoning-summary', 'auto', '--llm-text-verbosity', 'low']), patch('sys.stdout', new=stdout):
            exit_code = main()
        request = registry.last_run_kwargs['request']
        assert exit_code == 0
        assert registry.requested == ['analyze-vacancy']
        assert request.selected_resume == 'HoE'
        assert request.llm_provider == 'fake'
        assert request.llm_model == 'test-model'
        assert request.llm_temperature == 0.1
        assert request.llm_reasoning_effort == 'low'
        assert request.llm_reasoning_summary == 'auto'
        assert request.llm_text_verbosity == 'low'

    def test_analyze_cli_uses_workspace_config_defaults(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / '.tmp-tests'
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f'cli-analyze-config-{uuid.uuid4().hex}'
        config_path = workspace_dir / 'agent_memory' / 'config' / 'application-agent.json'
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps(
                {
                    'analyze-vacancy': {
                        'selected_resume': 'HoD',
                        'llm_provider': 'fake',
                        'llm_model': 'configured-model',
                        'llm_reasoning_effort': 'medium',
                        'llm_reasoning_summary': 'auto',
                        'llm_text_verbosity': 'medium',
                        'include_employer_channels': True,
                    }
                }
            ),
            encoding='utf-8',
        )
        result = WorkflowResult(workflow='analyze-vacancy', status='completed', summary='Analyzed vacancy.', artifacts=[])
        registry = _FakeRegistry(result)
        stdout = io.StringIO()
        with patch('application_agent.cli.build_default_registry', return_value=registry), patch.object(sys, 'argv', ['run_agent.py', '--root', str(workspace_dir), 'analyze-vacancy', '--vacancy-id', '20260424-example']), patch('sys.stdout', new=stdout):
            exit_code = main()
        request = registry.last_run_kwargs['request']
        assert exit_code == 0
        assert request.selected_resume == 'HoD'
        assert request.llm_provider == 'fake'
        assert request.llm_model == 'configured-model'
        assert request.llm_temperature is None
        assert request.llm_reasoning_effort == 'medium'
        assert request.llm_reasoning_summary == 'auto'
        assert request.llm_text_verbosity == 'medium'
        assert request.include_employer_channels is True

    def test_analyze_cli_loads_openai_secrets_config(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / '.tmp-tests'
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f'cli-analyze-secrets-{uuid.uuid4().hex}'
        secrets_path = workspace_dir / 'agent_memory' / 'config' / 'secrets.json'
        secrets_path.parent.mkdir(parents=True, exist_ok=True)
        secrets_path.write_text(json.dumps({'OPENAI_API_KEY': 'secret-key', 'OPENAI_BASE_URL': 'https://example.test/v1'}), encoding='utf-8')
        result = WorkflowResult(workflow='analyze-vacancy', status='completed', summary='Analyzed vacancy.', artifacts=[])
        registry = _FakeRegistry(result)
        stdout = io.StringIO()
        with patch('application_agent.cli.build_default_registry', return_value=registry), patch.object(sys, 'argv', ['job-application-agent.py', '--root', str(workspace_dir), 'analyze-vacancy', '--vacancy-id', '20260424-example', '--llm-provider', 'fake']), patch('sys.stdout', new=stdout):
            exit_code = main()
        request = registry.last_run_kwargs['request']
        assert exit_code == 0
        assert request.llm_api_key == 'secret-key'
        assert request.llm_base_url == 'https://example.test/v1'

    def test_analyze_cli_explicit_options_override_workspace_config(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / '.tmp-tests'
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f'cli-analyze-config-override-{uuid.uuid4().hex}'
        config_path = workspace_dir / 'agent_memory' / 'config' / 'application-agent.json'
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps({'analyze-vacancy': {'llm_provider': 'openai', 'llm_model': 'configured-model', 'llm_temperature': 0.9}}),
            encoding='utf-8',
        )
        result = WorkflowResult(workflow='analyze-vacancy', status='completed', summary='Analyzed vacancy.', artifacts=[])
        registry = _FakeRegistry(result)
        stdout = io.StringIO()
        with patch('application_agent.cli.build_default_registry', return_value=registry), patch.object(sys, 'argv', ['run_agent.py', '--root', str(workspace_dir), 'analyze-vacancy', '--vacancy-id', '20260424-example', '--llm-provider', 'fake', '--llm-model', 'cli-model', '--llm-temperature', '0.1']), patch('sys.stdout', new=stdout):
            exit_code = main()
        request = registry.last_run_kwargs['request']
        assert exit_code == 0
        assert request.llm_provider == 'fake'
        assert request.llm_model == 'cli-model'
        assert request.llm_temperature == 0.1

    def test_cli_reports_invalid_json_config(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / '.tmp-tests'
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f'cli-invalid-config-{uuid.uuid4().hex}'
        config_path = workspace_dir / 'agent_memory' / 'config' / 'application-agent.json'
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text('{ invalid json', encoding='utf-8')
        with patch.object(sys, 'argv', ['run_agent.py', '--root', str(workspace_dir), 'analyze-vacancy', '--vacancy-id', '20260424-example']):
            try:
                main()
            except ValueError as exc:
                assert 'Invalid JSON config' in str(exc)
            else:
                raise AssertionError('Expected invalid JSON config to raise ValueError.')

    def test_intake_adoptions_cli_routes_to_intake_workflow(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / '.tmp-tests'
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f'cli-intake-{uuid.uuid4().hex}'
        workspace_dir.mkdir(parents=True, exist_ok=True)
        result = WorkflowResult(workflow='intake-adoptions', status='completed', summary='Prepared adoptions intake for vacancy 20260421-example-role.', artifacts=[str(workspace_dir / 'adoptions' / 'inbox' / '20260421-example-role.md')])
        registry = _FakeRegistry(result)
        stdout = io.StringIO()
        with patch('application_agent.cli.build_default_registry', return_value=registry), patch.object(sys, 'argv', ['run_agent.py', '--root', str(workspace_dir), 'intake-adoptions', '--vacancy-id', '20260421-example-role']), patch('sys.stdout', new=stdout):
            exit_code = main()
        assert exit_code == 0
        assert registry.requested == ['intake-adoptions']
        payload = json.loads(stdout.getvalue())
        assert payload['workflow'] == 'intake-adoptions'
        assert 'intake' in payload['summary']

    def test_rebuild_master_cli_routes_to_rebuild_workflow(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / '.tmp-tests'
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f'cli-rebuild-{uuid.uuid4().hex}'
        workspace_dir.mkdir(parents=True, exist_ok=True)
        result = WorkflowResult(workflow='rebuild-master', status='completed', summary='Rebuilt MASTER approved-signals section.', artifacts=[str(workspace_dir / 'resumes' / 'MASTER.md')])
        registry = _FakeRegistry(result)
        stdout = io.StringIO()
        with patch('application_agent.cli.build_default_registry', return_value=registry), patch.object(sys, 'argv', ['run_agent.py', '--root', str(workspace_dir), 'rebuild-master']), patch('sys.stdout', new=stdout):
            exit_code = main()
        assert exit_code == 0
        assert registry.requested == ['rebuild-master']
        payload = json.loads(stdout.getvalue())
        assert payload['workflow'] == 'rebuild-master'
        assert 'MASTER' in payload['summary']

    def test_rebuild_role_resume_cli_routes_to_rebuild_role_workflow(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / '.tmp-tests'
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f'cli-rebuild-role-{uuid.uuid4().hex}'
        workspace_dir.mkdir(parents=True, exist_ok=True)
        result = WorkflowResult(workflow='rebuild-role-resume', status='completed', summary='Rebuilt CTO role resume managed block.', artifacts=[str(workspace_dir / 'resumes' / 'CTO.md')])
        registry = _FakeRegistry(result)
        stdout = io.StringIO()
        with patch('application_agent.cli.build_default_registry', return_value=registry), patch.object(sys, 'argv', ['run_agent.py', '--root', str(workspace_dir), 'rebuild-role-resume', '--target-role', 'CTO']), patch('sys.stdout', new=stdout):
            exit_code = main()
        assert exit_code == 0
        assert registry.requested == ['rebuild-role-resume']
        payload = json.loads(stdout.getvalue())
        assert payload['workflow'] == 'rebuild-role-resume'
        assert 'CTO' in payload['summary']

    def test_build_linkedin_cli_routes_to_workflow(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / '.tmp-tests'
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f'cli-build-linkedin-{uuid.uuid4().hex}'
        workspace_dir.mkdir(parents=True, exist_ok=True)
        result = WorkflowResult(workflow='build-linkedin', status='completed', summary='Built LinkedIn draft pack for CTO.', artifacts=[str(workspace_dir / 'profile' / 'linkedin' / 'CTO.md')])
        registry = _FakeRegistry(result)
        stdout = io.StringIO()
        with patch('application_agent.cli.build_default_registry', return_value=registry), patch.object(sys, 'argv', ['run_agent.py', '--root', str(workspace_dir), 'build-linkedin', '--target-role', 'CTO']), patch('sys.stdout', new=stdout):
            exit_code = main()
        assert exit_code == 0
        assert registry.requested == ['build-linkedin']
        payload = json.loads(stdout.getvalue())
        assert payload['workflow'] == 'build-linkedin'
        assert 'LinkedIn' in payload['summary']

    def test_export_resume_pdf_cli_routes_to_workflow(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / '.tmp-tests'
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f'cli-export-resume-pdf-{uuid.uuid4().hex}'
        workspace_dir.mkdir(parents=True, exist_ok=True)
        result = WorkflowResult(workflow='export-resume-pdf', status='completed', summary='Exported resume PDF for CTO.', artifacts=[str(workspace_dir / 'profile' / 'pdf' / 'CTO' / 'ru-EU.pdf')])
        registry = _FakeRegistry(result)
        stdout = io.StringIO()
        with patch('application_agent.cli.build_default_registry', return_value=registry), patch.object(sys, 'argv', ['run_agent.py', '--root', str(workspace_dir), 'export-resume-pdf', '--target-resume', 'CTO', '--output-language', 'ru', '--contact-region', 'EU', '--template-id', 'default']), patch('sys.stdout', new=stdout):
            exit_code = main()
        assert exit_code == 0
        assert registry.requested == ['export-resume-pdf']
        payload = json.loads(stdout.getvalue())
        assert payload['workflow'] == 'export-resume-pdf'
        assert 'PDF' in payload['summary']
