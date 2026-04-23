from __future__ import annotations

from dataclasses import dataclass, field
from functools import partial
from io import BytesIO
from pathlib import Path
import hashlib
import html
import re
import shutil
import subprocess
import uuid

from application_agent.master_rebuild import ensure_trailing_newline, normalize_newlines
from application_agent.review_state import normalize_text

SUPPORTED_OUTPUT_LANGUAGES = ("ru",)
SUPPORTED_TEMPLATE_IDS = ("default",)
RENDERER_VERSION = "export-resume-pdf-v1"
PLACEHOLDER_RE = re.compile(r"{{\s*(?P<key>[\w.]+)\s*}}")
H1_RE = re.compile(r"^#\s+(?P<title>.+?)\s*$")
H2_RE = re.compile(r"^##\s+(?P<title>.+?)\s*$")
H3_RE = re.compile(r"^###\s+(?P<title>.+?)\s*$")
PNG_PAGE_RE = re.compile(r"page-(?P<page>\d+)\.png$")
INLINE_BOLD_LINE_RE = re.compile(r"^\*\*(.+?)\*\*$")
LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
RAW_URL_RE = re.compile(r"(?<![\">])(https?://[^\s<]+)")
EMAIL_RE = re.compile(r"(?<![\w@])([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,})(?![\w@])", re.IGNORECASE)
PHONE_RE = re.compile(r"\+[\d\s()\-]{7,}")


class ExportResumePdfDependencyError(RuntimeError):
    """Raised when a required rendering dependency is unavailable."""


@dataclass(frozen=True)
class ResumeSurface:
    full_name: str
    title: str
    location: str
    relocation: str
    contacts: tuple[str, ...]
    public_links: tuple[str, ...]


@dataclass(frozen=True)
class ResumeBlock:
    kind: str
    text: str = ""
    items: tuple[str, ...] = ()
    children: tuple["ResumeBlock", ...] = ()


@dataclass(frozen=True)
class ResumeSection:
    heading: str
    blocks: tuple[ResumeBlock, ...]


@dataclass(frozen=True)
class ResumePdfProjection:
    target_resume: str
    output_language: str
    contact_region: str
    template_id: str
    surface: ResumeSurface
    sections: tuple[ResumeSection, ...]


@dataclass(frozen=True)
class ExportResumePdfComputation:
    changed: bool
    projection: ResumePdfProjection
    pdf_path: Path
    report_path: Path
    preview_files: tuple[Path, ...]
    report_markdown: str
    page_count: int
    render_summary: tuple[str, ...] = field(default_factory=tuple)


