from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

from application_agent.normalization.source_channels import normalize_response_method
from application_agent.utils.placeholders import display_or_unspecified

SPREADSHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
XR_NS = "http://schemas.microsoft.com/office/spreadsheetml/2014/revision"
RESPONSE_MONITORING_SHEET = "\u0414\u0430\u043d\u043d\u044b\u0435"
RESPONSE_MONITORING_COLUMNS = tuple("ABCDEFGHIJKLMNOPQ")

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
    updated_date: date | None = None


@dataclass(frozen=True)
class ResponseMonitoringActiveRow:
    row_index: int
    vacancy_id: str
    source_url: str
    updated_value: str
    updated_date: date | None = None


@dataclass(frozen=True)
class ResponseMonitoringRowUpdate:
    active_value: str | None = None
    updated_date: date | None = None


@dataclass(frozen=True)
class ResponseMonitoringWorkbookData:
    sheet_path: str
    sheet_xml: ET.Element
    archive_entries: dict[str, bytes]
    shared_strings: list[str]


def validate_response_monitoring_workbook(workbook_path: Path) -> None:
    if not workbook_path.exists():
        raise FileNotFoundError(
            f"Missing required workbook '{workbook_path}'. "
            "Current ingest-vacancy flow requires response-monitoring.xlsx before it can create vacancy artifacts."
        )

    try:
        with ZipFile(workbook_path) as workbook:
            workbook_xml = ET.fromstring(workbook.read("xl/workbook.xml"))
            relationships_xml = ET.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
            sheet_path = find_response_monitoring_sheet_path(workbook_xml, relationships_xml)
            sheet_xml = ET.fromstring(workbook.read(sheet_path))
        collect_sheet_rows(sheet_xml)
    except BadZipFile as exc:
        raise ValueError(
            f"Workbook '{workbook_path}' is not a valid .xlsx file. "
            "Restore a working response-monitoring.xlsx before running ingest-vacancy."
        ) from exc
    except KeyError as exc:
        raise ValueError(
            f"Workbook '{workbook_path}' is missing required Excel parts. "
            "Restore a valid response-monitoring.xlsx before running ingest-vacancy."
        ) from exc
    except ET.ParseError as exc:
        raise ValueError(
            f"Workbook '{workbook_path}' contains invalid XML. "
            "Restore a valid response-monitoring.xlsx before running ingest-vacancy."
        ) from exc
    except ValueError as exc:
        raise ValueError(
            f"Workbook '{workbook_path}' does not match the expected Response Monitoring format: {exc}"
        ) from exc


def append_ingest_record(
    workbook_path: Path,
    record: ResponseMonitoringIngestRecord,
    *,
    row_index: int | None = None,
) -> int:
    validate_response_monitoring_workbook(workbook_path)

    workbook_data = read_response_monitoring_workbook(workbook_path)
    rows = collect_sheet_rows(workbook_data.sheet_xml)
    target_row = find_target_row(rows, row_index)
    if target_row is None:
        target_row = append_empty_row(workbook_data.sheet_xml, rows)
        rows.append(target_row)

    resolved_row_index = int(target_row.attrib.get("r", "0") or 0)
    cells = ensure_row_has_cells(target_row)
    entry = build_ingest_entry(record)
    for column, value in entry.items():
        if isinstance(value, int):
            set_cell_number(cells[column], value)
        else:
            set_cell_text(cells[column], value)

    write_response_monitoring_workbook(workbook_path, workbook_data)
    return resolved_row_index


def build_ingest_entry(record: ResponseMonitoringIngestRecord) -> dict[str, str | int]:
    return {
        "A": record.vacancy_id,
        "B": record.source_channel.strip(),
        "C": record.source_url.strip(),
        "D": "\u0414\u0430",
        "E": excel_date_serial(record.updated_date) if record.updated_date else "",
        "F": record.company.strip(),
        "G": record.position.strip(),
        "H": display_or_unspecified(record.country),
        "I": display_or_unspecified(record.work_mode),
        "J": normalize_response_method(record.source_channel, record.source_url),
        "K": "\u0414\u0430",
        "L": excel_date_serial(record.ingest_date),
    }


def list_active_response_monitoring_rows(workbook_path: Path) -> list[ResponseMonitoringActiveRow]:
    validate_response_monitoring_workbook(workbook_path)
    workbook_data = read_response_monitoring_workbook(workbook_path)
    active_rows: list[ResponseMonitoringActiveRow] = []
    for row in collect_sheet_rows(workbook_data.sheet_xml):
        row_index = int(row.attrib.get("r", "0") or 0)
        if row_index < 3:
            continue
        cells = row_cells_by_column(row)
        active_value = cell_value(cells["D"], workbook_data.shared_strings) if "D" in cells else ""
        if active_value.strip().casefold() != "\u0434\u0430":
            continue
        active_rows.append(
            ResponseMonitoringActiveRow(
                row_index=row_index,
                vacancy_id=cell_value(cells["A"], workbook_data.shared_strings) if "A" in cells else "",
                source_url=cell_value(cells["C"], workbook_data.shared_strings) if "C" in cells else "",
                updated_value=cell_value(cells["E"], workbook_data.shared_strings) if "E" in cells else "",
                updated_date=parse_response_monitoring_date(
                    cell_value(cells["E"], workbook_data.shared_strings) if "E" in cells else ""
                ),
            )
        )
    return active_rows


