from __future__ import annotations
import pytest
import json
import sys
import uuid
from datetime import date
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from application_agent.integrations.response_monitoring import ResponseMonitoringIngestRecord, append_ingest_record
from application_agent.integrations.playwright_renderer import PlaywrightRenderedPage
from application_agent.memory.store import JsonMemoryStore
from application_agent.workspace import WorkspaceLayout
from application_agent.workflows.ingest_vacancy import IngestVacancyRequest, VacancySourceDetails, build_vacancy_id, build_response_monitoring_record, enrich_request, fetch_source_details, infer_source_channel, normalize_country_value, normalize_language_tag, parse_generic_vacancy_page, parse_hh_vacancy_page, parse_hh_vacancy_payload
from application_agent.workflows.vacancy_sources import should_use_playwright_fallback
from application_agent.workflows.registry import build_default_registry

def create_response_monitoring_workbook(path: Path) -> None:
    workbook_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">\n  <sheets>\n    <sheet name="Данные" sheetId="1" r:id="rId1"/>\n  </sheets>\n</workbook>\n'
    workbook_rels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>\n</Relationships>\n'
    worksheet_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">\n  <dimension ref="A1:P4"/>\n  <sheetData>\n    <row r="1">\n      <c r="A1" t="inlineStr"><is><t>Header</t></is></c>\n    </row>\n    <row r="2">\n      <c r="A2" t="inlineStr"><is><t>vacancy_id</t></is></c>\n    </row>\n    <row r="3">\n      <c r="A3" s="5"/>\n      <c r="B3" s="1"/>\n      <c r="C3" s="2"/>\n      <c r="D3" s="3"/>\n      <c r="E3" s="1"/>\n      <c r="F3" s="1"/>\n      <c r="G3" s="1"/>\n      <c r="H3" s="39"/>\n      <c r="I3" s="28"/>\n      <c r="J3" s="25"/>\n      <c r="K3" s="9"/>\n      <c r="L3" s="4"/>\n      <c r="M3" s="4"/>\n      <c r="N3" s="4"/>\n      <c r="O3" s="4"/>\n      <c r="P3" s="10"/>\n    </row>\n    <row r="4">\n      <c r="A4" s="6"/>\n      <c r="B4" s="6"/>\n      <c r="C4" s="7"/>\n      <c r="D4" s="8"/>\n      <c r="E4" s="7"/>\n      <c r="F4" s="7"/>\n      <c r="G4" s="7"/>\n      <c r="H4" s="11"/>\n      <c r="I4" s="29"/>\n      <c r="J4" s="26"/>\n      <c r="K4" s="12"/>\n      <c r="L4" s="13"/>\n      <c r="M4" s="13"/>\n      <c r="N4" s="13"/>\n      <c r="O4" s="13"/>\n      <c r="P4" s="14"/>\n    </row>\n  </sheetData>\n</worksheet>\n'
    content_types = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n  <Default Extension="xml" ContentType="application/xml"/>\n  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>\n  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>\n</Types>\n'
    root_rels = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>\n</Relationships>\n'
    with ZipFile(path, 'w', compression=ZIP_DEFLATED) as workbook:
        workbook.writestr('[Content_Types].xml', content_types)
        workbook.writestr('_rels/.rels', root_rels)
        workbook.writestr('xl/workbook.xml', workbook_xml)
        workbook.writestr('xl/_rels/workbook.xml.rels', workbook_rels)
        workbook.writestr('xl/worksheets/sheet1.xml', worksheet_xml)

