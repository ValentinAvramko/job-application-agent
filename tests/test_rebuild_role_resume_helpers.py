from __future__ import annotations
import sys
import uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from application_agent.master_rebuild import apply_rebuild_master_projection
from application_agent.review_state import AcceptedSignal, AcceptedSignalsStore
from application_agent.role_resume_rebuild import MANAGED_SECTION_END, MANAGED_SECTION_START, apply_rebuild_role_resume_projection
from application_agent.workspace import WorkspaceLayout

class TestRebuildRoleResumeHelpers:

    def test_projection_syncs_master_signals_without_role_knowledge_and_is_idempotent(self) -> None:
        workspace_dir, layout = build_workspace('rebuild-role-idempotent')
        prepare_master_with_signals(layout, [AcceptedSignal(signal='Leadership of 6 teams through engineering leads', target='MASTER.md', source_vacancy='vacancy-1', rationale='Approved durable leadership signal.', updated_at='2026-04-22T19:10:00+00:00')])
        role_resume_path = layout.resumes_dir / 'CTO.md'
        report_path = layout.runtime_memory_dir / 'rebuild-role-resume' / 'CTO.md'
        original_intro = '# CTO Resume'
        first = apply_rebuild_role_resume_projection(target_role='CTO', master_path=layout.resumes_dir / 'MASTER.md', role_resume_path=role_resume_path, role_signal_path=layout.knowledge_dir / 'roles' / 'CTO.md', report_path=report_path)
        second = apply_rebuild_role_resume_projection(target_role='CTO', master_path=layout.resumes_dir / 'MASTER.md', role_resume_path=role_resume_path, role_signal_path=layout.knowledge_dir / 'roles' / 'CTO.md', report_path=report_path)
        role_resume_text = role_resume_path.read_text(encoding='utf-8')
        report_text = report_path.read_text(encoding='utf-8')
        assert first.changed
        assert not second.changed
        assert original_intro in role_resume_text
        assert MANAGED_SECTION_START in role_resume_text
        assert MANAGED_SECTION_END in role_resume_text
        assert 'Leadership of 6 teams through engineering leads' in role_resume_text
        assert '- Target Role: CTO' in report_text
        assert '- Role Signals Added: 0' in report_text
        assert role_resume_text.index(MANAGED_SECTION_START) < role_resume_text.index('## Рекомендации')

    def test_projection_reports_master_and_role_signal_diffs_and_preserves_unmanaged_text(self) -> None:
        workspace_dir, layout = build_workspace('rebuild-role-diff')
        prepare_master_with_signals(layout, [AcceptedSignal(signal='OpenAI and Codex as working AI tools', target='MASTER.md', source_vacancy='vacancy-1', rationale='Confirmed as reusable AI tooling signal.', updated_at='2026-04-22T19:20:00+00:00'), AcceptedSignal(signal='Leadership of 6 teams through engineering leads', target='MASTER.md', source_vacancy='vacancy-2', rationale='Approved durable leadership signal.', updated_at='2026-04-22T19:21:00+00:00')])
        role_signal_path = layout.knowledge_dir / 'roles' / 'HoE.md'
        role_signal_path.write_text('# HoE Signals\n\n- Platform engineering leadership\n', encoding='utf-8', newline='\n')
        role_resume_path = layout.resumes_dir / 'HoE.md'
        original_unmanaged_line = 'Existing role-specific narrative.'
        report_path = layout.runtime_memory_dir / 'rebuild-role-resume' / 'HoE.md'
        apply_rebuild_role_resume_projection(target_role='HoE', master_path=layout.resumes_dir / 'MASTER.md', role_resume_path=role_resume_path, role_signal_path=role_signal_path, report_path=report_path)
        prepare_master_with_signals(layout, [AcceptedSignal(signal='Leadership of 6 teams through engineering leads', target='MASTER.md', source_vacancy='vacancy-3', rationale='Refined after additional review.', updated_at='2026-04-22T19:30:00+00:00'), AcceptedSignal(signal='Built internal RAG prototype with pgvector', target='MASTER.md', source_vacancy='vacancy-4', rationale='Confirmed as reusable product AI signal.', updated_at='2026-04-22T19:31:00+00:00')])
        role_signal_path.write_text('# HoE Signals\n\n- Engineering excellence and delivery systems\n', encoding='utf-8', newline='\n')
        result = apply_rebuild_role_resume_projection(target_role='HoE', master_path=layout.resumes_dir / 'MASTER.md', role_resume_path=role_resume_path, role_signal_path=role_signal_path, report_path=report_path)
        role_resume_text = role_resume_path.read_text(encoding='utf-8')
        report_text = report_path.read_text(encoding='utf-8')
        assert result.changed
        assert original_unmanaged_line in role_resume_text
        assert 'Built internal RAG prototype with pgvector' in role_resume_text
        assert 'Engineering excellence and delivery systems' in role_resume_text
        assert 'OpenAI and Codex as working AI tools' not in role_resume_text
        assert 'Platform engineering leadership' not in role_resume_text
        assert '- Master Signals Added: 1' in report_text
        assert '- Master Signals Updated: 1' in report_text
        assert '- Master Signals Removed: 1' in report_text
        assert '- Role Signals Added: 1' in report_text
        assert '- Role Signals Removed: 1' in report_text

def build_workspace(prefix: str) -> tuple[Path, WorkspaceLayout]:
    temp_root = Path(__file__).resolve().parents[1] / '.tmp-tests'
    temp_root.mkdir(exist_ok=True)
    workspace_dir = temp_root / f'{prefix}-{uuid.uuid4().hex}'
    workspace_dir.mkdir(parents=True, exist_ok=True)
    layout = WorkspaceLayout(workspace_dir)
    layout.bootstrap()
    write_master_resume(layout.resumes_dir / 'MASTER.md')
    write_role_resume(layout.resumes_dir / 'CTO.md', 'CTO Resume')
    write_role_resume(layout.resumes_dir / 'HoE.md', 'HoE Resume')
    return (workspace_dir, layout)

def write_master_resume(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(['# Candidate', '', '## О себе', '', '- Existing profile summary.', '', '## Ключевые компетенции', '', '- Existing leadership signal.', '', '## Рекомендации', '', 'References available on request.', '']), encoding='utf-8', newline='\n')

def write_role_resume(path: Path, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join([f'# {title}', '', '## О себе', '', 'Existing role-specific narrative.', '', '## Рекомендации', '', 'References available on request.', '']), encoding='utf-8', newline='\n')

def prepare_master_with_signals(layout: WorkspaceLayout, signals: list[AcceptedSignal]) -> None:
    accepted_path = layout.adoptions_dir / 'accepted' / 'MASTER.md'
    report_path = layout.runtime_memory_dir / 'rebuild-master' / 'latest.md'
    store = AcceptedSignalsStore()
    for signal in signals:
        store.upsert(signal)
    store.write(accepted_path)
    apply_rebuild_master_projection(master_path=layout.resumes_dir / 'MASTER.md', accepted_path=accepted_path, report_path=report_path)