def update_response_monitoring_updated_dates(workbook_path: Path, updates: dict[int, date]) -> int:
    if not updates:
        return 0
    return update_response_monitoring_rows(
        workbook_path,
        {row_index: ResponseMonitoringRowUpdate(updated_date=updated_date) for row_index, updated_date in updates.items()},
    )


def update_response_monitoring_rows(workbook_path: Path, updates: dict[int, ResponseMonitoringRowUpdate]) -> int:
    if not updates:
        return 0
    validate_response_monitoring_workbook(workbook_path)
    workbook_data = read_response_monitoring_workbook(workbook_path)
    updated_count = 0
    for row in collect_sheet_rows(workbook_data.sheet_xml):
        row_index = int(row.attrib.get("r", "0") or 0)
        if row_index not in updates:
            continue
        update = updates[row_index]
        cells = ensure_row_has_cells(row)
        changed = False
        if update.active_value is not None:
            set_cell_text(cells["D"], update.active_value)
            changed = True
        if update.updated_date is not None:
            set_cell_number(cells["E"], excel_date_serial(update.updated_date))
            changed = True
        if not changed:
            continue
        updated_count += 1
    write_response_monitoring_workbook(workbook_path, workbook_data)
    return updated_count


def read_response_monitoring_workbook(workbook_path: Path) -> ResponseMonitoringWorkbookData:
    with ZipFile(workbook_path) as workbook:
        workbook_xml = ET.fromstring(workbook.read("xl/workbook.xml"))
        relationships_xml = ET.fromstring(workbook.read("xl/_rels/workbook.xml.rels"))
        sheet_path = find_response_monitoring_sheet_path(workbook_xml, relationships_xml)
        sheet_xml = ET.fromstring(workbook.read(sheet_path))
        archive_entries = {name: workbook.read(name) for name in workbook.namelist()}
    return ResponseMonitoringWorkbookData(
        sheet_path=sheet_path,
        sheet_xml=sheet_xml,
        archive_entries=archive_entries,
        shared_strings=read_shared_strings(archive_entries),
    )


def write_response_monitoring_workbook(workbook_path: Path, workbook_data: ResponseMonitoringWorkbookData) -> None:
    normalize_sheet_root(workbook_data.sheet_xml)
    workbook_data.archive_entries[workbook_data.sheet_path] = ET.tostring(
        workbook_data.sheet_xml,
        encoding="utf-8",
        xml_declaration=True,
    )
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as target:
        for name, content in workbook_data.archive_entries.items():
            target.writestr(name, content)
    workbook_path.write_bytes(buffer.getvalue())


def read_shared_strings(archive_entries: dict[str, bytes]) -> list[str]:
    payload = archive_entries.get("xl/sharedStrings.xml")
    if not payload:
        return []
    shared_xml = ET.fromstring(payload)
    return [
        "".join(node.text or "" for node in item.findall(f".//{{{SPREADSHEET_NS}}}t"))
        for item in shared_xml.findall(f"{{{SPREADSHEET_NS}}}si")
    ]


def excel_date_serial(value: date) -> int:
    epoch = date(1899, 12, 30)
    return (value - epoch).days


def parse_response_monitoring_date(value: str) -> date | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    if cleaned.isdigit():
        epoch = date(1899, 12, 30)
        return date.fromordinal(epoch.toordinal() + int(cleaned))
    for date_format in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            if date_format == "%Y-%m-%d":
                return date.fromisoformat(cleaned)
            return datetime.strptime(cleaned, date_format).date()
        except ValueError:
            continue
    try:
        return date.fromisoformat(cleaned.split("T", maxsplit=1)[0])
    except ValueError:
        return None


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


def cell_value(cell: ET.Element, shared_strings: list[str] | None = None) -> str:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.findall(f".//{{{SPREADSHEET_NS}}}t"))
    value_node = cell.find(f"{{{SPREADSHEET_NS}}}v")
    if cell_type == "s" and value_node is not None and value_node.text is not None:
        shared_index = int(value_node.text)
        if shared_strings and 0 <= shared_index < len(shared_strings):
            return shared_strings[shared_index]
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
    end_column = "".join(char for char in end_ref if char.isalpha()) or RESPONSE_MONITORING_COLUMNS[-1]
    if column_number(end_column) < column_number(RESPONSE_MONITORING_COLUMNS[-1]):
        end_column = RESPONSE_MONITORING_COLUMNS[-1]
    dimension.attrib["ref"] = f"{start_ref}:{end_column}{row_index}"


def column_number(column: str) -> int:
    result = 0
    for char in column:
        result = result * 26 + ord(char.upper()) - ord("A") + 1
    return result


def normalize_sheet_root(sheet_xml: ET.Element) -> None:
    ignorable_key = f"{{{MC_NS}}}Ignorable"
    uid_key = f"{{{XR_NS}}}uid"
    if uid_key in sheet_xml.attrib:
        sheet_xml.attrib[ignorable_key] = "xr"
    else:
        sheet_xml.attrib.pop(ignorable_key, None)
