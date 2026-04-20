from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from application_agent.memory.models import WorkflowRun
from application_agent.memory.store import JsonMemoryStore
from application_agent.workflows.base import WorkflowResult
from application_agent.workspace import WorkspaceLayout

CYRILLIC_MAP = {
    "\u0430": "a",
    "\u0431": "b",
    "\u0432": "v",
    "\u0433": "g",
    "\u0434": "d",
    "\u0435": "e",
    "\u0451": "e",
    "\u0436": "zh",
    "\u0437": "z",
    "\u0438": "i",
    "\u0439": "y",
    "\u043a": "k",
    "\u043b": "l",
    "\u043c": "m",
    "\u043d": "n",
    "\u043e": "o",
    "\u043f": "p",
    "\u0440": "r",
    "\u0441": "s",
    "\u0442": "t",
    "\u0443": "u",
    "\u0444": "f",
    "\u0445": "h",
    "\u0446": "ts",
    "\u0447": "ch",
    "\u0448": "sh",
    "\u0449": "sch",
    "\u044a": "",
    "\u044b": "y",
    "\u044c": "",
    "\u044d": "e",
    "\u044e": "yu",
    "\u044f": "ya",
}

BLOCK_TAGS = {
    "article",
    "blockquote",
    "br",
    "div",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "main",
    "p",
    "section",
    "tr",
}
SKIP_TAGS = {"script", "style", "noscript"}
TITLE_PATTERNS = (
    re.compile(
        "\\u0412\\u0430\\u043a\\u0430\\u043d\\u0441\\u0438\\u044f\\s+(?P<position>.+?)\\s+\\u0432\\s+\\u043a\\u043e\\u043c\\u043f\\u0430\\u043d\\u0438\\u0438\\s+(?P<company>.+?)(?:\\s*[\\|\\-\\u2013\\u2014].*)?$",
        re.IGNORECASE,
    ),
    re.compile(
        "(?P<position>.+?)\\s+\\u0432\\s+\\u043a\\u043e\\u043c\\u043f\\u0430\\u043d\\u0438\\u0438\\s+(?P<company>.+?)(?:\\s*[\\|\\-\\u2013\\u2014].*)?$",
        re.IGNORECASE,
    ),
    re.compile("Work in\\s+(?P<company>.+?)\\s*[\\-\\u2013\\u2014]\\s*(?P<position>.+?)(?:\\s*[\\|\\-\\u2013\\u2014].*)?$", re.IGNORECASE),
    re.compile("(?P<position>.+?)\\s*[\\-\\u2013\\u2014]\\s*(?P<company>.+?)(?:\\s*[\\|\\-\\u2013\\u2014].*)?$", re.IGNORECASE),
)
BROKEN_MARKERS = ("\u00d0", "\u00d1", "\u00d2", "\u00d3", "\u00d4", "\u00d5", "\u00d6", "\u00d7", "\u00d8", "\u00d9", "\u00da", "\u00db", "\u00dc", "\u00dd", "\u00de", "\u00df", "\u00c2", "\u00c3")


def normalize_inline(text: str) -> str:
    return re.sub(r"\s+", " ", unescape(text).replace("\xa0", " ")).strip()


def normalize_multiline(text: str) -> str:
    normalized_lines = [normalize_inline(line) for line in text.replace("\r", "\n").split("\n")]
    filtered_lines = [line for line in normalized_lines if line]
    return "\n".join(filtered_lines).strip()


def text_score(text: str) -> tuple[int, int, int]:
    cyrillic = sum(1 for char in text if "\u0400" <= char <= "\u04ff")
    broken = sum(text.count(marker) for marker in BROKEN_MARKERS) + text.count("\ufffd")
    letters = sum(1 for char in text if char.isalpha())
    return (cyrillic * 4 + letters, -broken * 5, -len(text))


