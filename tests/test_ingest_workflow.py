from __future__ import annotations

import json
import sys
import unittest
import uuid
from datetime import date
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from application_agent.integrations.response_monitoring import ResponseMonitoringIngestRecord, append_ingest_record
from application_agent.memory.store import JsonMemoryStore
from application_agent.workspace import WorkspaceLayout
from application_agent.workflows.ingest_vacancy import (
    IngestVacancyRequest,
    VacancySourceDetails,
    build_vacancy_id,
    build_response_monitoring_record,
    enrich_request,
    infer_source_channel,
    normalize_country_value,
    normalize_language_tag,
    parse_generic_vacancy_page,
    parse_hh_vacancy_page,
    parse_hh_vacancy_payload,
)
from application_agent.workflows.registry import build_default_registry


def create_response_monitoring_workbook(path: Path) -> None:
    workbook_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Данные" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>
"""
    workbook_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>
"""
    worksheet_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="A1:P4"/>
  <sheetData>
    <row r="1">
      <c r="A1" t="inlineStr"><is><t>Header</t></is></c>
    </row>
    <row r="2">
      <c r="A2" t="inlineStr"><is><t>vacancy_id</t></is></c>
    </row>
    <row r="3">
      <c r="A3" s="5"/>
      <c r="B3" s="1"/>
      <c r="C3" s="2"/>
      <c r="D3" s="3"/>
      <c r="E3" s="1"/>
      <c r="F3" s="1"/>
      <c r="G3" s="1"/>
      <c r="H3" s="39"/>
      <c r="I3" s="28"/>
      <c r="J3" s="25"/>
      <c r="K3" s="9"/>
      <c r="L3" s="4"/>
      <c r="M3" s="4"/>
      <c r="N3" s="4"/>
      <c r="O3" s="4"/>
      <c r="P3" s="10"/>
    </row>
    <row r="4">
      <c r="A4" s="6"/>
      <c r="B4" s="6"/>
      <c r="C4" s="7"/>
      <c r="D4" s="8"/>
      <c r="E4" s="7"/>
      <c r="F4" s="7"/>
      <c r="G4" s="7"/>
      <c r="H4" s="11"/>
      <c r="I4" s="29"/>
      <c r="J4" s="26"/>
      <c r="K4" s="12"/>
      <c r="L4" s="13"/>
      <c r="M4" s="13"/>
      <c r="N4" s="13"/>
      <c r="O4" s="13"/>
      <c r="P4" s="14"/>
    </row>
  </sheetData>
</worksheet>
"""
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>
"""
    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>
