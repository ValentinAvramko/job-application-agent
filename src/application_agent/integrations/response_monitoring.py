from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

SPREADSHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
XR_NS = "http://schemas.microsoft.com/office/spreadsheetml/2014/revision"
RESPONSE_MONITORING_SHEET = "Данные"
RESPONSE_MONITORING_COLUMNS = tuple("ABCDEFGHIJK")
RESPONSE_MONITORING_METHOD_MAP = {
    "headhunter": "Сайт HH",
    "head hunter": "Сайт HH",
    "hh": "Сайт HH",
    "linkedin": "LinkedIn",
    "company site": "Сайт компании",
    "website": "Сайт компании",
    "email": "Email",
    "telegram": "Telegram",
    "whatsapp": "WhatsApp",
    "рекрутер": "Рекрутер",
    "кадровое агентство": "Кадровое агентство",
    "рекомендация": "Рекомендация",
    "manual": "Другое",
}

ET.register_namespace("", SPREADSHEET_NS)
ET.register_namespace("mc", MC_NS)
ET.register_namespace("r", REL_NS)
ET.register_namespace("xr", XR_NS)


@dataclass(frozen=True)
class ResponseMonitoringIngestRecord:
    vacancy_id: str
    source_channel: str
    source_url: str
    company: str
    position: str
    country: str
    work_mode: str
    ingest_date: date


def append_ingest_record(
    workbook_path: Path,
    record: ResponseMonitoringIngestRecord,
    *,
    row_index: int | None = None,
) -> int:
    with ZipFile(workbook_path) as workbook:
        workbook_xml = ET.fromstring(workbook.read("xl/workbook.xml"))
        relationships_xml = ET.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
        sheet_path = find_response_monitoring_sheet_path(workbook_xml, relationships_xml)
        sheet_xml = ET.fromstring(workbook.read(sheet_path))
        archive_entries = {name: workbook.read(name) for name in workbook.namelist()}

    rows = collect_sheet_rows(sheet_xml)
    target_row = find_target_row(rows, row_index)
    if target_row is None:
        target_row = append_empty_row(sheet_xml, rows)
        rows.append(target_row)

    resolved_row_index = int(target_row.attrib.get("r", "0") or 0)
    cells = ensure_row_has_cells(target_row)
    entry = build_ingest_entry(record)
    for column, value in entry.items():
        if isinstance(value, int):
            set_cell_number(cells[column], value)
        else:
            set_cell_text(cells[column], value)

    normalize_sheet_root(sheet_xml)
    archive_entries[sheet_path] = ET.tostring(sheet_xml, encoding="utf-8", xml_declaration=True)
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as target:
        for name, content in archive_entries.items():
            target.writestr(name, content)
    workbook_path.write_bytes(buffer.getvalue())
    return resolved_row_index


def build_ingest_entry(record: ResponseMonitoringIngestRecord) -> dict[str, str | int]:
    return {
        "A": record.vacancy_id,
        "B": record.source_channel.strip(),
        "C": record.source_url.strip(),
        "D": "Да",
        "E": record.company.strip(),
        "F": record.position.strip(),
        "G": display_value(record.country),
        "H": display_value(record.work_mode),
        "I": normalize_method(record.source_channel, record.source_url),
        "J": "Нет",
        "K": excel_date_serial(record.ingest_date),
    }


def excel_date_serial(value: date) -> int:
    epoch = date(1899, 12, 30)
    return (value - epoch).days


def display_value(value: str, default: str = "Не указано") -> str:
    cleaned = value.strip()
    return default if cleaned in {"", "Не указано", "n/a", "null"} else cleaned


def normalize_method(source_channel: str, source_url: str) -> str:
    channel = source_channel.strip().lower()
    if channel in RESPONSE_MONITORING_METHOD_MAP:
        return RESPONSE_MONITORING_METHOD_MAP[channel]

    host = source_url.strip().lower()
    if "hh.ru" in host:
        return "Сайт HH"
    if "linkedin.com" in host:
        return "LinkedIn"
    if any(token in host for token in ("career", "careers", "jobs")):
        return "Сайт компании"
    return "Другое"


def find_response_monitoring_sheet_path(workbook_xml: ET.Element, relationships_xml: ET.Element) -> str:
    relmap = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in relationships_xml
        if rel.attrib.get("Id") and rel.attrib.get("Target")
    }
    sheets = workbook_xml.find(f"{{{SPREADSHEET_NS}}}sheets")
    if sheets is None:
        raise ValueError("Workbook is missing sheets definition.")
    for sheet in sheets:
        if sheet.attrib.get("name") != RESPONSE_MONITORING_SHEET:
            continue
        relation_id = sheet.attrib.get(f"{{{REL_NS}}}id")
        if not relation_id or relation_id not in relmap:
            break
        target = relmap[relation_id].lstrip("/")
        return target if target.startswith("xl/") else f"xl/{target}"
    raise ValueError(f"Workbook does not contain sheet '{RESPONSE_MONITORING_SHEET}'.")


