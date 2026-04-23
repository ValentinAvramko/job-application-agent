from __future__ import annotations
import sys
import uuid
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from application_agent.adoptions_review import AnsweredQuestionInput, ApplyReviewDecisionRequest, ApprovedSignalInput, ClosedQuestionInput, apply_review_decision, load_review_session_context
from application_agent.review_state import QuestionEntry, QuestionLedger
from application_agent.workspace import WorkspaceLayout

class TestAdoptionsReviewSession:

    def test_load_review_context_collects_inbox_questions_and_accepted_state(self) -> None:
        workspace_dir, layout = build_workspace('review-session-context')
        write_inbox(layout, vacancy_id='vacancy-1')
        QuestionLedger(entries=[QuestionEntry(topic='Need proof of team scale', related_to='vacancy-1', why_it_matters='Blocks permanent promotion.', suggested_question='Ask about number of teams and leads.')]).write(layout.adoptions_dir / 'questions' / 'open.md')
        context = load_review_session_context(layout=layout, vacancy_id='vacancy-1')
        assert context.vacancy_id == 'vacancy-1'
        assert context.company == 'Example'
        assert context.position == 'Head of Engineering'
        assert context.selected_resume == 'HoE'
        assert len(context.temp_rows) == 1
        assert len(context.perm_rows) == 1
        assert len(context.new_data_rows) == 1
        assert len(context.pending_questions) == 1
        assert context.pending_questions[0].topic == 'Need proof of team scale'
        assert context.accepted_signals == []

    def test_apply_review_decision_updates_accepted_signals_and_question_statuses(self) -> None:
        workspace_dir, layout = build_workspace('review-session-apply')
        write_inbox(layout, vacancy_id='vacancy-1')
        QuestionLedger(entries=[QuestionEntry(topic='Need proof of team scale', related_to='vacancy-1', why_it_matters='Blocks permanent promotion.', suggested_question='Ask about number of teams and leads.'), QuestionEntry(topic='Need confirmation about AI tooling', related_to='vacancy-1', why_it_matters='May still be vacancy-specific.', suggested_question='Ask whether AI tooling was used directly by the candidate.')]).write(layout.adoptions_dir / 'questions' / 'open.md')
        result = apply_review_decision(layout=layout, request=ApplyReviewDecisionRequest(vacancy_id='vacancy-1', approved_signals=[ApprovedSignalInput(signal='Leadership of 6 teams through engineering leads', rationale='Confirmed during review as durable leadership signal.', updated_at='2026-04-22T17:00:00+00:00')], answered_questions=[AnsweredQuestionInput(topic='Need proof of team scale', answer='Candidate confirmed leadership of 6 teams and 44 people through leads.')], closed_questions=[ClosedQuestionInput(topic='Need confirmation about AI tooling', resolution='Kept as vacancy-specific only; not promoted to permanent current-state.')]))
        context = load_review_session_context(layout=layout, vacancy_id='vacancy-1')
        accepted_text = (layout.adoptions_dir / 'accepted' / 'MASTER.md').read_text(encoding='utf-8')
        questions_text = (layout.adoptions_dir / 'questions' / 'open.md').read_text(encoding='utf-8')
        assert result.approved_signal_count == 1
        assert result.answered_question_count == 1
        assert result.closed_question_count == 1
        assert len(context.accepted_signals) == 1
        assert context.accepted_signals[0].source_vacancy == 'vacancy-1'
        assert len(context.pending_questions) == 0
        assert len(context.answered_questions) == 1
        assert len(context.closed_questions) == 1
        assert 'Leadership of 6 teams through engineering leads' in accepted_text
        assert 'Confirmed during review as durable leadership signal' in accepted_text
        assert '## Answered' in questions_text
        assert '## Closed' in questions_text
        assert 'Candidate confirmed leadership of 6 teams and 44 people through leads' in questions_text
        assert 'Kept as vacancy-specific only' in questions_text

def build_workspace(prefix: str) -> tuple[Path, WorkspaceLayout]:
    temp_root = Path(__file__).resolve().parents[1] / '.tmp-tests'
    temp_root.mkdir(exist_ok=True)
    workspace_dir = temp_root / f'{prefix}-{uuid.uuid4().hex}'
    workspace_dir.mkdir(parents=True, exist_ok=True)
    layout = WorkspaceLayout(workspace_dir)
    layout.bootstrap()
    return (workspace_dir, layout)

def write_inbox(layout: WorkspaceLayout, *, vacancy_id: str) -> None:
    inbox_path = layout.adoptions_dir / 'inbox' / f'{vacancy_id}.md'
    inbox_path.parent.mkdir(parents=True, exist_ok=True)
    inbox_path.write_text('\n'.join(['# Adoptions Inbox', '', '## Vacancy', '', f'- Vacancy ID: {vacancy_id}', '- Company: Example', '- Position: Head of Engineering', '- Selected Resume: HoE', '', '## TEMP', '', '| Suggestion | Target | Reason | Evidence | Status |', '| --- | --- | --- | --- | --- |', '| Reorder summary around delivery ownership | HoE.md | Vacancy-specific framing for this role. | vacancies/vacancy-1/adoptions.md -> TEMP | TEMP |', '', '## PERM', '', '| Suggestion | Target | Reason | Evidence | Status |', '| --- | --- | --- | --- | --- |', '| Leadership of 6 teams through engineering leads | MASTER.md | Candidate durable signal for later review into accepted/MASTER.md. | vacancies/vacancy-1/adoptions.md -> PERM | PERM |', '', '## NEW DATA NEEDED', '', '| Missing Data | Why It Matters | Suggested Question | Status |', '| --- | --- | --- | --- |', '| Need proof of team scale | Blocks confident review and permanent promotion. | Ask about number of teams and leads. | NEW DATA NEEDED |', '']), encoding='utf-8', newline='\n')