class TestIngestWorkflow:

    def test_ingest_creates_vacancy_scaffold_and_memory(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / '.tmp-tests'
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f'ingest-workflow-{uuid.uuid4().hex}'
        workspace_dir.mkdir(parents=True, exist_ok=True)
        layout = WorkspaceLayout(workspace_dir)
        layout.bootstrap()
        store = JsonMemoryStore(layout)
        store.bootstrap()
        workflow = build_default_registry().get('ingest-vacancy')
        with patch('application_agent.workflows.ingest_vacancy.validate_response_monitoring_workbook', return_value=None), patch('application_agent.workflows.ingest_vacancy.append_ingest_record', return_value=3):
            result = workflow.run(layout=layout, store=store, request=IngestVacancyRequest(company='Citix', position='CIO', source_text='Platform strategy and team leadership.'))
        assert result.status == 'completed'
        assert len(result.artifacts) == 5
        task_memory = json.loads(store.task_memory_path.read_text(encoding='utf-8'))
        assert task_memory['active_workflow'] == 'ingest-vacancy'
        assert task_memory['active_vacancy_id'].startswith('20')

    def test_build_vacancy_id_transliterates_cyrillic(self) -> None:
        vacancy_id = build_vacancy_id(day=date(2026, 4, 20), company='Тестовая Компания', position='Руководитель разработки')
        assert vacancy_id == '20260420-testovaya-kompaniya-rukovoditel-razrabotki'

    def test_infer_source_channel(self) -> None:
        assert infer_source_channel('https://hh.ru/vacancy/132114761', '', '') == 'HeadHunter'
        assert infer_source_channel('https://career.habr.com/vacancies/1', '', '') == 'Habr Career'
        assert infer_source_channel('https://company.example/jobs/1', '', '') == 'Company Site'
        assert infer_source_channel('', 'manual text', '') == 'Manual'
        assert infer_source_channel('https://example.com/job', '', 'Custom') == 'Custom'

    def test_ingest_can_fill_rich_fields_from_source_url(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / '.tmp-tests'
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f'ingest-workflow-{uuid.uuid4().hex}'
        workspace_dir.mkdir(parents=True, exist_ok=True)
        layout = WorkspaceLayout(workspace_dir)
        layout.bootstrap()
        store = JsonMemoryStore(layout)
        store.bootstrap()
        workflow = build_default_registry().get('ingest-vacancy')
        with patch('application_agent.workflows.ingest_vacancy.fetch_source_details', return_value=VacancySourceDetails(company='Финтехробот', position='Head of Development / Руководитель разработки', source_text='Руководить разработкой.', source_markdown='## Зона ответственности\n\n- Руководить разработкой.', source_channel='HeadHunter', country='Россия', city='Москва', work_mode='удалённо', employment_type='Полная занятость', work_schedule='5/2', key_skills=['DevSecOps', 'CI/CD'])), patch('application_agent.workflows.ingest_vacancy.validate_response_monitoring_workbook', return_value=None), patch('application_agent.workflows.ingest_vacancy.append_ingest_record', return_value=42):
            result = workflow.run(layout=layout, store=store, request=IngestVacancyRequest(source_url='https://hh.ru/vacancy/132114761'))
        vacancy_id = store.load_task_memory().active_vacancy_id
        assert result.status == 'completed'
        assert vacancy_id is not None
        vacancy_dir = layout.vacancy_dir(vacancy_id)
        meta_text = (vacancy_dir / 'meta.yml').read_text(encoding='utf-8')
        source_text = (vacancy_dir / 'source.md').read_text(encoding='utf-8')
        assert 'source_channel: HeadHunter' in meta_text
        assert 'country: Россия' in meta_text
        assert 'work_mode: удалённо' in meta_text
        assert 'excel_row: 42' in meta_text
        assert '## Параметры вакансии' in source_text
        assert '- Город: Москва' in source_text
        assert '- DevSecOps' in source_text
        assert '### Зона ответственности' in source_text
        assert '\n## Ключевые навыки\n' not in source_text
        assert '\n### Ключевые навыки\n' in source_text

    def test_build_response_monitoring_record_maps_ingest_fields(self) -> None:
        record = build_response_monitoring_record(IngestVacancyRequest(company='Центр электронных финансов', position='Технический лидер', source_url='https://hh.ru/vacancy/132242694', source_channel='HeadHunter', country='Казахстан', work_mode='на месте работодателя', ingest_date=date(2026, 4, 21)), '20260421-tsentr-elektronnyh-finansov-tehnicheskiy-lider')
        assert record == ResponseMonitoringIngestRecord(vacancy_id='20260421-tsentr-elektronnyh-finansov-tehnicheskiy-lider', source_channel='HeadHunter', source_url='https://hh.ru/vacancy/132242694', company='Центр электронных финансов', position='Технический лидер', country='Казахстан', work_mode='на месте работодателя', ingest_date=date(2026, 4, 21))

    def test_ingest_requires_existing_response_monitoring_workbook(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / '.tmp-tests'
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f'ingest-workflow-missing-workbook-{uuid.uuid4().hex}'
        workspace_dir.mkdir(parents=True, exist_ok=True)
        layout = WorkspaceLayout(workspace_dir)
        layout.bootstrap()
        store = JsonMemoryStore(layout)
        store.bootstrap()
        workflow = build_default_registry().get('ingest-vacancy')
        request = IngestVacancyRequest(company='Citix', position='CIO', source_text='Platform strategy and team leadership.', ingest_date=date(2026, 4, 22))
        with pytest.raises(FileNotFoundError, match='response-monitoring.xlsx'):
            workflow.run(layout=layout, store=store, request=request)
        vacancy_id = build_vacancy_id(request.ingest_date, request.company, request.position)
        assert not layout.vacancy_dir(vacancy_id).exists()

    def test_ingest_requires_valid_response_monitoring_workbook(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / '.tmp-tests'
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f'ingest-workflow-invalid-workbook-{uuid.uuid4().hex}'
        workspace_dir.mkdir(parents=True, exist_ok=True)
        layout = WorkspaceLayout(workspace_dir)
        layout.bootstrap()
        store = JsonMemoryStore(layout)
        store.bootstrap()
        (workspace_dir / 'response-monitoring.xlsx').write_text('not a workbook', encoding='utf-8')
        workflow = build_default_registry().get('ingest-vacancy')
        request = IngestVacancyRequest(company='Citix', position='CIO', source_text='Platform strategy and team leadership.', ingest_date=date(2026, 4, 22))
        with pytest.raises(ValueError, match='valid .xlsx file'):
            workflow.run(layout=layout, store=store, request=request)
        vacancy_id = build_vacancy_id(request.ingest_date, request.company, request.position)
        assert not layout.vacancy_dir(vacancy_id).exists()

    def test_append_ingest_record_writes_columns_a_to_k(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / '.tmp-tests'
        temp_root.mkdir(exist_ok=True)
        workbook_path = temp_root / f'response-monitoring-{uuid.uuid4().hex}.xlsx'
        create_response_monitoring_workbook(workbook_path)
        row_index = append_ingest_record(workbook_path, ResponseMonitoringIngestRecord(vacancy_id='20260421-tsentr-elektronnyh-finansov-tehnicheskiy-lider', source_channel='HeadHunter', source_url='https://hh.ru/vacancy/132242694', company='Центр электронных финансов', position='Технический лидер', country='Казахстан', work_mode='на месте работодателя', ingest_date=date(2026, 4, 21)))
        assert row_index == 3
        with ZipFile(workbook_path) as workbook:
            sheet_xml = workbook.read('xl/worksheets/sheet1.xml')
            root = ET.fromstring(sheet_xml)
        ns = {'a': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        row = root.find(".//a:row[@r='3']", ns)
        assert row is not None
        sheet_text = sheet_xml.decode('utf-8')
        assert 'Ignorable="x14ac xr xr2 xr3"' not in sheet_text
        values: dict[str, str] = {}
        for cell in row.findall('a:c', ns):
            ref = cell.attrib['r']
            column = ''.join((char for char in ref if char.isalpha()))
            cell_type = cell.attrib.get('t')
            if cell_type == 'inlineStr':
                values[column] = ''.join((node.text or '' for node in cell.findall('.//a:t', ns)))
            else:
                value_node = cell.find('a:v', ns)
                values[column] = value_node.text if value_node is not None else ''
        assert values['A'] == '20260421-tsentr-elektronnyh-finansov-tehnicheskiy-lider'
        assert values['B'] == 'HeadHunter'
        assert values['C'] == 'https://hh.ru/vacancy/132242694'
        assert values['D'] == 'Да'
        assert values['E'] == 'Центр электронных финансов'
        assert values['F'] == 'Технический лидер'
        assert values['G'] == 'Казахстан'
        assert values['H'] == 'на месте работодателя'
        assert values['I'] == 'Сайт HH'
        assert values['J'] == 'Нет'
        assert values['K'] == '46133'

    def test_render_source_keeps_full_passport_and_params_with_no_data_fallback(self) -> None:
        workflow = build_default_registry().get('ingest-vacancy')
        source_text = workflow._render_source(IngestVacancyRequest(company='', position='', source_url='', source_channel='', country='', city='', employment_type='', work_schedule='', work_mode='Не указано', source_text='Example source'), '20260421-example-role')
        assert '## Паспорт' in source_text
        assert '- Компания: нет данных' in source_text
        assert '- Позиция: нет данных' in source_text
        assert '- ID вакансии: 20260421-example-role' in source_text
        assert '- Исходная ссылка: нет данных' in source_text
        assert '- Источник: Manual' in source_text
        assert '## Параметры вакансии' in source_text
        assert '- Страна: нет данных' in source_text
        assert '- Город: нет данных' in source_text
        assert '- Занятость: нет данных' in source_text
        assert '- График: нет данных' in source_text
        assert '- Формат работы: нет данных' in source_text

    def test_parse_hh_vacancy_payload_extracts_fields(self) -> None:
        payload = json.dumps({'name': 'Head of Development / Руководитель разработки', 'employer': {'name': 'Финтехробот'}, 'description': '<h2>Зона</h2><ul><li>Руководить</li></ul>', 'language': 'ru', 'employment': {'name': 'Полная занятость'}, 'schedule': {'name': 'Удалённая работа'}, 'area': {'name': 'Москва', 'country': 'Россия'}, 'key_skills': [{'name': 'DevSecOps'}, {'name': 'CI/CD'}]}, ensure_ascii=False)
        details = parse_hh_vacancy_payload(payload)
        assert details.company == 'Финтехробот'
        assert details.city == 'Москва'
        assert details.country == 'Россия'
        assert 'DevSecOps' in details.key_skills
        assert 'Ключевые навыки' in details.source_text
        assert '### Зона' in details.source_markdown
        assert details.source_markdown.count('### Ключевые навыки') == 1

    def test_parse_hh_vacancy_payload_prefers_text_over_area_country(self) -> None:
        payload = json.dumps({'name': 'Директор офиса цифровизации', 'employer': {'name': 'Белтаможсервис'}, 'description': '<p>Заработная плата от 5000 бел. руб.</p>', 'language': 'ru', 'area': {'name': 'Минск', 'country': 'Россия'}}, ensure_ascii=False)
        details = parse_hh_vacancy_payload(payload)
        assert details.city == 'Минск'
        assert details.country == 'Беларусь'

    def test_normalize_country_value_supports_full_iso_codes(self) -> None:
        assert normalize_country_value('KZ') == 'Казахстан'
        assert normalize_country_value('DEU') == 'Германия'
        assert normalize_country_value('PL') == 'Польша'
        assert normalize_country_value('Казахстан') == 'Казахстан'

    def test_normalize_language_tag_returns_primary_subtag(self) -> None:
        assert normalize_language_tag('en-US') == 'en'
        assert normalize_language_tag('ru_RU') == 'ru'
        assert normalize_language_tag('') == ''

    def test_parse_hh_vacancy_page_extracts_rich_fields(self) -> None:
        html = '\n        <html lang="ru">\n          <head>\n            <title>Вакансия Head of Development в Москве, работа в компании Финтехробот</title>\n            <meta property="og:title" content="Вакансия Head of Development в Москве, работа в компании Финтехробот" />\n            <meta name="description" content="Вакансия Head of Development. Зарплата: не указана. Москва. Требуемый опыт: 3–6 лет." />\n            <script id="js-script-global-vars">window.globalVars = { country: "1", area: "113" };</script>\n          </head>\n          <body>\n            <h1>Head of Development / Руководитель разработки</h1>\n            <div class="g-user-content" data-qa="vacancy-description">\n              <h2>Зона ответственности</h2>\n              <div><strong>Люди</strong></div>\n              <ul>\n                <li><div>Руководить командой</div></li>\n              </ul>\n            </div>\n            <div data-qa="common-employment-text">Полная занятость</div>\n            <p data-qa="work-schedule-by-days-text">График: 5/2</p>\n            <p data-qa="work-formats-text">Формат работы: удалённо</p>\n            <ul class="vacancy-skill-list">\n              <li data-qa="skills-element"><div class="magritte-tag__label">DevSecOps</div></li>\n              <li data-qa="skills-element"><div class="magritte-tag__label">CI/CD</div></li>\n            </ul>\n          </body>\n        </html>\n        '
        details = parse_hh_vacancy_page(html)
        assert details.source_channel == 'HeadHunter'
        assert details.country == 'Россия'
        assert details.city == 'Москва'
        assert details.work_mode == 'удалённо'
        assert details.work_schedule == '5/2'
        assert 'DevSecOps' in details.key_skills
        assert '- Руководить командой' in details.source_markdown
        assert '### Зона ответственности' in details.source_markdown
        assert details.source_markdown.count('### Ключевые навыки') == 1

    def test_parse_hh_vacancy_page_infers_belarus_from_minsk(self) -> None:
        html = '\n        <html lang="ru">\n          <head>\n            <title>Вакансия Директор офиса цифровизации в Минске, работа в компании Белтаможсервис</title>\n            <meta name="description" content="Вакансия Директор офиса цифровизации. Минск. Требуемый опыт: более 6 лет." />\n            <script id="js-script-global-vars">window.globalVars = { country: "1", area: "113" };</script>\n          </head>\n          <body>\n            <h1>Директор офиса цифровизации</h1>\n            <div class="g-user-content" data-qa="vacancy-description">\n              <p>Заработная плата от 5000 бел. руб.</p>\n            </div>\n            <div data-qa="common-employment-text">Полная занятость</div>\n          </body>\n        </html>\n        '
        details = parse_hh_vacancy_page(html)
        assert details.city == 'Минск'
        assert details.country == 'Беларусь'

    def test_parse_hh_vacancy_page_prefers_structured_country_over_hh_region(self) -> None:
        html = '\n        <html lang="ru">\n          <head>\n            <title>Вакансия Заместитель директора в Астане, работа в компании Центр электронных финансов</title>\n            <meta name="description" content="Вакансия Заместитель директора. Астана. Требуемый опыт: более 6 лет." />\n            <script id="js-script-global-vars">window.globalVars = { country: "1", area: "113" };</script>\n            <script type="application/ld+json">\n              {\n                "@context": "https://schema.org",\n                "@type": "JobPosting",\n                "title": "Заместитель директора",\n                "jobLocation": {\n                  "@type": "Place",\n                  "address": {\n                    "@type": "PostalAddress",\n                    "addressLocality": "Астана",\n                    "addressCountry": "KZ"\n                  }\n                },\n                "applicantLocationRequirements": {\n                  "@type": "Country",\n                  "name": "Казахстан"\n                }\n              }\n            </script>\n          </head>\n          <body>\n            <h1>Заместитель директора</h1>\n            <div class="g-user-content" data-qa="vacancy-description">\n              <p>Описание вакансии.</p>\n            </div>\n          </body>\n        </html>\n        '
        details = parse_hh_vacancy_page(html)
        assert details.city == 'Астана'
        assert details.country == 'Казахстан'

    def test_enrich_request_does_not_deepen_existing_markdown_headings(self) -> None:
        details = VacancySourceDetails(company='Белтаможсервис', position='Директор офиса цифровизации', source_text='Текст', source_markdown='### Ключевые навыки\n- Scrum', source_channel='HeadHunter', country='Беларусь', city='Минск', key_skills=['Scrum'])
        with patch('application_agent.workflows.ingest_vacancy.fetch_source_details', return_value=details):
            request = enrich_request(IngestVacancyRequest(source_url='https://hh.ru/vacancy/131945164', work_mode='Не указано', country='Не указано'))
        assert '### Ключевые навыки' in request.source_markdown
        assert '#### Ключевые навыки' not in request.source_markdown

    def test_parse_generic_vacancy_page_uses_structured_data(self) -> None:
        html = '\n        <html lang="ru">\n          <head>\n            <title>Вакансия Head of Development в компании Финтехробот</title>\n            <meta property="og:title" content="Вакансия Head of Development в компании Финтехробот" />\n            <script type="application/ld+json">\n              {\n                "@context": "https://schema.org",\n                "@type": "JobPosting",\n                "title": "Head of Development",\n                "description": "<p>Управлять командой разработки и delivery.</p>",\n                "hiringOrganization": {"@type": "Organization", "name": "Финтехробот"},\n                "jobLocation": {\n                  "@type": "Place",\n                  "address": {\n                    "@type": "PostalAddress",\n                    "addressLocality": "Астана",\n                    "addressCountry": "KZ"\n                  }\n                },\n                "applicantLocationRequirements": {\n                  "@type": "Country",\n                  "name": "Казахстан"\n                }\n              }\n            </script>\n          </head>\n          <body>\n            <h1>Head of Development</h1>\n          </body>\n        </html>\n        '
        details = parse_generic_vacancy_page(html, 'https://example.com/jobs/1')
        assert details.company == 'Финтехробот'
        assert details.position == 'Head of Development'
        assert details.source_channel == 'Company Site'
        assert details.city == 'Астана'
        assert details.country == 'Казахстан'
        assert 'Управлять командой разработки и delivery.' in details.source_text
        assert 'Управлять командой разработки' in details.source_markdown
        assert details.language == 'ru'

    def test_parse_generic_vacancy_page_prefers_body_over_truncated_meta_summary(self) -> None:
        html = '\n        <html lang="en">\n          <head>\n            <title>TaxDome - VP of Engineering</title>\n            <meta name="description" content="About TaxDome At TaxDome, we’re building the #1 platform across 40+ count..." />\n          </head>\n          <body>\n            <main>\n              <h2>VP of Engineering</h2>\n              <h3>About this role</h3>\n              <p>We\'re looking for a VP of Engineering to transform TaxDome into an AI-first engineering organization.</p>\n              <h3>What you\'ll be responsible for</h3>\n              <ul>\n                <li>Lead execution across the engineering organization.</li>\n              </ul>\n            </main>\n          </body>\n        </html>\n        '
        details = parse_generic_vacancy_page(html, 'https://careers.taxdome.com/v/189222-vp-of-engineering')
        assert details.language == 'en'
        assert "We're looking for a VP of Engineering" in details.source_text
        assert '### About this role' in details.source_markdown
        assert 'count...' not in details.source_text

    def test_parse_generic_vacancy_page_excludes_sidebar_and_footer_ui(self) -> None:
        html = '\n        <html lang="en">\n          <head>\n            <title>TaxDome - VP of Engineering</title>\n            <meta name="description" content="Short summary..." />\n          </head>\n          <body>\n            <div class="row">\n              <div class="col-lg-8 col-12">\n                <h2>VP of Engineering</h2>\n                <h3>About this role</h3>\n                <p>We\'re looking for a VP of Engineering to transform TaxDome into an AI-first engineering organization.</p>\n                <h3>What you\'ll be responsible for</h3>\n                <ul>\n                  <li>Lead execution across the engineering organization.</li>\n                </ul>\n              </div>\n              <div class="col-lg-4 col-12">\n                <a href="/apply">Apply now</a>\n                <button>Share</button>\n                <dl>\n                  <dt>Department</dt>\n                  <dd>Development</dd>\n                </dl>\n              </div>\n            </div>\n            <footer>\n              <div>Powered by PeopleForce</div>\n              <select>\n                <option>English</option>\n                <option>Polski</option>\n                <option>Deutsch</option>\n              </select>\n            </footer>\n          </body>\n        </html>\n        '
        details = parse_generic_vacancy_page(html, 'https://careers.taxdome.com/v/189222-vp-of-engineering')
        assert "We're looking for a VP of Engineering" in details.source_text
        assert 'Apply now' not in details.source_text
        assert 'Share' not in details.source_text
        assert 'Powered by PeopleForce' not in details.source_text
        assert 'Polski' not in details.source_text

    def test_parse_generic_vacancy_page_infers_company_from_branding_text(self) -> None:
        html = '\n        <html lang="en">\n          <head>\n            <title>Engineering Manager</title>\n            <meta name="description" content="We’re looking for curious, driven people to join Plata’s team." />\n          </head>\n          <body>\n            <main>\n              <p>We are Plata</p>\n              <h2>Engineering Manager</h2>\n              <p>Lead the engineering organization through the next stage of growth.</p>\n            </main>\n            <footer>\n              <a href="https://www.linkedin.com/company/bancoplata/">LinkedIn</a>\n            </footer>\n          </body>\n        </html>\n        '
        details = parse_generic_vacancy_page(html, 'https://careers.bancoplata.mx/vacancy/details?id=5107481008')
        assert details.company == 'Plata'
        assert details.position == 'Engineering Manager'
        assert details.language == 'en'

    def test_should_use_playwright_fallback_for_thin_generic_content(self) -> None:
        html = '\n        <html>\n          <head>\n            <script src="/static/app.js"></script>\n          </head>\n          <body>\n            <div id="root"></div>\n          </body>\n        </html>\n        '
        details = VacancySourceDetails(company='', position='Engineering Manager', source_text='Short summary')
        assert should_use_playwright_fallback(html, details)

    def test_fetch_source_details_uses_playwright_fallback_for_thin_generic_page(self) -> None:
        initial_html = '\n        <html>\n          <head>\n            <script src="/static/app.js"></script>\n          </head>\n          <body>\n            <div id="root"></div>\n          </body>\n        </html>\n        '
        initial_details = VacancySourceDetails(company='', position='Engineering Manager', source_text='Short summary', source_markdown='Short summary', source_channel='Website')
        rendered_details = VacancySourceDetails(company='Plata', position='Engineering Manager', source_text='Full rendered vacancy text with enough detail to trust the browser fallback.', source_markdown='### About role\n\nFull rendered vacancy text with enough detail to trust the browser fallback.', source_channel='Company Site', language='en')
        rendered_page = PlaywrightRenderedPage(html='<html><body><main><h1>Engineering Manager</h1><p>Full rendered vacancy text with enough detail to trust the browser fallback.</p></main></body></html>', url='https://careers.bancoplata.mx/vacancy/details?id=5107481008', title='Engineering Manager')
        with patch('application_agent.workflows.vacancy_sources.fetch_url', return_value=initial_html), patch('application_agent.workflows.vacancy_sources.parse_generic_vacancy_page', side_effect=[initial_details, rendered_details]), patch('application_agent.workflows.vacancy_sources.render_page_with_playwright', return_value=rendered_page):
            details = fetch_source_details('https://careers.bancoplata.mx/vacancy/details?id=5107481008')
        assert details.company == 'Plata'
        assert 'Full rendered vacancy text' in details.source_text

    def test_enrich_request_surfaces_fetch_error_when_required_fields_are_missing(self) -> None:
        with patch('application_agent.workflows.ingest_vacancy.fetch_source_details', side_effect=RuntimeError('connection refused')):
            with pytest.raises(ValueError, match='Failed to fetch vacancy details from source_url'):
                enrich_request(IngestVacancyRequest(source_url='https://careers.bancoplata.mx/vacancy/details?id=5107481008'))