def collect_sheet_rows(sheet_xml: ET.Element) -> list[ET.Element]:
    sheet_data = sheet_xml.find(f"{{{SPREADSHEET_NS}}}sheetData")
    if sheet_data is None:
        raise ValueError("Worksheet is missing sheetData.")
    return sheet_data.findall(f"{{{SPREADSHEET_NS}}}row")


def find_target_row(rows: list[ET.Element], row_index: int | None) -> ET.Element | None:
    if row_index is not None:
        for row in rows:
            if int(row.attrib.get("r", "0") or 0) == row_index:
                return row
        return None
    for row in rows:
        current_index = int(row.attrib.get("r", "0") or 0)
        if current_index < 3:
            continue
        cells = row_cells_by_column(row)
        if all(not cell_value(cells[column]).strip() for column in RESPONSE_MONITORING_COLUMNS if column in cells):
            return row
    return None


def append_empty_row(sheet_xml: ET.Element, rows: list[ET.Element]) -> ET.Element:
    sheet_data = sheet_xml.find(f"{{{SPREADSHEET_NS}}}sheetData")
    if sheet_data is None:
        raise ValueError("Worksheet is missing sheetData.")
    row_index = int(rows[-1].attrib.get("r", "2") or 2) + 1 if rows else 3
    template_cells = row_cells_by_column(rows[-1]) if rows else {}
    row = ET.Element(f"{{{SPREADSHEET_NS}}}row", {"r": str(row_index)})
    for column in RESPONSE_MONITORING_COLUMNS:
        style_id = template_cells.get(column).attrib.get("s") if column in template_cells else None
        row.append(build_empty_cell(f"{column}{row_index}", style_id))
    sheet_data.append(row)
    update_dimension_ref(sheet_xml, row_index)
    return row


def cell_value(cell: ET.Element) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(f".//{{{SPREADSHEET_NS}}}t"))
    value_node = cell.find(f"{{{SPREADSHEET_NS}}}v")
    return value_node.text or "" if value_node is not None else ""


def row_cells_by_column(row: ET.Element) -> dict[str, ET.Element]:
    cells: dict[str, ET.Element] = {}
    for cell in row.findall(f"{{{SPREADSHEET_NS}}}c"):
        ref = cell.attrib.get("r", "")
        column = "".join(char for char in ref if char.isalpha())
        if column:
            cells[column] = cell
    return cells


def build_empty_cell(cell_ref: str, style_id: str | None = None) -> ET.Element:
    attributes = {"r": cell_ref}
    if style_id:
        attributes["s"] = style_id
    return ET.Element(f"{{{SPREADSHEET_NS}}}c", attributes)


def ensure_row_has_cells(row: ET.Element) -> dict[str, ET.Element]:
    cells = row_cells_by_column(row)
    row_index = int(row.attrib.get("r", "0") or 0)
    for column in RESPONSE_MONITORING_COLUMNS:
        if column in cells:
            continue
        cell = build_empty_cell(f"{column}{row_index}")
        row.append(cell)
        cells[column] = cell
    return cells


def set_cell_text(cell: ET.Element, value: str) -> None:
    for child in list(cell):
        cell.remove(child)
    cell.attrib["t"] = "inlineStr"
    is_node = ET.SubElement(cell, f"{{{SPREADSHEET_NS}}}is")
    text_node = ET.SubElement(is_node, f"{{{SPREADSHEET_NS}}}t")
    text_node.text = value


def set_cell_number(cell: ET.Element, value: int) -> None:
    for child in list(cell):
        cell.remove(child)
    cell.attrib.pop("t", None)
    value_node = ET.SubElement(cell, f"{{{SPREADSHEET_NS}}}v")
    value_node.text = str(value)


def update_dimension_ref(sheet_xml: ET.Element, row_index: int) -> None:
    dimension = sheet_xml.find(f"{{{SPREADSHEET_NS}}}dimension")
    if dimension is None:
        return
    ref = dimension.attrib.get("ref", "")
    if ":" not in ref:
        return
    start_ref, end_ref = ref.split(":", maxsplit=1)
    end_column = "".join(char for char in end_ref if char.isalpha()) or "P"
    dimension.attrib["ref"] = f"{start_ref}:{end_column}{row_index}"


def normalize_sheet_root(sheet_xml: ET.Element) -> None:
    ignorable_key = f"{{{MC_NS}}}Ignorable"
    uid_key = f"{{{XR_NS}}}uid"
    if uid_key in sheet_xml.attrib:
        sheet_xml.attrib[ignorable_key] = "xr"
    else:
        sheet_xml.attrib.pop(ignorable_key, None)
