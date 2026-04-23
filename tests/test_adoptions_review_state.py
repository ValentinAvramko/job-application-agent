from __future__ import annotations
import sys
import uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from application_agent.review_state import AcceptedSignal, AcceptedSignalsStore, QuestionEntry, QuestionLedger

class TestAdoptionsReviewState:

    def test_question_ledger_loads_legacy_pending_only_format(self) -> None:
        workspace_dir = build_workspace('review-state-legacy')
        ledger_path = workspace_dir / 'adoptions' / 'questions' / 'open.md'
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        ledger_path.write_text('\n'.join(['# Open Questions', '', '## Pending', '', '| Topic | Related To | Why It Matters | Suggested Question | Status |', '| --- | --- | --- | --- | --- |', '| Missing proof of scale | vacancy-1 | Blocks review | Ask about scale | pending |', '']), encoding='utf-8', newline='\n')
        ledger = QuestionLedger.load(ledger_path)
        assert len(ledger.records()) == 1
        assert ledger.records('pending')[0].topic == 'Missing proof of scale'
        assert ledger.records('answered') == []
        assert ledger.records('closed') == []

    def test_question_ledger_moves_entries_between_pending_answered_and_closed(self) -> None:
        workspace_dir = build_workspace('review-state-questions')
        ledger_path = workspace_dir / 'adoptions' / 'questions' / 'open.md'
        ledger = QuestionLedger()
        ledger.upsert(QuestionEntry(topic='Missing proof of scale', related_to='vacancy-1', why_it_matters='Blocks durable decision.', suggested_question='Ask about team scale.'))
        ledger.upsert(QuestionEntry(topic='Need confirmation about AI tooling', related_to='vacancy-1', why_it_matters='May affect permanent signal.', suggested_question='Ask whether OpenAI tooling was used directly.'))
        ledger.mark_answered(topic='Missing proof of scale', related_to='vacancy-1', answer='Candidate confirmed leadership of 6 teams and 44 people.')
        ledger.mark_closed(topic='Need confirmation about AI tooling', related_to='vacancy-1', resolution='Confirmed as vacancy-specific only; not promoted to permanent signals.')
        ledger.write(ledger_path)
        reloaded = QuestionLedger.load(ledger_path)
        markdown = ledger_path.read_text(encoding='utf-8')
        assert reloaded.records('pending') == []
        assert len(reloaded.records('answered')) == 1
        assert len(reloaded.records('closed')) == 1
        assert '## Answered' in markdown
        assert '## Closed' in markdown
        assert 'Candidate confirmed leadership of 6 teams and 44 people' in markdown
        assert 'Confirmed as vacancy-specific only' in markdown

    def test_accepted_signals_store_upserts_updates_and_removes_current_state_rows(self) -> None:
        workspace_dir = build_workspace('review-state-accepted')
        accepted_path = workspace_dir / 'adoptions' / 'accepted' / 'MASTER.md'
        store = AcceptedSignalsStore()
        store.upsert(AcceptedSignal(signal='Leadership of 6 teams through engineering leads', target='MASTER.md', source_vacancy='vacancy-1', rationale='Approved as durable scale signal.', updated_at='2026-04-22T16:40:00+00:00'))
        store.upsert(AcceptedSignal(signal='Leadership of 6 teams through engineering leads', target='MASTER.md', source_vacancy='vacancy-2', rationale='Refined wording after review; remains current-state.', updated_at='2026-04-22T16:50:00+00:00'))
        store.upsert(AcceptedSignal(signal='OpenAI and Codex as working AI tools', target='MASTER.md', source_vacancy='vacancy-3', rationale='Confirmed as reusable tooling signal.', updated_at='2026-04-22T16:55:00+00:00'))
        store.remove(signal='OpenAI and Codex as working AI tools', target='MASTER.md')
        store.write(accepted_path)
        reloaded = AcceptedSignalsStore.load(accepted_path)
        markdown = accepted_path.read_text(encoding='utf-8')
        assert len(reloaded.records()) == 1
        assert reloaded.records()[0].source_vacancy == 'vacancy-2'
        assert 'Refined wording after review' in markdown
        assert 'vacancy-1' not in markdown
        assert 'OpenAI and Codex as working AI tools' not in markdown

def build_workspace(prefix: str) -> Path:
    temp_root = Path(__file__).resolve().parents[1] / '.tmp-tests'
    temp_root.mkdir(exist_ok=True)
    workspace_dir = temp_root / f'{prefix}-{uuid.uuid4().hex}'
    workspace_dir.mkdir(parents=True, exist_ok=True)
    return workspace_dir