def apply_export_resume_pdf_projection(
    *,
    target_resume: str,
    output_language: str,
    contact_region: str,
    template_id: str,
    resume_path: Path,
    profile_metadata_path: Path,
    pdf_output_path: Path,
    preview_dir: Path,
    report_path: Path,
) -> ExportResumePdfComputation:
    if not resume_path.exists():
        raise FileNotFoundError(f"Resume source is missing: {resume_path}")
    if not profile_metadata_path.exists():
        raise FileNotFoundError(f"Profile metadata is missing: {profile_metadata_path}")

    projection = compute_export_resume_pdf_projection(
        target_resume=target_resume,
        output_language=output_language,
        contact_region=contact_region,
        template_id=template_id,
        resume_text=resume_path.read_text(encoding="utf-8"),
        profile_metadata_text=profile_metadata_path.read_text(encoding="utf-8"),
    )

    staging_root = preview_dir.parent / f".tmp-export-resume-pdf-{uuid.uuid4().hex}"
    staging_root.parent.mkdir(parents=True, exist_ok=True)
    staging_root.mkdir(parents=True, exist_ok=True)
    try:
        temp_pdf_path = staging_root / "resume.pdf"
        temp_preview_dir = staging_root / "preview"
        temp_report_path = staging_root / "report.md"

        pdf_bytes = render_resume_pdf_bytes(projection)
        temp_pdf_path.write_bytes(pdf_bytes)
        preview_files = generate_pdf_previews(pdf_path=temp_pdf_path, preview_dir=temp_preview_dir)

        report_markdown = render_export_resume_pdf_report(
            projection=projection,
            pdf_path=pdf_output_path,
            report_path=report_path,
            preview_files=tuple(preview_dir / path.name for path in preview_files),
            page_count=len(preview_files),
        )
        temp_report_path.write_text(report_markdown, encoding="utf-8", newline="\n")

        changed = artifacts_changed(
            pdf_output_path=pdf_output_path,
            report_path=report_path,
            preview_dir=preview_dir,
            generated_pdf_bytes=pdf_bytes,
            generated_report=report_markdown,
            generated_preview_dir=temp_preview_dir,
        )

        if changed:
            persist_export_artifacts(
                pdf_output_path=pdf_output_path,
                report_path=report_path,
                preview_dir=preview_dir,
                generated_pdf_bytes=pdf_bytes,
                generated_report=report_markdown,
                generated_preview_dir=temp_preview_dir,
            )
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)

    final_preview_files = tuple(sorted(preview_dir.glob("page-*.png"), key=preview_sort_key))
    render_summary = build_render_summary(
        projection=projection,
        pdf_path=pdf_output_path,
        report_path=report_path,
        preview_files=final_preview_files,
        changed=changed,
    )
    return ExportResumePdfComputation(
        changed=changed,
        projection=projection,
        pdf_path=pdf_output_path,
        report_path=report_path,
        preview_files=final_preview_files,
        report_markdown=report_markdown,
        page_count=len(final_preview_files),
        render_summary=render_summary,
    )


def compute_export_resume_pdf_projection(
    *,
    target_resume: str,
    output_language: str,
    contact_region: str,
    template_id: str,
    resume_text: str,
    profile_metadata_text: str,
) -> ResumePdfProjection:
    normalized_target_resume = normalize_text(target_resume)
    normalized_output_language = normalize_text(output_language).lower()
    normalized_contact_region = normalize_text(contact_region).upper()
    normalized_template_id = normalize_text(template_id).lower()

    if not normalized_target_resume:
        raise ValueError("Target resume is required for export-resume-pdf.")
    if normalized_output_language not in SUPPORTED_OUTPUT_LANGUAGES:
        raise ValueError(
            f"Unsupported output language '{output_language}'. export-resume-pdf currently supports only 'ru'."
        )
    if normalized_template_id not in SUPPORTED_TEMPLATE_IDS:
        raise ValueError(
            f"Unsupported template_id '{template_id}'. export-resume-pdf currently supports only 'default'."
        )

    normalized_resume = normalize_newlines(resume_text)
    normalized_metadata = normalize_newlines(profile_metadata_text)
    resume_scalars = extract_front_matter_scalar_map(normalized_resume)
    profile_scalars = load_nested_scalar_map(normalized_metadata)

    region_scalars = extract_region_scalars(profile_scalars, normalized_contact_region)
    if not region_scalars:
        raise ValueError(
            f"Contact region '{normalized_contact_region}' is not defined in profile/contact-regions.yml."
        )

    placeholder_values = dict(resume_scalars)
    placeholder_values.update(resolve_placeholder_surface_values(resume_scalars, profile_scalars, normalized_contact_region))

    resume_body = substitute_placeholders(strip_front_matter(normalized_resume), placeholder_values)
    resume_title, body_without_title = split_title_and_body(resume_body)
    title = normalize_display_text(resume_title) or normalized_target_resume
    content_body = strip_surface_block(body_without_title)
    sections = parse_resume_sections(content_body)

    surface = ResumeSurface(
        full_name=resolve_full_name(resume_scalars, profile_scalars, normalized_contact_region),
        title=title,
        location=resolve_region_value(
            region_scalars=region_scalars,
            resume_scalars=resume_scalars,
            region=normalized_contact_region,
            key="location",
            fallback="Уточнить публичную локацию.",
        ),
        relocation=resolve_region_value(
            region_scalars=region_scalars,
            resume_scalars=resume_scalars,
            region=normalized_contact_region,
            key="relocation",
            fallback="Уточнить готовность к переезду.",
        ),
        contacts=build_contact_lines(region_scalars=region_scalars, resume_scalars=resume_scalars, region=normalized_contact_region),
        public_links=build_public_link_lines(profile_scalars=profile_scalars, resume_scalars=resume_scalars),
    )

    return ResumePdfProjection(
        target_resume=normalized_target_resume,
        output_language=normalized_output_language,
        contact_region=normalized_contact_region,
        template_id=normalized_template_id,
        surface=surface,
        sections=sections,
    )