def repair_mojibake(text: str) -> str:
    candidates = {text}
    for source_encoding, target_encoding in (("latin-1", "utf-8"), ("latin-1", "cp1251"), ("cp1251", "utf-8")):
        try:
            candidates.add(text.encode(source_encoding).decode(target_encoding))
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
    return max(candidates, key=text_score)


def clean_text(text: str) -> str:
    return repair_mojibake(normalize_inline(text))


def clean_multiline_text(text: str) -> str:
    return repair_mojibake(normalize_multiline(text))


def decode_bytes(raw: bytes, encodings: list[str]) -> str:
    seen: set[str] = set()
    decoded_candidates: list[str] = []
    for encoding in encodings:
        if not encoding or encoding in seen:
            continue
        seen.add(encoding)
        try:
            decoded_candidates.append(raw.decode(encoding))
        except UnicodeDecodeError:
            continue
    if not decoded_candidates:
        decoded_candidates.append(raw.decode("utf-8", errors="replace"))
    repaired_candidates = [repair_mojibake(candidate) for candidate in decoded_candidates]
    return max(repaired_candidates, key=text_score)


class HtmlTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in SKIP_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag in BLOCK_TAGS and self.parts and not self.parts[-1].endswith("\n"):
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIP_TAGS:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if self.skip_depth:
            return
        if tag in BLOCK_TAGS and self.parts and not self.parts[-1].endswith("\n"):
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        self.parts.append(data)

    def get_text(self) -> str:
        return clean_multiline_text("".join(self.parts))


class VacancyPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.html_lang = ""
        self.title_parts: list[str] = []
        self.h1_parts: list[str] = []
        self.meta: dict[str, str] = {}
        self.json_ld_chunks: list[str] = []
        self._capture_title = False
        self._capture_h1 = False
        self._capture_json_ld = False
        self._json_ld_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key.lower(): value for key, value in attrs if key}
        if tag == "html" and attrs_dict.get("lang"):
            self.html_lang = attrs_dict["lang"] or ""
            return
        if tag == "title":
            self._capture_title = True
            return
        if tag == "h1":
            self._capture_h1 = True
            return
        if tag == "meta":
            key = (attrs_dict.get("property") or attrs_dict.get("name") or attrs_dict.get("itemprop") or "").lower()
            value = attrs_dict.get("content") or ""
            if key and value and key not in self.meta:
                self.meta[key] = value
            return
        if tag == "script" and (attrs_dict.get("type") or "").lower() == "application/ld+json":
            self._capture_json_ld = True
            self._json_ld_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._capture_title = False
            return
        if tag == "h1":
            self._capture_h1 = False
            return
        if tag == "script" and self._capture_json_ld:
            chunk = "".join(self._json_ld_parts).strip()
            if chunk:
                self.json_ld_chunks.append(chunk)
            self._capture_json_ld = False
            self._json_ld_parts = []

    def handle_data(self, data: str) -> None:
        if self._capture_title:
            self.title_parts.append(data)
        if self._capture_h1:
            self.h1_parts.append(data)
        if self._capture_json_ld:
            self._json_ld_parts.append(data)

    @property
    def title(self) -> str:
        return clean_text("".join(self.title_parts))

    @property
    def h1(self) -> str:
        return clean_text("".join(self.h1_parts))


@dataclass
class VacancySourceDetails:
    company: str = ""
    position: str = ""
    source_text: str = ""
    language: str = ""


def html_to_text(html: str) -> str:
    parser = HtmlTextExtractor()
    parser.feed(html)
    return parser.get_text()


def slugify(value: str, fallback: str) -> str:
    lowered = value.strip().lower()
    transliterated = "".join(CYRILLIC_MAP.get(char, char) for char in lowered)
    cleaned = re.sub(r"[^a-z0-9]+", "-", transliterated)
    cleaned = re.sub(r"-{2,}", "-", cleaned).strip("-")
    return cleaned or fallback


