from __future__ import annotations
import pytest
import sys
import uuid
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from application_agent.export_resume_pdf import ExportResumePdfDependencyError, apply_export_resume_pdf_projection, generate_pdf_previews
from application_agent.workspace import WorkspaceLayout
PNG_BYTES = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc`\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'

class TestExportResumePdfHelpers:

    def test_helper_renders_pdf_report_and_is_idempotent(self) -> None:
        workspace_dir, layout = build_workspace('export-resume-pdf-idempotent')
        resume_path = layout.resumes_dir / 'CTO.md'
        pdf_output_path = layout.profile_dir / 'pdf' / 'CTO' / 'ru-EU.pdf'
        preview_dir = layout.runtime_memory_dir / 'export-resume-pdf' / 'CTO' / 'ru-EU'
        report_path = preview_dir / 'report.md'
        with patch('application_agent.export_resume_pdf.generate_pdf_previews', side_effect=fake_preview_renderer) as preview_mock:
            first = apply_export_resume_pdf_projection(target_resume='CTO', output_language='ru', contact_region='EU', template_id='default', resume_path=resume_path, profile_metadata_path=layout.profile_dir / 'contact-regions.yml', pdf_output_path=pdf_output_path, preview_dir=preview_dir, report_path=report_path)
            second = apply_export_resume_pdf_projection(target_resume='CTO', output_language='ru', contact_region='EU', template_id='default', resume_path=resume_path, profile_metadata_path=layout.profile_dir / 'contact-regions.yml', pdf_output_path=pdf_output_path, preview_dir=preview_dir, report_path=report_path)
        report = report_path.read_text(encoding='utf-8')
        assert preview_mock.call_count == 2
        assert first.changed
        assert not second.changed
        assert pdf_output_path.exists()
        assert pdf_output_path.stat().st_size > 0
        assert first.page_count == 1
        assert second.page_count == 1
        assert first.projection.surface.location == 'Bilbao, Spain'
        assert 'Телефон: +34 624 43 44 92' in first.projection.surface.contacts
        assert 'LinkedIn: https://linkedin.com/in/Avramko' in first.projection.surface.public_links
        assert first.preview_files[0].name == 'page-1.png'
        assert '- Target resume: CTO' in report
        assert '- Contact region: EU' in report
        assert '- Template: default' in report
        assert '- Preview pages: 1' in report

    def test_helper_rejects_invalid_inputs_before_rendering(self) -> None:
        workspace_dir, layout = build_workspace('export-resume-pdf-invalid')
        resume_path = layout.resumes_dir / 'MASTER.md'
        pdf_output_path = layout.profile_dir / 'pdf' / 'MASTER' / 'ru-RU.pdf'
        preview_dir = layout.runtime_memory_dir / 'export-resume-pdf' / 'MASTER' / 'ru-RU'
        report_path = preview_dir / 'report.md'
        with pytest.raises(ValueError, match="supports only 'ru'"):
            apply_export_resume_pdf_projection(target_resume='MASTER', output_language='en', contact_region='RU', template_id='default', resume_path=resume_path, profile_metadata_path=layout.profile_dir / 'contact-regions.yml', pdf_output_path=pdf_output_path, preview_dir=preview_dir, report_path=report_path)
        with pytest.raises(ValueError, match="supports only 'default'"):
            apply_export_resume_pdf_projection(target_resume='MASTER', output_language='ru', contact_region='RU', template_id='modern', resume_path=resume_path, profile_metadata_path=layout.profile_dir / 'contact-regions.yml', pdf_output_path=pdf_output_path, preview_dir=preview_dir, report_path=report_path)
        with pytest.raises(ValueError, match="Contact region 'US'"):
            apply_export_resume_pdf_projection(target_resume='MASTER', output_language='ru', contact_region='US', template_id='default', resume_path=resume_path, profile_metadata_path=layout.profile_dir / 'contact-regions.yml', pdf_output_path=pdf_output_path, preview_dir=preview_dir, report_path=report_path)

    def test_helper_raises_preview_dependency_error_without_partial_writes(self) -> None:
        workspace_dir, layout = build_workspace('export-resume-pdf-missing-poppler')
        resume_path = layout.resumes_dir / 'MASTER.md'
        pdf_output_path = layout.profile_dir / 'pdf' / 'MASTER' / 'ru-RU.pdf'
        preview_dir = layout.runtime_memory_dir / 'export-resume-pdf' / 'MASTER' / 'ru-RU'
        report_path = preview_dir / 'report.md'
        with patch('application_agent.export_resume_pdf.shutil.which', return_value=None):
            with pytest.raises(ExportResumePdfDependencyError, match='pdftoppm'):
                apply_export_resume_pdf_projection(target_resume='MASTER', output_language='ru', contact_region='RU', template_id='default', resume_path=resume_path, profile_metadata_path=layout.profile_dir / 'contact-regions.yml', pdf_output_path=pdf_output_path, preview_dir=preview_dir, report_path=report_path)
        assert not pdf_output_path.exists()
        assert not report_path.exists()
        assert not preview_dir.exists()

    def test_generate_pdf_previews_uses_pdftoppm_and_collects_sorted_pages(self) -> None:
        workspace_dir, layout = build_workspace('export-resume-pdf-previews')
        pdf_path = workspace_dir / 'dummy.pdf'
        pdf_path.write_bytes(b'%PDF-1.4\n% test\n')
        preview_dir = workspace_dir / 'preview'

        def fake_run(command: list[str], **_: object):
            assert command[0] == 'pdftoppm'
            assert '-png' in command
            preview_dir.mkdir(parents=True, exist_ok=True)
            (preview_dir / 'page-2.png').write_bytes(PNG_BYTES)
            (preview_dir / 'page-1.png').write_bytes(PNG_BYTES)

            class Result:
                returncode = 0
                stderr = ''
            return Result()
        with patch('application_agent.export_resume_pdf.shutil.which', return_value='pdftoppm'):
            with patch('application_agent.export_resume_pdf.subprocess.run', side_effect=fake_run):
                previews = generate_pdf_previews(pdf_path=pdf_path, preview_dir=preview_dir)
        assert [path.name for path in previews] == ['page-1.png', 'page-2.png']

def build_workspace(prefix: str) -> tuple[Path, WorkspaceLayout]:
    temp_root = Path(__file__).resolve().parents[1] / '.tmp-tests'
    temp_root.mkdir(exist_ok=True)
    workspace_dir = temp_root / f'{prefix}-{uuid.uuid4().hex}'
    workspace_dir.mkdir(parents=True, exist_ok=True)
    layout = WorkspaceLayout(workspace_dir)
    layout.bootstrap()
    write_profile_metadata(layout.profile_dir / 'contact-regions.yml')
    write_master_resume(layout.resumes_dir / 'MASTER.md')
    write_cto_resume(layout.resumes_dir / 'CTO.md')
    return (workspace_dir, layout)

def write_profile_metadata(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(['full_name:', '  ru: "Валентин Аврамко"', '  eu: "Valentin Avramko"', 'regions:', '  RU:', '    location: "Краснодар, Россия"', '    relocation: "Готов к переезду"', '    phone: "+7 (918) 990-10-09"', '    email: "avramko@mail.ru"', '    telegram: "@ValentinAvramko"', '    whatsapp: "+7 (918) 990-10-09"', '  EU:', '    location: "Bilbao, Spain"', '    relocation: "Open to relocation"', '    phone: "+34 624 43 44 92"', '    email: "valentin.avramko@gmail.com"', '    telegram: "@ValentinAvramko"', '    whatsapp: "+34 624 43 44 92"', 'links:', '  linkedin: "https://linkedin.com/in/Avramko"', '  github: "https://github.com/ValentinAvramko"', '']), encoding='utf-8', newline='\n')

def write_master_resume(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(['---', 'full_name:', '  ru: "Валентин Аврамко"', '  eu: "Valentin Avramko"', 'desired_roles: "Технический директор / CTO"', 'location:', '  ru: "Краснодар, Россия"', '  eu: "Bilbao, Spain"', 'contacts:', '  phone: "+7 (918) 990-10-09"', '  email: "avramko@mail.ru"', '  telegram: "@ValentinAvramko"', 'links:', '  linkedin: "https://linkedin.com/in/Avramko"', '---', '', '# {{ full_name }} - {{ desired_roles }}', '', '- **Контакты**', '  - **Телефон:** {{ contacts.phone }}', '  - **E-mail:** {{ contacts.email }}', '  - **Telegram:** {{ contacts.telegram }}', '  - **LinkedIn:** <{{ links.linkedin }}>', '', '- **Локация**', '  - **Город/страна:** {{ location }}', '  - **Готовность к переезду:** Готов к переезду', '', '## О себе', '', 'Руковожу архитектурой, delivery и инженерными командами в продуктовых и корпоративных системах.', '', '## Ключевые достижения', '', '- Снизил Lead Time и стабилизировал поставку изменений.', '- Построил управляемый процесс разработки и релизов.', '', '## Опыт работы', '', '### Free2Trip', '', '**CTO**', '', '- Отвечал за архитектуру и delivery цифровой платформы.', '', '## Рекомендации', '', 'Контакты могу предоставить по запросу.', '']), encoding='utf-8', newline='\n')

def write_cto_resume(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(['---', 'full_name:', '  ru: "Валентин Аврамко"', '  eu: "Valentin Avramko"', 'desired_roles: "Технический директор / CTO"', 'location:', '  ru: "Краснодар, Россия"', '  eu: "Bilbao, Spain"', 'contacts:', '  phone: "+7 (918) 990-10-09"', '  email: "avramko@mail.ru"', '  telegram: "@ValentinAvramko"', 'links:', '  linkedin: "https://linkedin.com/in/Avramko"', '---', '', '# {{ full_name }} - {{ desired_roles }}', '', '- **Контакты**', '  - **Телефон:** {{ contacts.phone }}', '  - **E-mail:** {{ contacts.email }}', '  - **Telegram:** {{ contacts.telegram }}', '  - **LinkedIn:** <{{ links.linkedin }}>', '', '- **Локация**', '  - **Город/страна:** {{ location }}', '  - **Готовность к переезду:** Готов к переезду', '', '## О себе', '', 'Технический директор с опытом управления инженерными командами, delivery и архитектурой корпоративных платформ.', '', '## Ключевые акценты', '', '- Platform engineering и delivery systems.', '- Executive stakeholder management.', '', '## Опыт работы', '', '### Free2Trip', '', '**CTO**', '', '- Руководил архитектурой и поставкой продукта.', '', '## Рекомендации', '', 'Контакты могу предоставить по запросу.', '']), encoding='utf-8', newline='\n')

def fake_preview_renderer(*, pdf_path: Path, preview_dir: Path, pdftoppm_path: str | None=None):
    preview_dir.mkdir(parents=True, exist_ok=True)
    page_path = preview_dir / 'page-1.png'
    page_path.write_bytes(PNG_BYTES)
    return (page_path,)