def render_resume_pdf_bytes(projection: ResumePdfProjection) -> bytes:
    (
        canvas_module,
        colors,
        TA_CENTER,
        A4,
        ParagraphStyle,
        getSampleStyleSheet,
        mm,
        ListFlowable,
        ListItem,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
    ) = require_reportlab()

    styles = build_pdf_styles(
        colors=colors,
        ParagraphStyle=ParagraphStyle,
        getSampleStyleSheet=getSampleStyleSheet,
        TA_CENTER=TA_CENTER,
    )
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=11.5 * mm,
        rightMargin=11.5 * mm,
        topMargin=11.5 * mm,
        bottomMargin=14 * mm,
        title=projection.surface.title,
        author="application-agent",
    )
    story = build_pdf_story(
        projection=projection,
        styles=styles,
        Paragraph=Paragraph,
        Spacer=Spacer,
        ListFlowable=ListFlowable,
        ListItem=ListItem,
    )
    footer = partial(draw_footer, colors=colors, title=projection.surface.title, page_size=A4, mm=mm)
    doc.build(story, onFirstPage=footer, onLaterPages=footer, canvasmaker=partial(canvas_module.Canvas, invariant=1))
    return buffer.getvalue()


def generate_pdf_previews(pdf_path: Path, preview_dir: Path, pdftoppm_path: str | None = None) -> tuple[Path, ...]:
    if not pdf_path.exists():
        raise FileNotFoundError(f"Generated PDF is missing: {pdf_path}")

    resolved_pdftoppm = pdftoppm_path or shutil.which("pdftoppm")
    if not resolved_pdftoppm:
        raise ExportResumePdfDependencyError(
            "pdftoppm (Poppler) is required for export-resume-pdf preview generation."
        )

    preview_dir.mkdir(parents=True, exist_ok=True)
    prefix = preview_dir / "page"
    result = subprocess.run(
        [resolved_pdftoppm, "-png", str(pdf_path), str(prefix)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = normalize_text(result.stderr) or "no stderr"
        raise ExportResumePdfDependencyError(f"pdftoppm preview rendering failed: {stderr}")

    preview_files = tuple(sorted(preview_dir.glob("page-*.png"), key=preview_sort_key))
    if not preview_files:
        raise ExportResumePdfDependencyError(
            "pdftoppm did not produce any preview PNG files for export-resume-pdf."
        )
    return preview_files


def render_export_resume_pdf_report(
    *,
    projection: ResumePdfProjection,
    pdf_path: Path,
    report_path: Path,
    preview_files: tuple[Path, ...],
    page_count: int,
) -> str:
    render_fingerprint = build_projection_fingerprint(projection)
    contact_lines = [f"- {item}" for item in projection.surface.contacts] or ["- none"]
    public_link_lines = [f"- {item}" for item in projection.surface.public_links] or ["- none"]
    section_lines = [f"- {section.heading}: {count_section_blocks(section)} blocks" for section in projection.sections] or ["- none"]
    preview_lines = [f"- `{path.name}`" for path in preview_files] or ["- none"]
    lines = [
        "# Export Resume PDF Render Report",
        "",
        "## Summary",
        "",
        f"- Target resume: {projection.target_resume}",
        f"- Output language: {projection.output_language}",
        f"- Contact region: {projection.contact_region}",
        f"- Template: {projection.template_id}",
        f"- Renderer version: {RENDERER_VERSION}",
        f"- Render fingerprint: `{render_fingerprint}`",
        f"- PDF artifact: `{pdf_path}`",
        f"- Verification report: `{report_path}`",
        f"- Preview pages: {page_count}",
        "",
        "## Rendered Surface",
        "",
        f"- Display name: {projection.surface.full_name}",
        f"- Title: {projection.surface.title}",
        f"- Location: {projection.surface.location}",
        f"- Relocation: {projection.surface.relocation}",
        "",
        "## Public Contacts",
        "",
        *contact_lines,
        "",
        "## Public Links",
        "",
        *public_link_lines,
        "",
        "## Parsed Sections",
        "",
        *section_lines,
        "",
        "## Preview Files",
        "",
        *preview_lines,
        "",
    ]
    return ensure_trailing_newline("\n".join(lines))


def build_render_summary(
    *,
    projection: ResumePdfProjection,
    pdf_path: Path,
    report_path: Path,
    preview_files: tuple[Path, ...],
    changed: bool,
) -> tuple[str, ...]:
    return (
        f"target_resume={projection.target_resume}",
        f"output_language={projection.output_language}",
        f"contact_region={projection.contact_region}",
        f"template_id={projection.template_id}",
        f"changed={'yes' if changed else 'no'}",
        f"pdf={pdf_path}",
        f"report={report_path}",
        f"preview_pages={len(preview_files)}",
    )


def artifacts_changed(
    *,
    pdf_output_path: Path,
    report_path: Path,
    preview_dir: Path,
    generated_pdf_bytes: bytes,
    generated_report: str,
    generated_preview_dir: Path,
) -> bool:
    if not pdf_output_path.exists() or not report_path.exists() or not preview_dir.exists():
        return True
    if pdf_output_path.stat().st_size == 0:
        return True
    if report_path.read_text(encoding="utf-8") != generated_report:
        return True
    return preview_fingerprint(preview_dir) != preview_fingerprint(generated_preview_dir)


def persist_export_artifacts(
    *,
    pdf_output_path: Path,
    report_path: Path,
    preview_dir: Path,
    generated_pdf_bytes: bytes,
    generated_report: str,
    generated_preview_dir: Path,
) -> None:
    pdf_output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)
    pdf_output_path.write_bytes(generated_pdf_bytes)
    report_path.write_text(generated_report, encoding="utf-8", newline="\n")
    existing_names = {path.name for path in preview_dir.glob("page-*.png")}
    generated_names = {path.name for path in generated_preview_dir.glob("page-*.png")}
    for generated_preview in generated_preview_dir.glob("page-*.png"):
        shutil.copy2(generated_preview, preview_dir / generated_preview.name)
    for stale_name in sorted(existing_names - generated_names):
        try:
            (preview_dir / stale_name).unlink(missing_ok=True)
        except PermissionError:
            pass

def preview_fingerprint(path: Path) -> tuple[tuple[str, bytes], ...]:
    if not path.exists():
        return ()
    fingerprint: list[tuple[str, bytes]] = []
    for file_path in sorted(path.glob("page-*.png"), key=preview_sort_key):
        fingerprint.append((file_path.name, file_path.read_bytes()))
    return tuple(fingerprint)


def build_pdf_story(
    *,
    projection: ResumePdfProjection,
    styles: dict[str, object],
    Paragraph,
    Spacer,
    ListFlowable,
    ListItem,
) -> list[object]:
    story: list[object] = [
        render_paragraph(projection.surface.title, styles["title"], Paragraph),
        Spacer(1, 2.5),
    ]

    surface_items = list(projection.surface.contacts + projection.surface.public_links)
    for row in chunked(surface_items, size=3):
        story.append(render_paragraph(" | ".join(row), styles["surface"], Paragraph))
    story.append(render_paragraph(f"Город/страна: {projection.surface.location}", styles["surface"], Paragraph))
    story.append(render_paragraph(f"Готовность к переезду: {projection.surface.relocation}", styles["surface"], Paragraph))
    story.append(Spacer(1, 4.0))

    for section in projection.sections:
        story.append(render_paragraph(section.heading, styles["section"], Paragraph))
        story.append(Spacer(1, 1.0))
        append_blocks_to_story(
            story=story,
            blocks=section.blocks,
            styles=styles,
            Paragraph=Paragraph,
            Spacer=Spacer,
            ListFlowable=ListFlowable,
            ListItem=ListItem,
        )
        story.append(Spacer(1, 2.0))

    return story


def append_blocks_to_story(
    *,
    story: list[object],
    blocks: tuple[ResumeBlock, ...],
    styles: dict[str, object],
    Paragraph,
    Spacer,
    ListFlowable,
    ListItem,
) -> None:
    for block in blocks:
        if block.kind == "paragraph":
            style = styles["role"] if INLINE_BOLD_LINE_RE.fullmatch(block.text) else styles["body"]
            story.append(render_paragraph(block.text, style, Paragraph))
            story.append(Spacer(1, 1.2))
            continue

        if block.kind == "bullets":
            items = [ListItem(render_paragraph(item, styles["bullet"], Paragraph)) for item in block.items]
            story.append(
                ListFlowable(
                    items,
                    bulletType="bullet",
                    start="-",
                    leftIndent=0,
                    bulletFontName="Helvetica",
                    bulletFontSize=8,
                    bulletOffsetY=0.0,
                )
            )
            story.append(Spacer(1, 1.4))
            continue

        if block.kind == "subsection":
            story.append(render_paragraph(block.text, styles["subsection"], Paragraph))
            story.append(Spacer(1, 0.8))
            append_blocks_to_story(
                story=story,
                blocks=block.children,
                styles=styles,
                Paragraph=Paragraph,
                Spacer=Spacer,
                ListFlowable=ListFlowable,
                ListItem=ListItem,
            )


def build_pdf_styles(*, colors, ParagraphStyle, getSampleStyleSheet, TA_CENTER) -> dict[str, object]:
    styles = getSampleStyleSheet()
    base = ParagraphStyle(
        "ResumeBase",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.7,
        leading=10.4,
        textColor=colors.HexColor("#1f2937"),
        spaceAfter=0,
    )
    return {
        "title": ParagraphStyle(
            "ResumeTitle",
            parent=base,
            fontName="Helvetica-Bold",
            fontSize=17.5,
            leading=20.0,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#0f172a"),
        ),
        "surface": ParagraphStyle(
            "ResumeSurface",
            parent=base,
            alignment=TA_CENTER,
            fontSize=8.0,
            leading=9.2,
            textColor=colors.HexColor("#334155"),
        ),
        "section": ParagraphStyle(
            "ResumeSection",
            parent=base,
            fontName="Helvetica-Bold",
            fontSize=11.2,
            leading=12.6,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=3.5,
        ),
        "subsection": ParagraphStyle(
            "ResumeSubsection",
            parent=base,
            fontName="Helvetica-Bold",
            fontSize=9.3,
            leading=10.5,
            textColor=colors.HexColor("#111827"),
        ),
        "role": ParagraphStyle(
            "ResumeRole",
            parent=base,
            fontName="Helvetica-Bold",
            fontSize=8.8,
            leading=10.2,
            textColor=colors.HexColor("#111827"),
        ),
        "body": ParagraphStyle(
            "ResumeBody",
            parent=base,
        ),
        "bullet": ParagraphStyle(
            "ResumeBullet",
            parent=base,
            leftIndent=10,
            firstLineIndent=0,
        ),
    }


def draw_footer(canvas, document, *, colors, title: str, page_size, mm) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#cbd5e1"))
    canvas.setLineWidth(0.4)
    canvas.line(document.leftMargin, 10.5 * mm, page_size[0] - document.rightMargin, 10.5 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawString(document.leftMargin, 6.5 * mm, title[:60])
    canvas.drawRightString(page_size[0] - document.rightMargin, 6.5 * mm, f"Page {canvas.getPageNumber()}")
    canvas.restoreState()


def require_reportlab():
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas
        from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer
    except ModuleNotFoundError as exc:
        raise ExportResumePdfDependencyError(
            "reportlab is required for export-resume-pdf rendering."
        ) from exc

    return (
        canvas,
        colors,
        TA_CENTER,
        A4,
        ParagraphStyle,
        getSampleStyleSheet,
        mm,
        ListFlowable,
        ListItem,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
    )


def parse_resume_sections(markdown: str) -> tuple[ResumeSection, ...]:
    lines = normalize_newlines(markdown).splitlines()
    index = 0
    sections: list[ResumeSection] = []

    while index < len(lines):
        while index < len(lines) and not lines[index].strip():
            index += 1
        if index >= len(lines):
            break

        heading_match = H2_RE.match(lines[index].strip())
        if heading_match:
            heading = normalize_display_text(heading_match.group("title"))
            index += 1
            blocks, index = parse_blocks(lines, index, stop_at_h2=True)
            sections.append(ResumeSection(heading=heading, blocks=tuple(blocks)))
            continue

        blocks, index = parse_blocks(lines, index, stop_at_h2=True)
        if blocks:
            sections.append(ResumeSection(heading="Профиль", blocks=tuple(blocks)))

    return tuple(sections)


def parse_blocks(lines: list[str], start_index: int, *, stop_at_h2: bool) -> tuple[list[ResumeBlock], int]:
    blocks: list[ResumeBlock] = []
    index = start_index

    while index < len(lines):
        stripped = lines[index].strip()
        if H2_RE.match(stripped):
            break
        if not stripped:
            index += 1
            continue
        h3_match = H3_RE.match(stripped)
        if h3_match:
            index += 1
            children, index = parse_blocks(lines, index, stop_at_h2=False)
            blocks.append(
                ResumeBlock(
                    kind="subsection",
                    text=normalize_display_text(h3_match.group("title")),
                    children=tuple(children),
                )
            )
            continue
        if not stop_at_h2 and H3_RE.match(stripped):
            break
        if stripped.startswith("- "):
            items: list[str] = []
            while index < len(lines):
                bullet_line = lines[index].strip()
                if not bullet_line.startswith("- "):
                    break
                items.append(clean_markdown_inline(bullet_line[2:]))
                index += 1
            blocks.append(ResumeBlock(kind="bullets", items=tuple(item for item in items if item)))
            continue

        paragraph_lines: list[str] = []
        while index < len(lines):
            candidate = lines[index].strip()
            if not candidate:
                break
            if H2_RE.match(candidate):
                break
            if not stop_at_h2 and H3_RE.match(candidate):
                break
            if candidate.startswith("- "):
                break
            paragraph_lines.append(candidate)
            index += 1
        paragraph_text = normalize_display_text(" ".join(paragraph_lines))
        if paragraph_text:
            blocks.append(ResumeBlock(kind="paragraph", text=paragraph_text))
        continue

    return blocks, index


def strip_surface_block(body: str) -> str:
    lines = normalize_newlines(body).splitlines()
    index = 0
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index < len(lines) and lines[index].strip().startswith("- "):
        while index < len(lines):
            if lines[index].strip().startswith("## "):
                break
            index += 1
    return ensure_trailing_newline("\n".join(lines[index:]).lstrip("\n"))


def split_title_and_body(markdown: str) -> tuple[str, str]:
    lines = normalize_newlines(markdown).splitlines()
    for index, raw_line in enumerate(lines):
        match = H1_RE.match(raw_line.strip())
        if match:
            title = clean_markdown_inline(match.group("title"))
            remainder = ensure_trailing_newline("\n".join(lines[index + 1 :]).lstrip("\n"))
            return title, remainder
    return "", normalize_newlines(markdown)


def build_contact_lines(*, region_scalars: dict[str, str], resume_scalars: dict[str, str], region: str) -> tuple[str, ...]:
    contacts = {
        "Телефон": first_non_empty(region_scalars.get("phone"), resolve_scalar_by_region(resume_scalars, "contacts.phone", region)),
        "E-mail": first_non_empty(region_scalars.get("email"), resolve_scalar_by_region(resume_scalars, "contacts.email", region)),
        "Telegram": first_non_empty(region_scalars.get("telegram"), resume_scalars.get("contacts.telegram")),
        "WhatsApp": first_non_empty(
            region_scalars.get("whatsapp"), resolve_scalar_by_region(resume_scalars, "contacts.whatsapp", region)
        ),
    }
    lines = [f"{label}: {value}" for label, value in contacts.items() if value]
    return tuple(lines)


def build_public_link_lines(*, profile_scalars: dict[str, str], resume_scalars: dict[str, str]) -> tuple[str, ...]:
    link_candidates = {
        "LinkedIn": first_non_empty(profile_scalars.get("links.linkedin"), resume_scalars.get("links.linkedin")),
        "GitHub": first_non_empty(profile_scalars.get("links.github"), resume_scalars.get("links.github")),
        "Website": first_non_empty(profile_scalars.get("links.website"), resume_scalars.get("links.website")),
    }
    return tuple(f"{label}: {value}" for label, value in link_candidates.items() if value)


def resolve_full_name(resume_scalars: dict[str, str], profile_scalars: dict[str, str], region: str) -> str:
    return first_non_empty(
        resolve_scalar_by_region(profile_scalars, "full_name", region),
        resolve_scalar_by_region(resume_scalars, "full_name", region),
        resume_scalars.get("full_name"),
        "Уточнить публичное имя.",
    )


def resolve_region_value(
    *,
    region_scalars: dict[str, str],
    resume_scalars: dict[str, str],
    region: str,
    key: str,
    fallback: str,
) -> str:
    return first_non_empty(region_scalars.get(key), resolve_scalar_by_region(resume_scalars, key, region), resume_scalars.get(key), fallback)


def resolve_placeholder_surface_values(
    resume_scalars: dict[str, str],
    profile_scalars: dict[str, str],
    region: str,
) -> dict[str, str]:
    region_scalars = extract_region_scalars(profile_scalars, region)
    return {
        "full_name": resolve_full_name(resume_scalars, profile_scalars, region),
        "location": resolve_region_value(
            region_scalars=region_scalars,
            resume_scalars=resume_scalars,
            region=region,
            key="location",
            fallback="",
        ),
        "relocation": resolve_region_value(
            region_scalars=region_scalars,
            resume_scalars=resume_scalars,
            region=region,
            key="relocation",
            fallback="",
        ),
        "contacts.phone": first_non_empty(region_scalars.get("phone"), resolve_scalar_by_region(resume_scalars, "contacts.phone", region)),
        "contacts.email": first_non_empty(region_scalars.get("email"), resolve_scalar_by_region(resume_scalars, "contacts.email", region)),
        "contacts.telegram": first_non_empty(region_scalars.get("telegram"), resume_scalars.get("contacts.telegram")),
        "contacts.whatsapp": first_non_empty(
            region_scalars.get("whatsapp"), resolve_scalar_by_region(resume_scalars, "contacts.whatsapp", region)
        ),
        "links.linkedin": first_non_empty(profile_scalars.get("links.linkedin"), resume_scalars.get("links.linkedin")),
        "links.github": first_non_empty(profile_scalars.get("links.github"), resume_scalars.get("links.github")),
        "links.website": first_non_empty(profile_scalars.get("links.website"), resume_scalars.get("links.website")),
    }


def extract_region_scalars(profile_scalars: dict[str, str], region: str) -> dict[str, str]:
    prefix = f"regions.{region}."
    extracted: dict[str, str] = {}
    for key, value in profile_scalars.items():
        if key.startswith(prefix):
            extracted[key[len(prefix) :]] = value
    return extracted


def resolve_scalar_by_region(payload: dict[str, str], base_key: str, region: str) -> str:
    locale_preferences = {
        "RU": ("ru",),
        "KZ": ("kz", "ru"),
        "EU": ("eu", "en", "ru"),
    }
    for locale in locale_preferences.get(region, ()):
        value = payload.get(f"{base_key}.{locale}")
        if value:
            return value
    return payload.get(base_key, "")


def extract_front_matter_scalar_map(markdown: str) -> dict[str, str]:
    lines = normalize_newlines(markdown).splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    payload_lines: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            return load_nested_scalar_map("\n".join(payload_lines))
        payload_lines.append(line)
    return {}


def strip_front_matter(markdown: str) -> str:
    lines = normalize_newlines(markdown).splitlines()
    if not lines or lines[0].strip() != "---":
        return normalize_newlines(markdown)
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return ensure_trailing_newline("\n".join(lines[index + 1 :]).lstrip("\n"))
    return normalize_newlines(markdown)


def load_nested_scalar_map(text: str) -> dict[str, str]:
    if not text.strip():
        return {}

    payload: dict[str, str] = {}
    stack: list[tuple[int, str]] = []
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#") or ":" not in raw_line:
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        stripped = raw_line.strip()
        key, raw_value = stripped.split(":", maxsplit=1)
        key = key.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        if raw_value.strip():
            value = parse_scalar(raw_value.strip())
            path = ".".join([segment for _, segment in stack] + [key])
            payload[path] = value
            continue
        stack.append((indent, key))
    return payload


def parse_scalar(value: str) -> str:
    stripped = value.strip()
    if stripped.startswith('"') and stripped.endswith('"'):
        stripped = stripped[1:-1]
    if stripped.startswith("'") and stripped.endswith("'"):
        stripped = stripped[1:-1]
    return normalize_display_text(stripped)


def substitute_placeholders(markdown: str, values: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        key = match.group("key")
        return values.get(key, "")

    return ensure_trailing_newline(PLACEHOLDER_RE.sub(replace, normalize_newlines(markdown)))


def render_paragraph(text: str, style, Paragraph):
    return Paragraph(convert_inline_markup(text), style)


def convert_inline_markup(value: str) -> str:
    value = normalize_display_text(value)
    value = re.sub(r"<(https?://[^>]+)>", r"\1", value)
    value = html.escape(value)
    value = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", value)
    value = LINK_RE.sub(lambda match: f'<link href="{match.group(2)}" color="#334155">{match.group(1)}</link>', value)
    value = RAW_URL_RE.sub(lambda match: f'<link href="{match.group(1)}" color="#334155">{match.group(1)}</link>', value)
    value = EMAIL_RE.sub(
        lambda match: f'<link href="mailto:{match.group(1)}" color="#334155">{match.group(1)}</link>',
        value,
    )
    return value


def clean_markdown_inline(value: str) -> str:
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", value)
    cleaned = re.sub(r"`(.*?)`", r"\1", cleaned)
    cleaned = cleaned.replace("<", "").replace(">", "")
    return normalize_display_text(cleaned)


def normalize_display_text(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\u2014", " - ").replace("\u2013", "-").replace("\u2011", "-")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r" *\n *", "\n", normalized)
    return normalized.strip()


def first_non_empty(*values: str) -> str:
    for value in values:
        normalized = normalize_text(value)
        if normalized:
            return normalized
    return ""


def build_projection_fingerprint(projection: ResumePdfProjection) -> str:
    lines = [
        RENDERER_VERSION,
        projection.target_resume,
        projection.output_language,
        projection.contact_region,
        projection.template_id,
        projection.surface.full_name,
        projection.surface.title,
        projection.surface.location,
        projection.surface.relocation,
        *projection.surface.contacts,
        *projection.surface.public_links,
    ]
    for section in projection.sections:
        lines.append(section.heading)
        append_block_fingerprint(lines, section.blocks)
    payload = "\n".join(lines).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


def append_block_fingerprint(lines: list[str], blocks: tuple[ResumeBlock, ...]) -> None:
    for block in blocks:
        lines.append(block.kind)
        lines.append(block.text)
        lines.extend(block.items)
        append_block_fingerprint(lines, block.children)


def count_section_blocks(section: ResumeSection) -> int:
    total = 0
    for block in section.blocks:
        total += 1
        if block.kind == "subsection":
            total += len(block.children)
    return total


def preview_sort_key(path: Path) -> tuple[int, str]:
    match = PNG_PAGE_RE.match(path.name)
    if match:
        return (int(match.group("page")), path.name)
    return (0, path.name)


def chunked(items: list[str], *, size: int) -> list[list[str]]:
    return [items[index : index + size] for index in range(0, len(items), size)]