"""
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as workbook:
        workbook.writestr("[Content_Types].xml", content_types)
        workbook.writestr("_rels/.rels", root_rels)
        workbook.writestr("xl/workbook.xml", workbook_xml)
        workbook.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        workbook.writestr("xl/worksheets/sheet1.xml", worksheet_xml)


class IngestWorkflowTests(unittest.TestCase):
    def test_ingest_creates_vacancy_scaffold_and_memory(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f"ingest-workflow-{uuid.uuid4().hex}"
        workspace_dir.mkdir(parents=True, exist_ok=True)

        layout = WorkspaceLayout(workspace_dir)
        layout.bootstrap()
        store = JsonMemoryStore(layout)
        store.bootstrap()
        workflow = build_default_registry().get("ingest-vacancy")

        with patch("application_agent.workflows.ingest_vacancy.append_ingest_record", return_value=3):
            result = workflow.run(
                layout=layout,
                store=store,
                request=IngestVacancyRequest(
                    company="Citix",
                    position="CIO",
                    source_text="Platform strategy and team leadership.",
                ),
            )

        self.assertEqual(result.status, "completed")
        self.assertEqual(len(result.artifacts), 5)

        task_memory = json.loads(store.task_memory_path.read_text(encoding="utf-8"))
        self.assertEqual(task_memory["active_workflow"], "ingest-vacancy")
        self.assertTrue(task_memory["active_vacancy_id"].startswith("20"))

    def test_build_vacancy_id_transliterates_cyrillic(self) -> None:
        vacancy_id = build_vacancy_id(
            day=date(2026, 4, 20),
            company="\u0422\u0435\u0441\u0442\u043e\u0432\u0430\u044f \u041a\u043e\u043c\u043f\u0430\u043d\u0438\u044f",
            position="\u0420\u0443\u043a\u043e\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u044c \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0438",
        )
        self.assertEqual(vacancy_id, "20260420-testovaya-kompaniya-rukovoditel-razrabotki")

    def test_infer_source_channel(self) -> None:
        self.assertEqual(infer_source_channel("https://hh.ru/vacancy/132114761", "", ""), "HeadHunter")
        self.assertEqual(infer_source_channel("https://career.habr.com/vacancies/1", "", ""), "Habr Career")
        self.assertEqual(infer_source_channel("https://company.example/jobs/1", "", ""), "Company Site")
        self.assertEqual(infer_source_channel("", "manual text", ""), "Manual")
        self.assertEqual(infer_source_channel("https://example.com/job", "", "Custom"), "Custom")

    def test_ingest_can_fill_rich_fields_from_source_url(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        workspace_dir = temp_root / f"ingest-workflow-{uuid.uuid4().hex}"
        workspace_dir.mkdir(parents=True, exist_ok=True)

        layout = WorkspaceLayout(workspace_dir)
        layout.bootstrap()
        store = JsonMemoryStore(layout)
        store.bootstrap()
        workflow = build_default_registry().get("ingest-vacancy")

        with patch(
            "application_agent.workflows.ingest_vacancy.fetch_source_details",
            return_value=VacancySourceDetails(
                company="\u0424\u0438\u043d\u0442\u0435\u0445\u0440\u043e\u0431\u043e\u0442",
                position="Head of Development / \u0420\u0443\u043a\u043e\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u044c \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0438",
                source_text="\u0420\u0443\u043a\u043e\u0432\u043e\u0434\u0438\u0442\u044c \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u043e\u0439.",
                source_markdown="## \u0417\u043e\u043d\u0430 \u043e\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0435\u043d\u043d\u043e\u0441\u0442\u0438\n\n- \u0420\u0443\u043a\u043e\u0432\u043e\u0434\u0438\u0442\u044c \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u043e\u0439.",
                source_channel="HeadHunter",
                country="\u0420\u043e\u0441\u0441\u0438\u044f",
                city="\u041c\u043e\u0441\u043a\u0432\u0430",
                work_mode="\u0443\u0434\u0430\u043b\u0451\u043d\u043d\u043e",
                employment_type="\u041f\u043e\u043b\u043d\u0430\u044f \u0437\u0430\u043d\u044f\u0442\u043e\u0441\u0442\u044c",
                work_schedule="5/2",
                key_skills=["DevSecOps", "CI/CD"],
            ),
        ), patch("application_agent.workflows.ingest_vacancy.append_ingest_record", return_value=42):
            result = workflow.run(
                layout=layout,
                store=store,
                request=IngestVacancyRequest(source_url="https://hh.ru/vacancy/132114761"),
            )

        vacancy_id = store.load_task_memory().active_vacancy_id
        self.assertEqual(result.status, "completed")
        self.assertIsNotNone(vacancy_id)

        vacancy_dir = layout.vacancy_dir(vacancy_id)
        meta_text = (vacancy_dir / "meta.yml").read_text(encoding="utf-8")
        source_text = (vacancy_dir / "source.md").read_text(encoding="utf-8")

        self.assertIn("source_channel: HeadHunter", meta_text)
        self.assertIn("country: \u0420\u043e\u0441\u0441\u0438\u044f", meta_text)
        self.assertIn("work_mode: \u0443\u0434\u0430\u043b\u0451\u043d\u043d\u043e", meta_text)
        self.assertIn("excel_row: 42", meta_text)
        self.assertIn("## \u041f\u0430\u0440\u0430\u043c\u0435\u0442\u0440\u044b \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u0438", source_text)
        self.assertIn("- \u0413\u043e\u0440\u043e\u0434: \u041c\u043e\u0441\u043a\u0432\u0430", source_text)
        self.assertIn("- DevSecOps", source_text)
        self.assertIn("### \u0417\u043e\u043d\u0430 \u043e\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0435\u043d\u043d\u043e\u0441\u0442\u0438", source_text)
        self.assertNotIn("\n## \u041a\u043b\u044e\u0447\u0435\u0432\u044b\u0435 \u043d\u0430\u0432\u044b\u043a\u0438\n", source_text)
        self.assertIn("\n### \u041a\u043b\u044e\u0447\u0435\u0432\u044b\u0435 \u043d\u0430\u0432\u044b\u043a\u0438\n", source_text)

    def test_build_response_monitoring_record_maps_ingest_fields(self) -> None:
        record = build_response_monitoring_record(
            IngestVacancyRequest(
                company="\u0426\u0435\u043d\u0442\u0440 \u044d\u043b\u0435\u043a\u0442\u0440\u043e\u043d\u043d\u044b\u0445 \u0444\u0438\u043d\u0430\u043d\u0441\u043e\u0432",
                position="\u0422\u0435\u0445\u043d\u0438\u0447\u0435\u0441\u043a\u0438\u0439 \u043b\u0438\u0434\u0435\u0440",
                source_url="https://hh.ru/vacancy/132242694",
                source_channel="HeadHunter",
                country="\u041a\u0430\u0437\u0430\u0445\u0441\u0442\u0430\u043d",
                work_mode="\u043d\u0430 \u043c\u0435\u0441\u0442\u0435 \u0440\u0430\u0431\u043e\u0442\u043e\u0434\u0430\u0442\u0435\u043b\u044f",
                ingest_date=date(2026, 4, 21),
            ),
            "20260421-tsentr-elektronnyh-finansov-tehnicheskiy-lider",
        )

        self.assertEqual(
            record,
            ResponseMonitoringIngestRecord(
                vacancy_id="20260421-tsentr-elektronnyh-finansov-tehnicheskiy-lider",
                source_channel="HeadHunter",
                source_url="https://hh.ru/vacancy/132242694",
                company="\u0426\u0435\u043d\u0442\u0440 \u044d\u043b\u0435\u043a\u0442\u0440\u043e\u043d\u043d\u044b\u0445 \u0444\u0438\u043d\u0430\u043d\u0441\u043e\u0432",
                position="\u0422\u0435\u0445\u043d\u0438\u0447\u0435\u0441\u043a\u0438\u0439 \u043b\u0438\u0434\u0435\u0440",
                country="\u041a\u0430\u0437\u0430\u0445\u0441\u0442\u0430\u043d",
                work_mode="\u043d\u0430 \u043c\u0435\u0441\u0442\u0435 \u0440\u0430\u0431\u043e\u0442\u043e\u0434\u0430\u0442\u0435\u043b\u044f",
                ingest_date=date(2026, 4, 21),
            ),
        )

    def test_append_ingest_record_writes_columns_a_to_k(self) -> None:
        temp_root = Path(__file__).resolve().parents[1] / ".tmp-tests"
        temp_root.mkdir(exist_ok=True)
        workbook_path = temp_root / f"response-monitoring-{uuid.uuid4().hex}.xlsx"
        create_response_monitoring_workbook(workbook_path)

        row_index = append_ingest_record(
            workbook_path,
            ResponseMonitoringIngestRecord(
                vacancy_id="20260421-tsentr-elektronnyh-finansov-tehnicheskiy-lider",
                source_channel="HeadHunter",
                source_url="https://hh.ru/vacancy/132242694",
                company="\u0426\u0435\u043d\u0442\u0440 \u044d\u043b\u0435\u043a\u0442\u0440\u043e\u043d\u043d\u044b\u0445 \u0444\u0438\u043d\u0430\u043d\u0441\u043e\u0432",
                position="\u0422\u0435\u0445\u043d\u0438\u0447\u0435\u0441\u043a\u0438\u0439 \u043b\u0438\u0434\u0435\u0440",
                country="\u041a\u0430\u0437\u0430\u0445\u0441\u0442\u0430\u043d",
                work_mode="\u043d\u0430 \u043c\u0435\u0441\u0442\u0435 \u0440\u0430\u0431\u043e\u0442\u043e\u0434\u0430\u0442\u0435\u043b\u044f",
                ingest_date=date(2026, 4, 21),
            ),
        )

        self.assertEqual(row_index, 3)

        with ZipFile(workbook_path) as workbook:
            sheet_xml = workbook.read("xl/worksheets/sheet1.xml")
            root = ET.fromstring(sheet_xml)
        ns = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
        row = root.find(".//a:row[@r='3']", ns)
        self.assertIsNotNone(row)
        sheet_text = sheet_xml.decode("utf-8")
        self.assertNotIn('Ignorable="x14ac xr xr2 xr3"', sheet_text)
        values: dict[str, str] = {}
        for cell in row.findall("a:c", ns):
            ref = cell.attrib["r"]
            column = "".join(char for char in ref if char.isalpha())
            cell_type = cell.attrib.get("t")
            if cell_type == "inlineStr":
                values[column] = "".join(node.text or "" for node in cell.findall(".//a:t", ns))
            else:
                value_node = cell.find("a:v", ns)
                values[column] = value_node.text if value_node is not None else ""

        self.assertEqual(values["A"], "20260421-tsentr-elektronnyh-finansov-tehnicheskiy-lider")
        self.assertEqual(values["B"], "HeadHunter")
        self.assertEqual(values["C"], "https://hh.ru/vacancy/132242694")
        self.assertEqual(values["D"], "\u0414\u0430")
        self.assertEqual(values["E"], "\u0426\u0435\u043d\u0442\u0440 \u044d\u043b\u0435\u043a\u0442\u0440\u043e\u043d\u043d\u044b\u0445 \u0444\u0438\u043d\u0430\u043d\u0441\u043e\u0432")
        self.assertEqual(values["F"], "\u0422\u0435\u0445\u043d\u0438\u0447\u0435\u0441\u043a\u0438\u0439 \u043b\u0438\u0434\u0435\u0440")
        self.assertEqual(values["G"], "\u041a\u0430\u0437\u0430\u0445\u0441\u0442\u0430\u043d")
        self.assertEqual(values["H"], "\u043d\u0430 \u043c\u0435\u0441\u0442\u0435 \u0440\u0430\u0431\u043e\u0442\u043e\u0434\u0430\u0442\u0435\u043b\u044f")
        self.assertEqual(values["I"], "\u0421\u0430\u0439\u0442 HH")
        self.assertEqual(values["J"], "\u041d\u0435\u0442")
        self.assertEqual(values["K"], "46133")

    def test_render_source_keeps_full_passport_and_params_with_no_data_fallback(self) -> None:
        workflow = build_default_registry().get("ingest-vacancy")

        source_text = workflow._render_source(
            IngestVacancyRequest(
                company="",
                position="",
                source_url="",
                source_channel="",
                country="",
                city="",
                employment_type="",
                work_schedule="",
                work_mode="\u041d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d\u043e",
                source_text="Example source",
            ),
            "20260421-example-role",
        )

        self.assertIn("## \u041f\u0430\u0441\u043f\u043e\u0440\u0442", source_text)
        self.assertIn("- \u041a\u043e\u043c\u043f\u0430\u043d\u0438\u044f: \u043d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445", source_text)
        self.assertIn("- \u041f\u043e\u0437\u0438\u0446\u0438\u044f: \u043d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445", source_text)
        self.assertIn("- ID \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u0438: 20260421-example-role", source_text)
        self.assertIn("- \u0418\u0441\u0445\u043e\u0434\u043d\u0430\u044f \u0441\u0441\u044b\u043b\u043a\u0430: \u043d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445", source_text)
        self.assertIn("- \u0418\u0441\u0442\u043e\u0447\u043d\u0438\u043a: Manual", source_text)
        self.assertIn("## \u041f\u0430\u0440\u0430\u043c\u0435\u0442\u0440\u044b \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u0438", source_text)
        self.assertIn("- \u0421\u0442\u0440\u0430\u043d\u0430: \u043d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445", source_text)
        self.assertIn("- \u0413\u043e\u0440\u043e\u0434: \u043d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445", source_text)
        self.assertIn("- \u0417\u0430\u043d\u044f\u0442\u043e\u0441\u0442\u044c: \u043d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445", source_text)
        self.assertIn("- \u0413\u0440\u0430\u0444\u0438\u043a: \u043d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445", source_text)
        self.assertIn("- \u0424\u043e\u0440\u043c\u0430\u0442 \u0440\u0430\u0431\u043e\u0442\u044b: \u043d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445", source_text)

    def test_parse_hh_vacancy_payload_extracts_fields(self) -> None:
        payload = json.dumps(
            {
                "name": "Head of Development / \u0420\u0443\u043a\u043e\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u044c \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0438",
                "employer": {"name": "\u0424\u0438\u043d\u0442\u0435\u0445\u0440\u043e\u0431\u043e\u0442"},
                "description": "<h2>\u0417\u043e\u043d\u0430</h2><ul><li>\u0420\u0443\u043a\u043e\u0432\u043e\u0434\u0438\u0442\u044c</li></ul>",
                "language": "ru",
                "employment": {"name": "\u041f\u043e\u043b\u043d\u0430\u044f \u0437\u0430\u043d\u044f\u0442\u043e\u0441\u0442\u044c"},
                "schedule": {"name": "\u0423\u0434\u0430\u043b\u0451\u043d\u043d\u0430\u044f \u0440\u0430\u0431\u043e\u0442\u0430"},
                "area": {"name": "\u041c\u043e\u0441\u043a\u0432\u0430", "country": "\u0420\u043e\u0441\u0441\u0438\u044f"},
                "key_skills": [{"name": "DevSecOps"}, {"name": "CI/CD"}],
            },
            ensure_ascii=False,
        )

        details = parse_hh_vacancy_payload(payload)

        self.assertEqual(details.company, "\u0424\u0438\u043d\u0442\u0435\u0445\u0440\u043e\u0431\u043e\u0442")
        self.assertEqual(details.city, "\u041c\u043e\u0441\u043a\u0432\u0430")
        self.assertEqual(details.country, "\u0420\u043e\u0441\u0441\u0438\u044f")
        self.assertIn("DevSecOps", details.key_skills)
        self.assertIn("\u041a\u043b\u044e\u0447\u0435\u0432\u044b\u0435 \u043d\u0430\u0432\u044b\u043a\u0438", details.source_text)
        self.assertIn("### \u0417\u043e\u043d\u0430", details.source_markdown)
        self.assertEqual(details.source_markdown.count("### \u041a\u043b\u044e\u0447\u0435\u0432\u044b\u0435 \u043d\u0430\u0432\u044b\u043a\u0438"), 1)

    def test_parse_hh_vacancy_payload_prefers_text_over_area_country(self) -> None:
        payload = json.dumps(
            {
                "name": "\u0414\u0438\u0440\u0435\u043a\u0442\u043e\u0440 \u043e\u0444\u0438\u0441\u0430 \u0446\u0438\u0444\u0440\u043e\u0432\u0438\u0437\u0430\u0446\u0438\u0438",
                "employer": {"name": "\u0411\u0435\u043b\u0442\u0430\u043c\u043e\u0436\u0441\u0435\u0440\u0432\u0438\u0441"},
                "description": "<p>\u0417\u0430\u0440\u0430\u0431\u043e\u0442\u043d\u0430\u044f \u043f\u043b\u0430\u0442\u0430 \u043e\u0442 5000 \u0431\u0435\u043b. \u0440\u0443\u0431.</p>",
                "language": "ru",
                "area": {"name": "\u041c\u0438\u043d\u0441\u043a", "country": "\u0420\u043e\u0441\u0441\u0438\u044f"},
            },
            ensure_ascii=False,
        )

        details = parse_hh_vacancy_payload(payload)

        self.assertEqual(details.city, "\u041c\u0438\u043d\u0441\u043a")
        self.assertEqual(details.country, "\u0411\u0435\u043b\u0430\u0440\u0443\u0441\u044c")

    def test_normalize_country_value_supports_full_iso_codes(self) -> None:
        self.assertEqual(normalize_country_value("KZ"), "Kazakhstan")
        self.assertEqual(normalize_country_value("DEU"), "Germany")
        self.assertEqual(normalize_country_value("PL"), "Poland")
        self.assertEqual(normalize_country_value("\u041a\u0430\u0437\u0430\u0445\u0441\u0442\u0430\u043d"), "\u041a\u0430\u0437\u0430\u0445\u0441\u0442\u0430\u043d")

    def test_normalize_language_tag_returns_primary_subtag(self) -> None:
        self.assertEqual(normalize_language_tag("en-US"), "en")
        self.assertEqual(normalize_language_tag("ru_RU"), "ru")
        self.assertEqual(normalize_language_tag(""), "")

    def test_parse_hh_vacancy_page_extracts_rich_fields(self) -> None:
        html = """
        <html lang="ru">
          <head>
            <title>\u0412\u0430\u043a\u0430\u043d\u0441\u0438\u044f Head of Development \u0432 \u041c\u043e\u0441\u043a\u0432\u0435, \u0440\u0430\u0431\u043e\u0442\u0430 \u0432 \u043a\u043e\u043c\u043f\u0430\u043d\u0438\u0438 \u0424\u0438\u043d\u0442\u0435\u0445\u0440\u043e\u0431\u043e\u0442</title>
            <meta property="og:title" content="\u0412\u0430\u043a\u0430\u043d\u0441\u0438\u044f Head of Development \u0432 \u041c\u043e\u0441\u043a\u0432\u0435, \u0440\u0430\u0431\u043e\u0442\u0430 \u0432 \u043a\u043e\u043c\u043f\u0430\u043d\u0438\u0438 \u0424\u0438\u043d\u0442\u0435\u0445\u0440\u043e\u0431\u043e\u0442" />
            <meta name="description" content="\u0412\u0430\u043a\u0430\u043d\u0441\u0438\u044f Head of Development. \u0417\u0430\u0440\u043f\u043b\u0430\u0442\u0430: \u043d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d\u0430. \u041c\u043e\u0441\u043a\u0432\u0430. \u0422\u0440\u0435\u0431\u0443\u0435\u043c\u044b\u0439 \u043e\u043f\u044b\u0442: 3\u20136 \u043b\u0435\u0442." />
            <script id="js-script-global-vars">window.globalVars = { country: "1", area: "113" };</script>
          </head>
          <body>
            <h1>Head of Development / \u0420\u0443\u043a\u043e\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u044c \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0438</h1>
            <div class="g-user-content" data-qa="vacancy-description">
              <h2>\u0417\u043e\u043d\u0430 \u043e\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0435\u043d\u043d\u043e\u0441\u0442\u0438</h2>
              <div><strong>\u041b\u044e\u0434\u0438</strong></div>
              <ul>
                <li><div>\u0420\u0443\u043a\u043e\u0432\u043e\u0434\u0438\u0442\u044c \u043a\u043e\u043c\u0430\u043d\u0434\u043e\u0439</div></li>
              </ul>
            </div>
            <div data-qa="common-employment-text">\u041f\u043e\u043b\u043d\u0430\u044f \u0437\u0430\u043d\u044f\u0442\u043e\u0441\u0442\u044c</div>
            <p data-qa="work-schedule-by-days-text">\u0413\u0440\u0430\u0444\u0438\u043a: 5/2</p>
            <p data-qa="work-formats-text">\u0424\u043e\u0440\u043c\u0430\u0442 \u0440\u0430\u0431\u043e\u0442\u044b: \u0443\u0434\u0430\u043b\u0451\u043d\u043d\u043e</p>
            <ul class="vacancy-skill-list">
              <li data-qa="skills-element"><div class="magritte-tag__label">DevSecOps</div></li>
              <li data-qa="skills-element"><div class="magritte-tag__label">CI/CD</div></li>
            </ul>
          </body>
        </html>
        """

        details = parse_hh_vacancy_page(html)

        self.assertEqual(details.source_channel, "HeadHunter")
        self.assertEqual(details.country, "\u0420\u043e\u0441\u0441\u0438\u044f")
        self.assertEqual(details.city, "\u041c\u043e\u0441\u043a\u0432\u0430")
        self.assertEqual(details.work_mode, "\u0443\u0434\u0430\u043b\u0451\u043d\u043d\u043e")
        self.assertEqual(details.work_schedule, "5/2")
        self.assertIn("DevSecOps", details.key_skills)
        self.assertIn("- \u0420\u0443\u043a\u043e\u0432\u043e\u0434\u0438\u0442\u044c \u043a\u043e\u043c\u0430\u043d\u0434\u043e\u0439", details.source_markdown)
        self.assertIn("### \u0417\u043e\u043d\u0430 \u043e\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0435\u043d\u043d\u043e\u0441\u0442\u0438", details.source_markdown)
        self.assertEqual(details.source_markdown.count("### \u041a\u043b\u044e\u0447\u0435\u0432\u044b\u0435 \u043d\u0430\u0432\u044b\u043a\u0438"), 1)

    def test_parse_hh_vacancy_page_infers_belarus_from_minsk(self) -> None:
        html = """
        <html lang="ru">
          <head>
            <title>\u0412\u0430\u043a\u0430\u043d\u0441\u0438\u044f \u0414\u0438\u0440\u0435\u043a\u0442\u043e\u0440 \u043e\u0444\u0438\u0441\u0430 \u0446\u0438\u0444\u0440\u043e\u0432\u0438\u0437\u0430\u0446\u0438\u0438 \u0432 \u041c\u0438\u043d\u0441\u043a\u0435, \u0440\u0430\u0431\u043e\u0442\u0430 \u0432 \u043a\u043e\u043c\u043f\u0430\u043d\u0438\u0438 \u0411\u0435\u043b\u0442\u0430\u043c\u043e\u0436\u0441\u0435\u0440\u0432\u0438\u0441</title>
            <meta name="description" content="\u0412\u0430\u043a\u0430\u043d\u0441\u0438\u044f \u0414\u0438\u0440\u0435\u043a\u0442\u043e\u0440 \u043e\u0444\u0438\u0441\u0430 \u0446\u0438\u0444\u0440\u043e\u0432\u0438\u0437\u0430\u0446\u0438\u0438. \u041c\u0438\u043d\u0441\u043a. \u0422\u0440\u0435\u0431\u0443\u0435\u043c\u044b\u0439 \u043e\u043f\u044b\u0442: \u0431\u043e\u043b\u0435\u0435 6 \u043b\u0435\u0442." />
            <script id="js-script-global-vars">window.globalVars = { country: "1", area: "113" };</script>
          </head>
          <body>
            <h1>\u0414\u0438\u0440\u0435\u043a\u0442\u043e\u0440 \u043e\u0444\u0438\u0441\u0430 \u0446\u0438\u0444\u0440\u043e\u0432\u0438\u0437\u0430\u0446\u0438\u0438</h1>
            <div class="g-user-content" data-qa="vacancy-description">
              <p>\u0417\u0430\u0440\u0430\u0431\u043e\u0442\u043d\u0430\u044f \u043f\u043b\u0430\u0442\u0430 \u043e\u0442 5000 \u0431\u0435\u043b. \u0440\u0443\u0431.</p>
            </div>
            <div data-qa="common-employment-text">\u041f\u043e\u043b\u043d\u0430\u044f \u0437\u0430\u043d\u044f\u0442\u043e\u0441\u0442\u044c</div>
          </body>
        </html>
        """

        details = parse_hh_vacancy_page(html)

        self.assertEqual(details.city, "\u041c\u0438\u043d\u0441\u043a")
        self.assertEqual(details.country, "\u0411\u0435\u043b\u0430\u0440\u0443\u0441\u044c")

    def test_parse_hh_vacancy_page_prefers_structured_country_over_hh_region(self) -> None:
        html = """
        <html lang="ru">
          <head>
            <title>\u0412\u0430\u043a\u0430\u043d\u0441\u0438\u044f \u0417\u0430\u043c\u0435\u0441\u0442\u0438\u0442\u0435\u043b\u044c \u0434\u0438\u0440\u0435\u043a\u0442\u043e\u0440\u0430 \u0432 \u0410\u0441\u0442\u0430\u043d\u0435, \u0440\u0430\u0431\u043e\u0442\u0430 \u0432 \u043a\u043e\u043c\u043f\u0430\u043d\u0438\u0438 \u0426\u0435\u043d\u0442\u0440 \u044d\u043b\u0435\u043a\u0442\u0440\u043e\u043d\u043d\u044b\u0445 \u0444\u0438\u043d\u0430\u043d\u0441\u043e\u0432</title>
            <meta name="description" content="\u0412\u0430\u043a\u0430\u043d\u0441\u0438\u044f \u0417\u0430\u043c\u0435\u0441\u0442\u0438\u0442\u0435\u043b\u044c \u0434\u0438\u0440\u0435\u043a\u0442\u043e\u0440\u0430. \u0410\u0441\u0442\u0430\u043d\u0430. \u0422\u0440\u0435\u0431\u0443\u0435\u043c\u044b\u0439 \u043e\u043f\u044b\u0442: \u0431\u043e\u043b\u0435\u0435 6 \u043b\u0435\u0442." />
            <script id="js-script-global-vars">window.globalVars = { country: "1", area: "113" };</script>
            <script type="application/ld+json">
              {
                "@context": "https://schema.org",
                "@type": "JobPosting",
                "title": "\u0417\u0430\u043c\u0435\u0441\u0442\u0438\u0442\u0435\u043b\u044c \u0434\u0438\u0440\u0435\u043a\u0442\u043e\u0440\u0430",
                "jobLocation": {
                  "@type": "Place",
                  "address": {
                    "@type": "PostalAddress",
                    "addressLocality": "\u0410\u0441\u0442\u0430\u043d\u0430",
                    "addressCountry": "KZ"
                  }
                },
                "applicantLocationRequirements": {
                  "@type": "Country",
                  "name": "\u041a\u0430\u0437\u0430\u0445\u0441\u0442\u0430\u043d"
                }
              }
            </script>
          </head>
          <body>
            <h1>\u0417\u0430\u043c\u0435\u0441\u0442\u0438\u0442\u0435\u043b\u044c \u0434\u0438\u0440\u0435\u043a\u0442\u043e\u0440\u0430</h1>
            <div class="g-user-content" data-qa="vacancy-description">
              <p>\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435 \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u0438.</p>
            </div>
          </body>
        </html>
        """

        details = parse_hh_vacancy_page(html)

        self.assertEqual(details.city, "\u0410\u0441\u0442\u0430\u043d\u0430")
        self.assertEqual(details.country, "\u041a\u0430\u0437\u0430\u0445\u0441\u0442\u0430\u043d")

    def test_enrich_request_does_not_deepen_existing_markdown_headings(self) -> None:
        details = VacancySourceDetails(
            company="\u0411\u0435\u043b\u0442\u0430\u043c\u043e\u0436\u0441\u0435\u0440\u0432\u0438\u0441",
            position="\u0414\u0438\u0440\u0435\u043a\u0442\u043e\u0440 \u043e\u0444\u0438\u0441\u0430 \u0446\u0438\u0444\u0440\u043e\u0432\u0438\u0437\u0430\u0446\u0438\u0438",
            source_text="\u0422\u0435\u043a\u0441\u0442",
            source_markdown="### \u041a\u043b\u044e\u0447\u0435\u0432\u044b\u0435 \u043d\u0430\u0432\u044b\u043a\u0438\n- Scrum",
            source_channel="HeadHunter",
            country="\u0411\u0435\u043b\u0430\u0440\u0443\u0441\u044c",
            city="\u041c\u0438\u043d\u0441\u043a",
            key_skills=["Scrum"],
        )

        with patch("application_agent.workflows.ingest_vacancy.fetch_source_details", return_value=details):
            request = enrich_request(
                IngestVacancyRequest(
                    source_url="https://hh.ru/vacancy/131945164",
                    work_mode="\u041d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d\u043e",
                    country="\u041d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d\u043e",
                )
            )

        self.assertIn("### \u041a\u043b\u044e\u0447\u0435\u0432\u044b\u0435 \u043d\u0430\u0432\u044b\u043a\u0438", request.source_markdown)
        self.assertNotIn("#### \u041a\u043b\u044e\u0447\u0435\u0432\u044b\u0435 \u043d\u0430\u0432\u044b\u043a\u0438", request.source_markdown)

    def test_parse_generic_vacancy_page_uses_structured_data(self) -> None:
        html = """
        <html lang="ru">
          <head>
            <title>\u0412\u0430\u043a\u0430\u043d\u0441\u0438\u044f Head of Development \u0432 \u043a\u043e\u043c\u043f\u0430\u043d\u0438\u0438 \u0424\u0438\u043d\u0442\u0435\u0445\u0440\u043e\u0431\u043e\u0442</title>
            <meta property="og:title" content="\u0412\u0430\u043a\u0430\u043d\u0441\u0438\u044f Head of Development \u0432 \u043a\u043e\u043c\u043f\u0430\u043d\u0438\u0438 \u0424\u0438\u043d\u0442\u0435\u0445\u0440\u043e\u0431\u043e\u0442" />
            <script type="application/ld+json">
              {
                "@context": "https://schema.org",
                "@type": "JobPosting",
                "title": "Head of Development",
                "description": "<p>\u0423\u043f\u0440\u0430\u0432\u043b\u044f\u0442\u044c \u043a\u043e\u043c\u0430\u043d\u0434\u043e\u0439 \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0438 \u0438 delivery.</p>",
                "hiringOrganization": {"@type": "Organization", "name": "\u0424\u0438\u043d\u0442\u0435\u0445\u0440\u043e\u0431\u043e\u0442"},
                "jobLocation": {
                  "@type": "Place",
                  "address": {
                    "@type": "PostalAddress",
                    "addressLocality": "\u0410\u0441\u0442\u0430\u043d\u0430",
                    "addressCountry": "KZ"
                  }
                },
                "applicantLocationRequirements": {
                  "@type": "Country",
                  "name": "\u041a\u0430\u0437\u0430\u0445\u0441\u0442\u0430\u043d"
                }
              }
            </script>
          </head>
          <body>
            <h1>Head of Development</h1>
          </body>
        </html>
        """

        details = parse_generic_vacancy_page(html, "https://example.com/jobs/1")

        self.assertEqual(details.company, "\u0424\u0438\u043d\u0442\u0435\u0445\u0440\u043e\u0431\u043e\u0442")
        self.assertEqual(details.position, "Head of Development")
        self.assertEqual(details.source_channel, "Company Site")
        self.assertEqual(details.city, "\u0410\u0441\u0442\u0430\u043d\u0430")
        self.assertEqual(details.country, "\u041a\u0430\u0437\u0430\u0445\u0441\u0442\u0430\u043d")
        self.assertIn("\u0423\u043f\u0440\u0430\u0432\u043b\u044f\u0442\u044c \u043a\u043e\u043c\u0430\u043d\u0434\u043e\u0439 \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0438 \u0438 delivery.", details.source_text)
        self.assertIn("\u0423\u043f\u0440\u0430\u0432\u043b\u044f\u0442\u044c \u043a\u043e\u043c\u0430\u043d\u0434\u043e\u0439 \u0440\u0430\u0437\u0440\u0430\u0431\u043e\u0442\u043a\u0438", details.source_markdown)
        self.assertEqual(details.language, "ru")

    def test_parse_generic_vacancy_page_prefers_body_over_truncated_meta_summary(self) -> None:
        html = """
        <html lang="en">
          <head>
            <title>TaxDome - VP of Engineering</title>
            <meta name="description" content="About TaxDome At TaxDome, we’re building the #1 platform across 40+ count..." />
          </head>
          <body>
            <main>
              <h2>VP of Engineering</h2>
              <h3>About this role</h3>
              <p>We're looking for a VP of Engineering to transform TaxDome into an AI-first engineering organization.</p>
              <h3>What you'll be responsible for</h3>
              <ul>
                <li>Lead execution across the engineering organization.</li>
              </ul>
            </main>
          </body>
        </html>
        """

        details = parse_generic_vacancy_page(html, "https://careers.taxdome.com/v/189222-vp-of-engineering")

        self.assertEqual(details.language, "en")
        self.assertIn("We're looking for a VP of Engineering", details.source_text)
        self.assertIn("### About this role", details.source_markdown)
        self.assertNotIn("count...", details.source_text)

    def test_parse_generic_vacancy_page_excludes_sidebar_and_footer_ui(self) -> None:
        html = """
        <html lang="en">
          <head>
            <title>TaxDome - VP of Engineering</title>
            <meta name="description" content="Short summary..." />
          </head>
          <body>
            <div class="row">
              <div class="col-lg-8 col-12">
                <h2>VP of Engineering</h2>
                <h3>About this role</h3>
                <p>We're looking for a VP of Engineering to transform TaxDome into an AI-first engineering organization.</p>
                <h3>What you'll be responsible for</h3>
                <ul>
                  <li>Lead execution across the engineering organization.</li>
                </ul>
              </div>
              <div class="col-lg-4 col-12">
                <a href="/apply">Apply now</a>
                <button>Share</button>
                <dl>
                  <dt>Department</dt>
                  <dd>Development</dd>
                </dl>
              </div>
            </div>
            <footer>
              <div>Powered by PeopleForce</div>
              <select>
                <option>English</option>
                <option>Polski</option>
                <option>Deutsch</option>
              </select>
            </footer>
          </body>
        </html>
        """

        details = parse_generic_vacancy_page(html, "https://careers.taxdome.com/v/189222-vp-of-engineering")

        self.assertIn("We're looking for a VP of Engineering", details.source_text)
        self.assertNotIn("Apply now", details.source_text)
        self.assertNotIn("Share", details.source_text)
        self.assertNotIn("Powered by PeopleForce", details.source_text)
        self.assertNotIn("Polski", details.source_text)

    def test_parse_generic_vacancy_page_infers_company_from_branding_text(self) -> None:
        html = """
        <html lang="en">
          <head>
            <title>Engineering Manager</title>
            <meta name="description" content="We’re looking for curious, driven people to join Plata’s team." />
          </head>
          <body>
            <main>
              <p>We are Plata</p>
              <h2>Engineering Manager</h2>
              <p>Lead the engineering organization through the next stage of growth.</p>
            </main>
            <footer>
              <a href="https://www.linkedin.com/company/bancoplata/">LinkedIn</a>
            </footer>
          </body>
        </html>
        """

        details = parse_generic_vacancy_page(html, "https://careers.bancoplata.mx/vacancy/details?id=5107481008")

        self.assertEqual(details.company, "Plata")
        self.assertEqual(details.position, "Engineering Manager")
        self.assertEqual(details.language, "en")

    def test_enrich_request_surfaces_fetch_error_when_required_fields_are_missing(self) -> None:
        with patch(
            "application_agent.workflows.ingest_vacancy.fetch_source_details",
            side_effect=RuntimeError("connection refused"),
        ):
            with self.assertRaisesRegex(ValueError, "Failed to fetch vacancy details from source_url"):
                enrich_request(IngestVacancyRequest(source_url="https://careers.bancoplata.mx/vacancy/details?id=5107481008"))


if __name__ == "__main__":
    unittest.main()