def build_vacancy_id(day: date, company: str, position: str) -> str:
    return f"{day:%Y%m%d}-{slugify(company, 'company')}-{slugify(position, 'role')}"


def resolve_vacancy_id(layout: WorkspaceLayout, base_id: str) -> str:
    candidate = base_id
    suffix = 2
    while layout.vacancy_dir(candidate).exists():
        candidate = f"{base_id}-{suffix:02d}"
        suffix += 1
    return candidate


def parse_hh_vacancy_url(source_url: str) -> str | None:
    parsed = urlparse(source_url)
    if not parsed.netloc.endswith("hh.ru"):
        return None
    match = re.search(r"/vacancy/(\d+)", parsed.path)
    if not match:
        return None
    return match.group(1)


def fetch_url(source_url: str, *, accept: str) -> str:
    request = Request(
        source_url,
        headers={
            "User-Agent": "application-agent/0.1 (+https://api.hh.ru)",
            "Accept": accept,
        },
    )
    with urlopen(request, timeout=15) as response:
        raw = response.read()
        header_encoding = response.headers.get_content_charset()
        candidates = [header_encoding]
        if "json" in accept:
            candidates.extend(["utf-8", "utf-8-sig", "cp1251", "latin-1"])
        else:
            candidates.extend(["utf-8", "utf-8-sig", "cp1251", "latin-1"])
        return decode_bytes(raw, [encoding for encoding in candidates if encoding])


def parse_hh_vacancy_payload(payload: str) -> VacancySourceDetails:
    data = json.loads(payload)
    description = html_to_text(str(data.get("description", "") or ""))
    if not description:
        description = clean_multiline_text(
            "\n".join(
                [
                    str(data.get("snippet", {}).get("responsibility", "") or ""),
                    str(data.get("snippet", {}).get("requirement", "") or ""),
                ]
            )
        )
    employer = data.get("employer") or {}
    return VacancySourceDetails(
        company=clean_text(str(employer.get("name", "") or "")),
        position=clean_text(str(data.get("name", "") or "")),
        source_text=description,
        language=clean_text(str(data.get("language", "") or "")),
    )


def iter_json_nodes(value: object) -> list[dict[str, object]]:
    nodes: list[dict[str, object]] = []
    if isinstance(value, dict):
        nodes.append(value)
        graph = value.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                nodes.extend(iter_json_nodes(item))
    elif isinstance(value, list):
        for item in value:
            nodes.extend(iter_json_nodes(item))
    return nodes


def parse_structured_job_posting(chunks: list[str]) -> VacancySourceDetails:
    for chunk in chunks:
        try:
            payload = json.loads(chunk)
        except json.JSONDecodeError:
            continue
        for node in iter_json_nodes(payload):
            raw_type = node.get("@type")
            if isinstance(raw_type, str):
                types = [raw_type]
            elif isinstance(raw_type, list):
                types = [item for item in raw_type if isinstance(item, str)]
            else:
                types = []
            normalized_types = {item.lower() for item in types}
            if "jobposting" not in normalized_types:
                continue
            organization = node.get("hiringOrganization") or {}
            company = ""
            if isinstance(organization, dict):
                company = clean_text(str(organization.get("name", "") or ""))
            return VacancySourceDetails(
                company=company,
                position=clean_text(str(node.get("title", "") or node.get("name", "") or "")),
                source_text=html_to_text(str(node.get("description", "") or "")),
            )
    return VacancySourceDetails()


def derive_title_parts(raw_title: str) -> VacancySourceDetails:
    cleaned = clean_text(raw_title)
    for pattern in TITLE_PATTERNS:
        match = pattern.match(cleaned)
        if match:
            return VacancySourceDetails(
                company=clean_text(match.groupdict().get("company", "") or ""),
                position=clean_text(match.groupdict().get("position", "") or ""),
            )
    return VacancySourceDetails(position=cleaned)


