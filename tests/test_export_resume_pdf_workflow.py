from __future__ import annotations
import pytest
import sys
import uuid
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from application_agent.memory.store import JsonMemoryStore
from application_agent.workflows.export_resume_pdf import ExportResumePdfRequest, ExportResumePdfWorkflow
from application_agent.workspace import WorkspaceLayout
PNG_BYTES = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc`\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'

class TestExportResumePdfWorkflow:

    def test_workflow_writes_pdf_and_runtime_verification_artifacts(self) -> None:
        workspace_dir, layout, store = build_workspace('export-resume-pdf-workflow')
        master_path = layout.resumes_dir / 'MASTER.md'
        role_resume_path = layout.resumes_dir / 'CTO.md'
        original_master = master_path.read_text(encoding='utf-8')
        original_role_resume = role_resume_path.read_text(encoding='utf-8')
        with patch('application_agent.export_resume_pdf.generate_pdf_previews', side_effect=fake_preview_renderer):
            result = ExportResumePdfWorkflow().run(layout=layout, store=store, request=ExportResumePdfRequest(target_resume='cto', output_language='', contact_region='', template_id=''))
        pdf_path = layout.profile_dir / 'pdf' / 'CTO' / 'ru-EU.pdf'
        preview_dir = layout.runtime_memory_dir / 'export-resume-pdf' / 'CTO' / 'ru-EU'
        report_path = preview_dir / 'report.md'
        preview_path = preview_dir / 'page-1.png'
        snapshot = store.snapshot()
        assert result.workflow == 'export-resume-pdf'
        assert result.status == 'completed'
        assert 'CTO' in result.summary
        assert pdf_path.exists()
        assert report_path.exists()
        assert preview_path.exists()
        assert 'ru/EU' in result.summary
        assert snapshot['task_memory']['active_artifacts'] == [str(pdf_path), str(report_path), str(preview_path)]
        assert snapshot['task_memory']['active_workflow'] == 'export-resume-pdf'
        assert snapshot['task_memory']['active_vacancy_id'] is None
        assert snapshot['workflow_runs'][-1]['workflow'] == 'export-resume-pdf'
        assert master_path.read_text(encoding='utf-8') == original_master
        assert role_resume_path.read_text(encoding='utf-8') == original_role_resume

    def test_workflow_rejects_unknown_resume(self) -> None:
        workspace_dir, layout, store = build_workspace('export-resume-pdf-invalid')
        with pytest.raises(ValueError, match='Unknown target_resume'):
            ExportResumePdfWorkflow().run(layout=layout, store=store, request=ExportResumePdfRequest(target_resume='VP'))

def build_workspace(prefix: str) -> tuple[Path, WorkspaceLayout, JsonMemoryStore]:
    temp_root = Path(__file__).resolve().parents[1] / '.tmp-tests'
    temp_root.mkdir(exist_ok=True)
    workspace_dir = temp_root / f'{prefix}-{uuid.uuid4().hex}'
    workspace_dir.mkdir(parents=True, exist_ok=True)
    layout = WorkspaceLayout(workspace_dir)
    layout.bootstrap()
    write_profile_metadata(layout.profile_dir / 'contact-regions.yml')
    write_master_resume(layout.resumes_dir / 'MASTER.md')
    write_cto_resume(layout.resumes_dir / 'CTO.md')
    store = JsonMemoryStore(layout)
    store.bootstrap()
    return (workspace_dir, layout, store)

def write_profile_metadata(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(['full_name:', '  ru: "Валентин Аврамко"', '  eu: "Valentin Avramko"', 'regions:', '  RU:', '    location: "Краснодар, Россия"', '    relocation: "Готов к переезду"', '    phone: "+7 (918) 990-10-09"', '    email: "avramko@mail.ru"', '    telegram: "@ValentinAvramko"', '    whatsapp: "+7 (918) 990-10-09"', '  EU:', '    location: "Bilbao, Spain"', '    relocation: "Open to relocation"', '    phone: "+34 624 43 44 92"', '    email: "valentin.avramko@gmail.com"', '    telegram: "@ValentinAvramko"', '    whatsapp: "+34 624 43 44 92"', 'links:', '  linkedin: "https://linkedin.com/in/Avramko"', '  github: "https://github.com/ValentinAvramko"', 'defaults:', '  contact_region_by_vacancy_country:', '    default: "EU"', '']), encoding='utf-8', newline='\n')

def write_master_resume(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(['---', 'full_name:', '  ru: "Валентин Аврамко"', '  eu: "Valentin Avramko"', 'desired_roles: "Технический директор / CTO"', 'location:', '  ru: "Краснодар, Россия"', '  eu: "Bilbao, Spain"', 'contacts:', '  phone: "+7 (918) 990-10-09"', '  email: "avramko@mail.ru"', '  telegram: "@ValentinAvramko"', 'links:', '  linkedin: "https://linkedin.com/in/Avramko"', '---', '', '# {{ full_name }} - {{ desired_roles }}', '', '- **Контакты**', '  - **Телефон:** {{ contacts.phone }}', '  - **E-mail:** {{ contacts.email }}', '  - **Telegram:** {{ contacts.telegram }}', '  - **LinkedIn:** <{{ links.linkedin }}>', '', '- **Локация**', '  - **Город/страна:** {{ location }}', '  - **Готовность к переезду:** Готов к переезду', '', '## О себе', '', 'Руковожу архитектурой, delivery и инженерными командами.', '', '## Опыт работы', '', '### Free2Trip', '', '**CTO**', '', '- Отвечал за архитектуру и delivery цифровой платформы.', '']), encoding='utf-8', newline='\n')

def write_cto_resume(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(['---', 'full_name:', '  ru: "Валентин Аврамко"', '  eu: "Valentin Avramko"', 'desired_roles: "Технический директор / CTO"', 'location:', '  ru: "Краснодар, Россия"', '  eu: "Bilbao, Spain"', 'contacts:', '  phone: "+7 (918) 990-10-09"', '  email: "avramko@mail.ru"', '  telegram: "@ValentinAvramko"', 'links:', '  linkedin: "https://linkedin.com/in/Avramko"', '---', '', '# {{ full_name }} - {{ desired_roles }}', '', '- **Контакты**', '  - **Телефон:** {{ contacts.phone }}', '  - **E-mail:** {{ contacts.email }}', '  - **Telegram:** {{ contacts.telegram }}', '  - **LinkedIn:** <{{ links.linkedin }}>', '', '- **Локация**', '  - **Город/страна:** {{ location }}', '  - **Готовность к переезду:** Готов к переезду', '', '## О себе', '', 'Технический директор с опытом управления инженерными командами и delivery.', '', '## Опыт работы', '', '### Free2Trip', '', '**CTO**', '', '- Руководил архитектурой и поставкой продукта.', '']), encoding='utf-8', newline='\n')

def fake_preview_renderer(*, pdf_path: Path, preview_dir: Path, pdftoppm_path: str | None=None):
    preview_dir.mkdir(parents=True, exist_ok=True)
    page_path = preview_dir / 'page-1.png'
    page_path.write_bytes(PNG_BYTES)
    return (page_path,)