def parse_generic_vacancy_page(html: str) -> VacancySourceDetails:
    parser = VacancyPageParser()
    parser.feed(html)
    structured = parse_structured_job_posting(parser.json_ld_chunks)
    title_parts = derive_title_parts(parser.meta.get("og:title") or parser.title or parser.h1)

    source_text = structured.source_text
    if not source_text:
        source_text = clean_multiline_text(parser.meta.get("description", "") or parser.meta.get("og:description", ""))
    if not source_text:
        source_text = html_to_text(html)

    return VacancySourceDetails(
        company=structured.company or title_parts.company,
        position=structured.position or parser.h1 or title_parts.position,
        source_text=source_text,
        language=clean_text(parser.html_lang),
    )


def fetch_source_details(source_url: str) -> VacancySourceDetails:
    vacancy_id = parse_hh_vacancy_url(source_url)
    if vacancy_id:
        try:
            payload = fetch_url(f"https://api.hh.ru/vacancies/{vacancy_id}", accept="application/json")
            details = parse_hh_vacancy_payload(payload)
            if details.company or details.position or details.source_text:
                return details
        except Exception:
            pass
    html = fetch_url(source_url, accept="text/html,application/xhtml+xml")
    return parse_generic_vacancy_page(html)


def enrich_request(request: "IngestVacancyRequest") -> "IngestVacancyRequest":
    if not request.source_url.strip():
        return request
    needs_enrichment = not request.company.strip() or not request.position.strip() or not request.source_text.strip()
    if not needs_enrichment:
        return request
    try:
        details = fetch_source_details(request.source_url.strip())
    except Exception:
        return request

    language = request.language
    if not language.strip() and details.language:
        language = details.language

    return replace(
        request,
        company=request.company.strip() or details.company,
        position=request.position.strip() or details.position,
        source_text=request.source_text.strip() or details.source_text,
        language=language,
    )


@dataclass
class IngestVacancyRequest:
    company: str = ""
    position: str = ""
    source_text: str = ""
    source_url: str = ""
    source_channel: str = "Manual"
    source_type: str = ""
    language: str = "ru"
    country: str = "\u041d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d\u043e"
    work_mode: str = "\u041d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d\u043e"
    target_mode: str = "balanced"
    include_employer_channels: bool = False
    ingest_date: date = field(default_factory=date.today)

    def normalized_source_type(self) -> str:
        if self.source_type:
            return self.source_type
        has_url = bool(self.source_url.strip())
        has_text = bool(self.source_text.strip())
        if has_url and has_text:
            return "url+text"
        if has_url:
            return "url"
        return "text"


class IngestVacancyWorkflow:
    name = "ingest-vacancy"
    description = "\u0421\u043e\u0437\u0434\u0430\u0451\u0442 \u043a\u0430\u0440\u043a\u0430\u0441 \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u0438 \u0438 \u0437\u0430\u043f\u0438\u0441\u044b\u0432\u0430\u0435\u0442 \u0441\u0442\u0430\u0440\u0442\u043e\u0432\u044b\u0439 runtime-\u0441\u043b\u0435\u0434."

    def run(self, *, layout: WorkspaceLayout, store: JsonMemoryStore, request: IngestVacancyRequest) -> WorkflowResult:
        started_at = datetime.now(timezone.utc).isoformat()
        request = enrich_request(request)
        missing_fields = [name for name, value in (("company", request.company), ("position", request.position)) if not value.strip()]
        if missing_fields:
            missing = ", ".join(missing_fields)
            raise ValueError(
                f"ingest-vacancy requires company and position, unless they can be extracted from source_url. Missing: {missing}."
            )

        base_id = build_vacancy_id(request.ingest_date, request.company, request.position)
        vacancy_id = resolve_vacancy_id(layout, base_id)
        vacancy_dir = layout.vacancy_dir(vacancy_id)
        vacancy_dir.mkdir(parents=True, exist_ok=True)

        meta_path = vacancy_dir / "meta.yml"
        source_path = vacancy_dir / "source.md"
        analysis_path = vacancy_dir / "analysis.md"
        adoptions_path = vacancy_dir / "adoptions.md"

        timestamp = datetime.now(timezone.utc).isoformat()
        meta_path.write_text(self._render_meta(request, vacancy_id, timestamp), encoding="utf-8", newline="\n")
        source_path.write_text(self._render_source(request, vacancy_id), encoding="utf-8", newline="\n")
        analysis_path.write_text(self._render_analysis(vacancy_id, request), encoding="utf-8", newline="\n")
        adoptions_path.write_text(self._render_adoptions(vacancy_id), encoding="utf-8", newline="\n")

        artifacts = [str(meta_path), str(source_path), str(analysis_path), str(adoptions_path)]
        store.remember_task(self.name, vacancy_id, artifacts)
        store.append_run(
            WorkflowRun(
                workflow=self.name,
                status="completed",
                started_at=started_at,
                completed_at=datetime.now(timezone.utc).isoformat(),
                artifacts=artifacts,
                summary=f"\u0421\u043e\u0437\u0434\u0430\u043d \u043a\u0430\u0440\u043a\u0430\u0441 \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u0438 {vacancy_id}.",
            )
        )
        return WorkflowResult(
            workflow=self.name,
            status="completed",
            summary=f"\u0421\u043e\u0437\u0434\u0430\u043d \u043a\u0430\u0440\u043a\u0430\u0441 \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u0438 {vacancy_id}.",
            artifacts=artifacts,
        )

    def _render_meta(self, request: IngestVacancyRequest, vacancy_id: str, timestamp: str) -> str:
        return "\n".join(
            [
                f"vacancy_id: {vacancy_id}",
                f"source_type: {request.normalized_source_type()}",
                f"source_url: {request.source_url or 'null'}",
                f"source_channel: {request.source_channel}",
                f"company: {request.company}",
                f"position: {request.position}",
                f"language: {request.language}",
                f"country: {request.country}",
                f"work_mode: {request.work_mode}",
                'is_active: "\u0414\u0430"',
                f"ingested_at: {timestamp}",
                "selected_resume: undecided",
                f"target_mode: {request.target_mode}",
                f"include_employer_channels: {str(request.include_employer_channels).lower()}",
                "excel_row: null",
                "status: ingested",
                'notes: ""',
                "",
            ]
        )

    def _render_source(self, request: IngestVacancyRequest, vacancy_id: str) -> str:
        return "\n".join(
            [
                "# \u0418\u0441\u0442\u043e\u0447\u043d\u0438\u043a \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u0438",
                "",
                "## \u041f\u0430\u0441\u043f\u043e\u0440\u0442",
                "",
                f"- \u041a\u043e\u043c\u043f\u0430\u043d\u0438\u044f: {request.company}",
                f"- \u041f\u043e\u0437\u0438\u0446\u0438\u044f: {request.position}",
                f"- ID \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u0438: {vacancy_id}",
                f"- \u0418\u0441\u0445\u043e\u0434\u043d\u0430\u044f \u0441\u0441\u044b\u043b\u043a\u0430: {request.source_url or 'n/a'}",
                f"- \u0418\u0441\u0442\u043e\u0447\u043d\u0438\u043a: {request.source_channel}",
                "",
                "## \u0418\u0441\u0445\u043e\u0434\u043d\u044b\u0439 \u0442\u0435\u043a\u0441\u0442",
                "",
                request.source_text.strip() or "<!-- \u0412\u0441\u0442\u0430\u0432\u044c \u0441\u044e\u0434\u0430 \u0438\u0441\u0445\u043e\u0434\u043d\u044b\u0439 \u0442\u0435\u043a\u0441\u0442 \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u0438 \u0431\u0435\u0437 \u0438\u043d\u0442\u0435\u0440\u043f\u0440\u0435\u0442\u0430\u0446\u0438\u0438. -->",
                "",
            ]
        )

    def _render_analysis(self, vacancy_id: str, request: IngestVacancyRequest) -> str:
        return "\n".join(
            [
                "# \u0410\u043d\u0430\u043b\u0438\u0437 \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u0438",
                "",
                "## \u0421\u0432\u043e\u0434\u043a\u0430",
                "",
                f"- ID \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u0438: {vacancy_id}",
                "- \u0412\u044b\u0431\u0440\u0430\u043d\u043d\u043e\u0435 \u0440\u0435\u0437\u044e\u043c\u0435: undecided",
                f"- \u0420\u0435\u0436\u0438\u043c \u0430\u0434\u0430\u043f\u0442\u0430\u0446\u0438\u0438: {self._render_target_mode(request.target_mode)}",
                f"- \u042f\u0437\u044b\u043a: {request.language}",
                f"- \u041a\u0430\u043d\u0430\u043b\u044b \u0440\u0430\u0431\u043e\u0442\u043e\u0434\u0430\u0442\u0435\u043b\u044f: {'\u0434\u0430' if request.include_employer_channels else '\u043d\u0435\u0442'}",
                "",
                "## \u0410\u043d\u0430\u043b\u0438\u0437 \u0441\u043e\u043e\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0438\u044f: \u0442\u0435\u043a\u0443\u0449\u0435\u0435 \u0440\u0435\u0437\u044e\u043c\u0435",
                "",
                "- \u041e\u0431\u0449\u0435\u0435 \u0441\u043e\u043e\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0438\u0435:",
                "- \u041a\u0440\u0430\u0442\u043a\u0438\u0439 \u0432\u044b\u0432\u043e\u0434:",
                "",
                "## \u0410\u043d\u0430\u043b\u0438\u0437 \u0441\u043e\u043e\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0438\u044f: \u043f\u043e\u0441\u043b\u0435 \u043f\u0440\u0435\u0434\u043b\u043e\u0436\u0435\u043d\u043d\u044b\u0445 \u043f\u0440\u0430\u0432\u043e\u043a",
                "",
                "- \u041f\u0440\u043e\u0433\u043d\u043e\u0437 \u0441\u043e\u043e\u0442\u0432\u0435\u0442\u0441\u0442\u0432\u0438\u044f:",
                "- \u041f\u0440\u0438\u0440\u043e\u0441\u0442:",
                "- \u041a\u043e\u043c\u043c\u0435\u043d\u0442\u0430\u0440\u0438\u0439:",
                "",
                "## \u041c\u0430\u0442\u0440\u0438\u0446\u0430 \u0442\u0440\u0435\u0431\u043e\u0432\u0430\u043d\u0438\u0439",
                "",
                "| \u0422\u0440\u0435\u0431\u043e\u0432\u0430\u043d\u0438\u0435 | \u041f\u0440\u0438\u043e\u0440\u0438\u0442\u0435\u0442 | \u041f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043d\u0438\u0435 | \u041f\u043e\u043a\u0440\u044b\u0442\u0438\u0435 | \u041a\u043e\u043c\u043c\u0435\u043d\u0442\u0430\u0440\u0438\u0439 |",
                "| --- | --- | --- | --- | --- |",
                "",
                "## \u0421\u0438\u043b\u044c\u043d\u044b\u0435 \u0441\u0442\u043e\u0440\u043e\u043d\u044b",
                "",
                "- ",
                "",
                "## \u041f\u0440\u043e\u0431\u0435\u043b\u044b",
                "",
                "- ",
                "",
                "## \u0417\u0430\u043c\u0435\u0442\u043a\u0438 \u0434\u043b\u044f \u0441\u043e\u043f\u0440\u043e\u0432\u043e\u0434\u0438\u0442\u0435\u043b\u044c\u043d\u043e\u0433\u043e \u043f\u0438\u0441\u044c\u043c\u0430",
                "",
                "- ",
                "",
                "## \u0417\u0430\u043c\u0435\u0442\u043a\u0438 \u043f\u043e \u043f\u0440\u0430\u0432\u043a\u0430\u043c \u0440\u0435\u0437\u044e\u043c\u0435",
                "",
                "- ",
                "",
                "## \u041a\u0430\u043d\u0430\u043b\u044b \u0441\u0432\u044f\u0437\u0438 \u0441 \u0440\u0430\u0431\u043e\u0442\u043e\u0434\u0430\u0442\u0435\u043b\u0435\u043c",
                "",
                "- ",
                "",
                "## \u0412\u043e\u043f\u0440\u043e\u0441\u044b \u043d\u0430 \u0443\u0442\u043e\u0447\u043d\u0435\u043d\u0438\u0435",
                "",
                "- ",
                "",
            ]
        )

    def _render_adoptions(self, vacancy_id: str) -> str:
        return "\n".join(
            [
                "# \u0410\u0434\u0430\u043f\u0442\u0430\u0446\u0438\u0438 \u043f\u043e \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u0438",
                "",
                f"- ID \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u0438: {vacancy_id}",
                "",
                "## \u0412\u0440\u0435\u043c\u0435\u043d\u043d\u044b\u0435 \u0441\u0438\u0433\u043d\u0430\u043b\u044b",
                "",
                "- ",
                "",
                "## \u041a\u0430\u043d\u0434\u0438\u0434\u0430\u0442\u044b \u0432 \u043f\u043e\u0441\u0442\u043e\u044f\u043d\u043d\u044b\u0435 \u0441\u0438\u0433\u043d\u0430\u043b\u044b",
                "",
                "- ",
                "",
                "## \u041e\u0442\u043a\u0440\u044b\u0442\u044b\u0435 \u0432\u043e\u043f\u0440\u043e\u0441\u044b",
                "",
                "- ",
                "",
                "## \u041e\u0431\u0449\u0438\u0435 \u0440\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0430\u0446\u0438\u0438 \u043f\u043e \u0434\u043e\u0431\u0430\u0432\u043b\u0435\u043d\u0438\u044e \u0438\u0437 MASTER \u0432 \u0432\u044b\u0431\u0440\u0430\u043d\u043d\u0443\u044e \u0440\u043e\u043b\u0435\u0432\u0443\u044e \u0432\u0435\u0440\u0441\u0438\u044e",
                "",
                "- ",
                "",
                "## \u041e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u0435 \u0440\u0430\u0437\u0434\u0435\u043b\u0430 `\u041e \u0441\u0435\u0431\u0435 (\u043f\u0440\u043e\u0444\u0438\u043b\u044c)`",
                "",
                "- ",
                "",
                "## \u041e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u0435 \u0440\u0430\u0437\u0434\u0435\u043b\u0430 `\u041a\u043b\u044e\u0447\u0435\u0432\u044b\u0435 \u043a\u043e\u043c\u043f\u0435\u0442\u0435\u043d\u0446\u0438\u0438`",
                "",
                "- ",
                "",
                "## \u041e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u0435 \u0440\u0430\u0437\u0434\u0435\u043b\u0430 `\u041e\u043f\u044b\u0442 \u0440\u0430\u0431\u043e\u0442\u044b`",
                "",
                "- ",
                "",
            ]
        )

    def _render_target_mode(self, target_mode: str) -> str:
        mapping = {
            "conservative": "\u043a\u043e\u043d\u0441\u0435\u0440\u0432\u0430\u0442\u0438\u0432\u043d\u044b\u0439",
            "balanced": "\u0441\u0431\u0430\u043b\u0430\u043d\u0441\u0438\u0440\u043e\u0432\u0430\u043d\u043d\u044b\u0439",
            "aggressive": "\u0430\u0433\u0440\u0435\u0441\u0441\u0438\u0432\u043d\u044b\u0439",
        }
        return mapping.get(target_mode, target_mode)
