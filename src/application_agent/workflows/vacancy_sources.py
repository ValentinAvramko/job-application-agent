from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from application_agent.integrations.playwright_renderer import render_page_with_playwright
from application_agent.normalization.countries import (
    infer_country_name_from_text,
    normalize_country_name,
    resolve_country_name_from_hh_id,
)
from application_agent.normalization.generic_page_rules import (
    GENERIC_COMPANY_STOPWORDS as DATA_GENERIC_COMPANY_STOPWORDS,
    GENERIC_UI_NOISE_LINES as DATA_GENERIC_UI_NOISE_LINES,
)
from application_agent.normalization.source_channels import infer_source_channel as infer_source_channel_value
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
GENERIC_PRIMARY_TAGS = {"main", "article", "section", "div"}
GENERIC_SKIP_CONTAINER_TAGS = {"footer", "aside", "nav", "header"}
GENERIC_POSITIVE_HINTS = ("content", "main", "description", "job", "vacancy", "posting", "article", "details")
GENERIC_NEGATIVE_HINTS = ("sidebar", "footer", "share", "social", "header", "nav", "menu", "apply", "cta", "locale", "language")
GENERIC_UI_NOISE_LINES = {
    "apply now",
    "share",
    "share to",
    "link",
    "copy",
    "department",
    "development",
    "powered by peopleforce",
    "english",
    "polski",
    "deutsch",
    "español",
    "português",
    "ukrainian",
    "magyar",
    "slovenčina",
    "українська",
}
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
HH_TITLE_PATTERN = re.compile(
    "\\u0412\\u0430\\u043a\\u0430\\u043d\\u0441\\u0438\\u044f\\s+(?P<position>.+?)\\s+\\u0432\\s+(?P<city>.+?),\\s+\\u0440\\u0430\\u0431\\u043e\\u0442\\u0430\\s+\\u0432\\s+\\u043a\\u043e\\u043c\\u043f\\u0430\\u043d\\u0438\\u0438\\s+(?P<company>.+?)(?:\\s*[\\|\\-\\u2013\\u2014].*)?$",
    re.IGNORECASE,
)
BROKEN_MARKERS = ("\u00d0", "\u00d1", "\u00d2", "\u00d3", "\u00d4", "\u00d5", "\u00d6", "\u00d7", "\u00d8", "\u00d9", "\u00da", "\u00db", "\u00dc", "\u00dd", "\u00de", "\u00df", "\u00c2", "\u00c3")
GENERIC_COMPANY_STOPWORDS = {
    "career",
    "careers",
    "company",
    "home",
    "job",
    "jobs",
    "open roles",
    "role",
    "team",
    "this role",
    "us",
    "vacancy",
}
GENERIC_COMPANY_TEXT_PATTERNS = (
    re.compile(r"\bWe are\s+(?P<company>[^\n\r|]{1,60})", re.IGNORECASE),
    re.compile(r"\bJoin\s+(?P<company>[^\n\r|]{1,60}?)(?:['’]s)?\s+team\b", re.IGNORECASE),
    re.compile(r"\bCareers at\s+(?P<company>[^\n\r|]{1,60})", re.IGNORECASE),
    re.compile(r"\bJob openings at\s+(?P<company>[^\n\r|]{1,60})", re.IGNORECASE),
    re.compile(r"\bAbout\s+(?P<company>[^\n\r|]{1,60})", re.IGNORECASE),
)


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


def collapse_blank_lines(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    collapsed: list[str] = []
    blank = False
    for line in lines:
        if not line.strip():
            if not blank and collapsed:
                collapsed.append("")
            blank = True
            continue
        collapsed.append(line.strip())
        blank = False
    return "\n".join(collapsed).strip()


def normalize_embedded_markdown_headings(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        level = len(match.group(1))
        normalized_level = 3 if level < 3 else level
        return f"{'#' * normalized_level} "

    return re.sub(r"^(#{1,6})\s+", repl, text, flags=re.MULTILINE)


def cleanup_company_candidate(value: str) -> str:
    cleaned = clean_text(value)
    if not cleaned:
        return ""
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"\s+(team|careers?|jobs?|vacancies?)$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"(?:['’]s)\s*$", "", cleaned)
    cleaned = re.sub(r"[|,;:()\[\]{}]+$", "", cleaned).strip()
    return cleaned


def is_plausible_company_name(value: str) -> bool:
    cleaned = cleanup_company_candidate(value)
    if not cleaned:
        return False
    if len(cleaned) > 80:
        return False
    lower = cleaned.lower()
    if lower in DATA_GENERIC_COMPANY_STOPWORDS:
        return False
    if lower.startswith(("open ", "this ", "join ", "about ", "see ")):
        return False
    words = [part for part in re.split(r"\s+", lower) if part]
    if words and all(word in DATA_GENERIC_COMPANY_STOPWORDS for word in words):
        return False
    return True


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


class HtmlMarkdownExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.skip_depth = 0
        self.list_depth = 0
        self.in_strong = 0

    def _ensure_line(self) -> None:
        if not self.parts:
            return
        if not self.parts[-1].endswith("\n"):
            self.parts.append("\n")

    def _ensure_blank_line(self) -> None:
        joined = "".join(self.parts)
        if not joined.endswith("\n\n"):
            self._ensure_line()
            self.parts.append("\n")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in SKIP_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        if tag in {"h1", "h2", "h3"}:
            self._ensure_blank_line()
            level = {"h1": "### ", "h2": "### ", "h3": "#### "}[tag]
            self.parts.append(level)
            return
        if tag in {"p", "div", "section"}:
            self._ensure_blank_line()
            return
        if tag in {"ul", "ol"}:
            self.list_depth += 1
            self._ensure_line()
            return
        if tag == "li":
            self._ensure_line()
            indent = "  " * max(self.list_depth - 1, 0)
            self.parts.append(f"{indent}- ")
            return
        if tag == "br":
            self._ensure_line()
            return
        if tag in {"strong", "b"}:
            self.parts.append("**")
            self.in_strong += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIP_TAGS:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if self.skip_depth:
            return
        if tag in {"ul", "ol"}:
            self.list_depth = max(0, self.list_depth - 1)
            self._ensure_blank_line()
            return
        if tag in {"p", "div", "section", "li", "h1", "h2", "h3"}:
            self._ensure_line()
            if tag in {"h1", "h2", "h3", "p", "section"}:
                self._ensure_blank_line()
            return
        if tag in {"strong", "b"} and self.in_strong:
            self.parts.append("**")
            self.in_strong -= 1

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        self.parts.append(data)

    def get_markdown(self) -> str:
        raw = "".join(self.parts)
        raw = raw.replace("\r", "")
        raw = re.sub(r"[ \t]+\n", "\n", raw)
        raw = re.sub(r"-\s*\n\s*", "- ", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return collapse_blank_lines(clean_multiline_text(raw))


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


class HHDescriptionParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key.lower(): value for key, value in attrs if key}
        if self.depth == 0 and attrs_dict.get("data-qa") == "vacancy-description":
            self.depth = 1
            return
        if self.depth:
            self.depth += 1
            self.parts.append(self.get_starttag_text())

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.depth:
            self.parts.append(self.get_starttag_text())

    def handle_endtag(self, tag: str) -> None:
        if not self.depth:
            return
        if self.depth > 1:
            self.parts.append(f"</{tag}>")
        self.depth -= 1

    def handle_data(self, data: str) -> None:
        if self.depth:
            self.parts.append(data)

    def get_html(self) -> str:
        return "".join(self.parts).strip()


class GenericPrimaryContentParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.candidates: list[dict[str, object]] = []
        self.stack: list[dict[str, object]] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key.lower(): value for key, value in attrs if key}
        if self.skip_depth:
            self.skip_depth += 1
            return
        if tag in GENERIC_SKIP_CONTAINER_TAGS:
            self.skip_depth = 1
            return

        for candidate in self.stack:
            if candidate["tag"] == tag:
                candidate["depth"] += 1
            candidate["parts"].append(self.get_starttag_text())
            if tag in {"h1", "h2", "h3", "h4"}:
                candidate["headings"] += 1
            if tag in {"p", "li"}:
                candidate["paragraphs"] += 1

        if tag not in GENERIC_PRIMARY_TAGS:
            return

        attrs_blob = " ".join(value for value in (attrs_dict.get("class"), attrs_dict.get("id")) if value).lower()
        negative = any(hint in attrs_blob for hint in GENERIC_NEGATIVE_HINTS)
        positive = any(hint in attrs_blob for hint in GENERIC_POSITIVE_HINTS)
        candidate = {
            "tag": tag,
            "depth": 1,
            "parts": [self.get_starttag_text()],
            "text": [],
            "headings": 1 if tag in {"h1", "h2", "h3", "h4"} else 0,
            "paragraphs": 1 if tag in {"p", "li"} else 0,
            "attrs_blob": attrs_blob,
            "negative": negative,
            "positive": positive,
        }
        self.stack.append(candidate)

    def handle_endtag(self, tag: str) -> None:
        if self.skip_depth:
            self.skip_depth -= 1
            return
        if not self.stack:
            return

        for candidate in self.stack:
            candidate["parts"].append(f"</{tag}>")

        for idx in range(len(self.stack) - 1, -1, -1):
            candidate = self.stack[idx]
            if candidate["tag"] != tag:
                continue
            candidate["depth"] -= 1
            if candidate["depth"] <= 0:
                self.candidates.append(candidate)
                self.stack.pop(idx)
            break

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.skip_depth:
            return
        for candidate in self.stack:
            candidate["parts"].append(self.get_starttag_text())

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        for candidate in self.stack:
            candidate["parts"].append(data)
            candidate["text"].append(data)

    def get_best_html(self) -> str:
        best_html = ""
        best_score = 0
        for candidate in self.candidates:
            text = clean_multiline_text("".join(candidate["text"]))
            if len(text) < 300:
                continue
            score = len(text)
            score += int(candidate["headings"]) * 150
            score += int(candidate["paragraphs"]) * 40
            if candidate["tag"] in {"main", "article"}:
                score += 500
            if candidate["positive"]:
                score += 300
            if candidate["negative"]:
                score -= 1000
            if score > best_score:
                best_score = score
                best_html = "".join(candidate["parts"]).strip()
        return best_html


@dataclass
class VacancySourceDetails:
    company: str = ""
    position: str = ""
    source_text: str = ""
    source_markdown: str = ""
    language: str = ""
    source_channel: str = ""
    country: str = ""
    city: str = ""
    work_mode: str = ""
    employment_type: str = ""
    work_schedule: str = ""
    key_skills: list[str] = field(default_factory=list)


def html_to_text(html: str) -> str:
    parser = HtmlTextExtractor()
    parser.feed(html)
    return parser.get_text()


def html_to_markdown(html: str) -> str:
    parser = HtmlMarkdownExtractor()
    parser.feed(html)
    return parser.get_markdown()


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


def infer_source_channel(source_url: str, source_text: str, explicit: str = "") -> str:
    return infer_source_channel_value(source_url, source_text, explicit)


def strip_value_label(text: str) -> str:
    cleaned = clean_text(text)
    if ":" in cleaned:
        _, value = cleaned.split(":", 1)
        return clean_text(value)
    return cleaned


def is_unspecified(value: str) -> bool:
    cleaned = clean_text(value).lower()
    return cleaned in {"", "\u043d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d\u043e", "n/a", "null"}


def build_response_monitoring_record(request: "IngestVacancyRequest", vacancy_id: str) -> ResponseMonitoringIngestRecord:
    source_channel = request.source_channel.strip() or infer_source_channel(request.source_url, request.source_text)
    return ResponseMonitoringIngestRecord(
        vacancy_id=vacancy_id,
        source_channel=source_channel,
        source_url=request.source_url.strip(),
        company=request.company.strip(),
        position=request.position.strip(),
        country=request.country.strip(),
        work_mode=request.work_mode.strip(),
        ingest_date=request.ingest_date,
    )


def fetch_url(source_url: str, *, accept: str) -> str:
    request = Request(
        source_url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; application-agent/0.1)",
            "Accept": accept,
        },
    )
    with urlopen(request, timeout=15) as response:
        raw = response.read()
        header_encoding = response.headers.get_content_charset()
        candidates = [header_encoding, "utf-8", "utf-8-sig", "cp1251", "latin-1"]
        return decode_bytes(raw, [encoding for encoding in candidates if encoding])


def parse_hh_vacancy_payload(payload: str) -> VacancySourceDetails:
    data = json.loads(payload)
    description = html_to_text(str(data.get("description", "") or ""))
    description_markdown = html_to_markdown(str(data.get("description", "") or ""))
    if not description:
        description = clean_multiline_text(
            "\n".join(
                [
                    str(data.get("snippet", {}).get("responsibility", "") or ""),
                    str(data.get("snippet", {}).get("requirement", "") or ""),
                ]
            )
        )
        description_markdown = description
    employer = data.get("employer") or {}
    area = data.get("area") or {}
    city = clean_text(str(area.get("name", "") or ""))
    key_skills = [clean_text(str(item.get("name", "") or "")) for item in data.get("key_skills", []) if isinstance(item, dict)]
    country = resolve_hh_country(
        city=city,
        text="\n".join(
            [
                description,
                str(data.get("snippet", {}).get("responsibility", "") or ""),
                str(data.get("snippet", {}).get("requirement", "") or ""),
            ]
        ),
        area_country=str(area.get("country", "") or ""),
    )
    return VacancySourceDetails(
        company=clean_text(str(employer.get("name", "") or "")),
        position=clean_text(str(data.get("name", "") or "")),
        source_text=build_enriched_source_text(description, key_skills, "", "", ""),
        source_markdown=build_enriched_source_markdown(description_markdown, key_skills),
        language=normalize_language_tag(str(data.get("language", "") or "")) or infer_language_from_text(description),
        source_channel="HeadHunter",
        country=country,
        city=city,
        work_mode=clean_text(str((data.get("schedule") or {}).get("name", "") or "")),
        employment_type=clean_text(str((data.get("employment") or {}).get("name", "") or "")),
        key_skills=[skill for skill in key_skills if skill],
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


def normalize_country_value(value: str) -> str:
    cleaned = clean_text(value)
    if not cleaned:
        return ""
    return normalize_country_name(cleaned)


def normalize_language_tag(value: str) -> str:
    cleaned = clean_text(value).lower().replace("_", "-")
    if not cleaned:
        return ""
    return cleaned.split("-", 1)[0]


def infer_language_from_text(text: str) -> str:
    cleaned = clean_multiline_text(text)
    if not cleaned:
        return ""
    if re.search(r"[\u0400-\u04FF]", cleaned):
        return "ru"
    if re.search(r"[A-Za-z]", cleaned):
        return "en"
    return ""


def looks_like_truncated_summary(text: str) -> bool:
    cleaned = clean_multiline_text(text)
    if not cleaned:
        return False
    lower = cleaned.lower()
    return (
        cleaned.endswith("...")
        or cleaned.endswith("\u2026")
        or " count..." in lower
        or " count\u2026" in lower
    )


def choose_preferred_page_text(primary: str, fallback: str) -> str:
    primary_clean = clean_multiline_text(primary)
    fallback_clean = clean_multiline_text(fallback)
    if not primary_clean:
        return fallback_clean
    if not fallback_clean:
        return primary_clean
    if looks_like_truncated_summary(primary_clean) and len(fallback_clean) > len(primary_clean):
        return fallback_clean
    if len(fallback_clean) > max(len(primary_clean) * 2, len(primary_clean) + 400):
        return fallback_clean
    return primary_clean


def is_generic_ui_noise_line(line: str) -> bool:
    cleaned = clean_text(line).strip(" -*#:\t").lower()
    if not cleaned:
        return False
    if cleaned in DATA_GENERIC_UI_NOISE_LINES:
        return True
    if cleaned.startswith("powered by "):
        return True
    broken = sum(cleaned.count(marker.lower()) for marker in BROKEN_MARKERS)
    if broken >= 2 and len(cleaned) <= 40:
        return True
    return False


def strip_generic_ui_noise(text: str) -> str:
    cleaned_lines = [line for line in text.splitlines() if not is_generic_ui_noise_line(line)]
    return collapse_blank_lines("\n".join(cleaned_lines))


def extract_primary_content_html(html: str) -> str:
    parser = GenericPrimaryContentParser()
    parser.feed(html)
    return parser.get_best_html()


def extract_country_from_country_node(value: object) -> str:
    if isinstance(value, dict):
        return normalize_country_value(str(value.get("name", "") or value.get("addressCountry", "") or ""))
    if isinstance(value, str):
        return normalize_country_value(value)
    return ""


def extract_structured_location(value: object) -> tuple[str, str]:
    if isinstance(value, list):
        for item in value:
            city, country = extract_structured_location(item)
            if city or country:
                return city, country
        return "", ""
    if not isinstance(value, dict):
        return "", ""

    address = value.get("address") if isinstance(value.get("address"), dict) else {}
    city = clean_text(str(address.get("addressLocality", "") or value.get("addressLocality", "") or ""))
    country = normalize_country_value(
        str(
            address.get("addressCountry", "")
            or value.get("addressCountry", "")
            or ""
        )
    )
    return city, country


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
            description_html = str(node.get("description", "") or "")
            description_text = html_to_text(description_html)
            description_markdown = html_to_markdown(description_html)
            city, country = extract_structured_location(node.get("jobLocation"))
            applicant_country = extract_country_from_country_node(node.get("applicantLocationRequirements"))
            country = applicant_country or country
            return VacancySourceDetails(
                company=company,
                position=clean_text(str(node.get("title", "") or node.get("name", "") or "")),
                source_text=description_text,
                source_markdown=description_markdown,
                language=infer_language_from_text(description_text),
                country=country,
                city=city,
            )
    return VacancySourceDetails()


def derive_title_parts(raw_title: str) -> VacancySourceDetails:
    cleaned = clean_text(raw_title)
    hh_match = HH_TITLE_PATTERN.match(cleaned)
    if hh_match:
        return VacancySourceDetails(
            company=clean_text(hh_match.groupdict().get("company", "") or ""),
            position=clean_text(hh_match.groupdict().get("position", "") or ""),
            city=clean_text(hh_match.groupdict().get("city", "") or ""),
        )
    for pattern in TITLE_PATTERNS:
        match = pattern.match(cleaned)
        if match:
            return VacancySourceDetails(
                company=clean_text(match.groupdict().get("company", "") or ""),
                position=clean_text(match.groupdict().get("position", "") or ""),
            )
    return VacancySourceDetails(position=cleaned)


def infer_company_from_branding_text(text: str) -> str:
    cleaned_text = clean_multiline_text(text)
    if not cleaned_text:
        return ""
    for pattern in GENERIC_COMPANY_TEXT_PATTERNS:
        match = pattern.search(cleaned_text)
        if not match:
            continue
        candidate = cleanup_company_candidate(match.groupdict().get("company", "") or "")
        if is_plausible_company_name(candidate):
            return candidate
    return ""


def infer_company_from_social_links(html: str) -> str:
    match = re.search(r"https?://(?:[\w.-]+\.)?linkedin\.com/company/([A-Za-z0-9-]+)/?", html, flags=re.IGNORECASE)
    if not match:
        return ""
    slug = match.group(1).strip("-")
    if not slug:
        return ""
    candidate = cleanup_company_candidate(" ".join(part.capitalize() for part in slug.split("-") if part))
    return candidate if is_plausible_company_name(candidate) else ""


def infer_company_from_host(source_url: str) -> str:
    host = urlparse(source_url).netloc.lower()
    if not host:
        return ""
    labels = [
        label
        for label in host.split(".")
        if label and label not in {"www", "career", "careers", "job", "jobs", "vacancy", "vacancies"}
    ]
    if not labels:
        return ""
    candidate = cleanup_company_candidate(" ".join(part.capitalize() for part in labels[0].split("-") if part))
    return candidate if is_plausible_company_name(candidate) else ""


def infer_generic_company(parser: VacancyPageParser, html: str, source_url: str, text: str) -> str:
    meta_candidates = (
        parser.meta.get("application-name", ""),
        parser.meta.get("og:site_name", ""),
        parser.meta.get("apple-mobile-web-app-title", ""),
    )
    for candidate in meta_candidates:
        candidate = cleanup_company_candidate(candidate)
        if is_plausible_company_name(candidate):
            return candidate

    combined_text = "\n".join(
        part
        for part in (
            parser.meta.get("og:title", ""),
            parser.title,
            parser.h1,
            parser.meta.get("description", ""),
            parser.meta.get("og:description", ""),
            text,
        )
        if part
    )
    for candidate in (
        infer_company_from_branding_text(combined_text),
        infer_company_from_social_links(html),
        infer_company_from_host(source_url),
    ):
        if is_plausible_company_name(candidate):
            return cleanup_company_candidate(candidate)
    return ""


def extract_hh_global_var(html: str, name: str) -> str:
    match = re.search(rf'{re.escape(name)}:\s*"([^"]+)"', html)
    return clean_text(match.group(1)) if match else ""


def extract_hh_text_by_qa(html: str, data_qa: str) -> str:
    match = re.search(rf'data-qa="{re.escape(data_qa)}"[^>]*>(.*?)</(?:p|div|span)>', html, flags=re.S)
    return html_to_text(match.group(1)) if match else ""


def extract_hh_description_html(html: str) -> str:
    parser = HHDescriptionParser()
    parser.feed(html)
    return parser.get_html()


def extract_hh_skills(html: str) -> list[str]:
    skills = re.findall(
        r'data-qa="skills-element"[^>]*>.*?<div[^>]*magritte-tag__label[^>]*>(.*?)</div>',
        html,
        flags=re.S,
    )
    cleaned = [clean_text(skill) for skill in skills if clean_text(skill)]
    return list(dict.fromkeys(cleaned))


def extract_hh_city_from_meta(description: str) -> str:
    cleaned = clean_text(description)
    match = re.search(r"\.\s*([^.]+)\.\s*\u0422\u0440\u0435\u0431\u0443\u0435\u043c\u044b\u0439 \u043e\u043f\u044b\u0442:", cleaned)
    if match:
        return clean_text(match.group(1))
    return ""


def infer_country_from_text(text: str) -> str:
    return infer_country_name_from_text(clean_multiline_text(text))


def resolve_hh_country(
    *,
    structured_country: str = "",
    city: str = "",
    text: str = "",
    country_id: str = "",
    area_country: str = "",
) -> str:
    normalized_structured_country = normalize_country_value(structured_country)
    if normalized_structured_country:
        return normalized_structured_country
    text_country = infer_country_from_text(text)
    if text_country:
        return text_country
    normalized_area_country = normalize_country_value(area_country)
    if normalized_area_country:
        return normalized_area_country
    return resolve_country_name_from_hh_id(clean_text(country_id))


def build_enriched_source_text(
    description: str,
    key_skills: list[str],
    employment_type: str,
    work_schedule: str,
    work_mode: str,
) -> str:
    sections: list[str] = []
    if description.strip():
        sections.append(clean_multiline_text(description))
    details: list[str] = []
    if employment_type:
        details.append(f"\u0417\u0430\u043d\u044f\u0442\u043e\u0441\u0442\u044c: {employment_type}")
    if work_schedule:
        details.append(f"\u0413\u0440\u0430\u0444\u0438\u043a: {work_schedule}")
    if work_mode:
        details.append(f"\u0424\u043e\u0440\u043c\u0430\u0442 \u0440\u0430\u0431\u043e\u0442\u044b: {work_mode}")
    if details:
        sections.append("\n".join(details))
    if key_skills:
        sections.append(
            "\u041a\u043b\u044e\u0447\u0435\u0432\u044b\u0435 \u043d\u0430\u0432\u044b\u043a\u0438:\n" + "\n".join(f"- {skill}" for skill in key_skills)
        )
    return "\n\n".join(section for section in sections if section.strip()).strip()


def build_enriched_source_markdown(description_markdown: str, key_skills: list[str]) -> str:
    sections: list[str] = []
    normalized_description = normalize_embedded_markdown_headings(description_markdown.strip())
    if normalized_description:
        sections.append(normalized_description)
    has_skills_heading = bool(re.search(r"(?m)^#{1,6}\s+Ключевые навыки\s*$", normalized_description))
    if key_skills and not has_skills_heading:
        sections.append("### Ключевые навыки\n" + "\n".join(f"- {skill}" for skill in key_skills))
    return "\n\n".join(section for section in sections if section.strip()).strip()


def parse_hh_vacancy_page(html: str) -> VacancySourceDetails:
    page = VacancyPageParser()
    page.feed(html)
    structured = parse_structured_job_posting(page.json_ld_chunks)

    title_parts = derive_title_parts(page.meta.get("og:title") or page.title or page.h1)
    city_from_meta = extract_hh_city_from_meta(page.meta.get("description", "") or page.meta.get("og:description", ""))
    description_html = extract_hh_description_html(html)
    description_markdown = html_to_markdown(description_html) if description_html else ""
    description_text = html_to_text(description_html) if description_html else ""

    employment_type = strip_value_label(extract_hh_text_by_qa(html, "common-employment-text"))
    work_schedule = strip_value_label(extract_hh_text_by_qa(html, "work-schedule-by-days-text"))
    work_mode = strip_value_label(extract_hh_text_by_qa(html, "work-formats-text"))
    key_skills = extract_hh_skills(html)
    country_id = extract_hh_global_var(html, "country")
    country = resolve_hh_country(
        structured_country=structured.country,
        city=structured.city or city_from_meta or title_parts.city,
        text="\n".join(
            part
            for part in [
                page.meta.get("description", "") or page.meta.get("og:description", ""),
                page.title,
                page.h1,
                description_text,
            ]
            if part
        ),
        country_id=country_id,
    )

    return VacancySourceDetails(
        company=structured.company or title_parts.company or derive_title_parts(page.h1).company,
        position=page.h1 or structured.position or title_parts.position,
        source_text=build_enriched_source_text(description_text, key_skills, employment_type, work_schedule, work_mode),
        source_markdown=build_enriched_source_markdown(description_markdown, key_skills),
        language=normalize_language_tag(page.html_lang) or structured.language or infer_language_from_text(description_text),
        source_channel="HeadHunter",
        country=country,
        city=structured.city or city_from_meta or title_parts.city,
        work_mode=work_mode,
        employment_type=employment_type,
        work_schedule=work_schedule,
        key_skills=key_skills,
    )


def infer_work_mode_from_text(text: str) -> str:
    lower = clean_multiline_text(text).lower()
    if "\u0443\u0434\u0430\u043b" in lower or "remote" in lower:
        return "\u0443\u0434\u0430\u043b\u0451\u043d\u043d\u043e"
    if "\u0433\u0438\u0431\u0440\u0438\u0434" in lower or "hybrid" in lower:
        return "\u0433\u0438\u0431\u0440\u0438\u0434"
    if "\u043e\u0444\u0438\u0441" in lower or "office" in lower:
        return "\u043e\u0444\u0438\u0441"
    return ""


def parse_generic_vacancy_page(html: str, source_url: str = "") -> VacancySourceDetails:
    parser = VacancyPageParser()
    parser.feed(html)
    structured = parse_structured_job_posting(parser.json_ld_chunks)
    title_parts = derive_title_parts(parser.meta.get("og:title") or parser.title or parser.h1)

    meta_summary = clean_multiline_text(parser.meta.get("description", "") or parser.meta.get("og:description", ""))
    primary_html = extract_primary_content_html(html)
    extraction_html = primary_html or html
    body_text = html_to_text(extraction_html)
    body_markdown = html_to_markdown(extraction_html)

    source_text = structured.source_text
    if not source_text:
        source_text = choose_preferred_page_text(meta_summary, body_text)
    source_text = strip_generic_ui_noise(source_text)

    source_markdown = structured.source_markdown
    if not source_markdown:
        preferred_text = choose_preferred_page_text(meta_summary, body_text)
        if preferred_text == meta_summary:
            source_markdown = meta_summary
        else:
            source_markdown = body_markdown
    source_markdown = strip_generic_ui_noise(source_markdown)
    company = structured.company or title_parts.company or infer_generic_company(parser, html, source_url, source_text or body_text)

    return VacancySourceDetails(
        company=company,
        position=structured.position or parser.h1 or title_parts.position,
        source_text=source_text,
        source_markdown=source_markdown,
        language=normalize_language_tag(parser.html_lang) or structured.language or infer_language_from_text(source_text),
        source_channel=infer_source_channel(source_url, source_text),
        country=structured.country,
        city=structured.city or title_parts.city,
        work_mode=infer_work_mode_from_text(source_text),
        key_skills=[],
    )


def looks_like_js_heavy_html(html: str) -> bool:
    lower = html.lower()
    return any(
        token in lower
        for token in (
            "__next_data__",
            "__nuxt",
            "window.__initial_state__",
            "window.__apollo_state__",
            "webpack",
            "framer",
            "data-reactroot",
            "application/ld+json",
        )
    )


def should_use_playwright_fallback(html: str, details: VacancySourceDetails) -> bool:
    source_text = clean_multiline_text(details.source_text)
    if not source_text:
        return True
    if looks_like_truncated_summary(source_text):
        return True
    if len(source_text) < 400 and looks_like_js_heavy_html(html):
        return True
    if len(source_text) < 250:
        return True
    if not details.company.strip() or not details.position.strip():
        return True
    return False


def fetch_source_details(source_url: str) -> VacancySourceDetails:
    vacancy_id = parse_hh_vacancy_url(source_url)
    html = ""
    if vacancy_id:
        try:
            payload = fetch_url(f"https://api.hh.ru/vacancies/{vacancy_id}", accept="application/json")
            details = parse_hh_vacancy_payload(payload)
            html = fetch_url(source_url, accept="text/html,application/xhtml+xml")
            html_details = parse_hh_vacancy_page(html)
            return merge_source_details(details, html_details, source_url)
        except Exception:
            pass
        if not html:
            html = fetch_url(source_url, accept="text/html,application/xhtml+xml")
        return parse_hh_vacancy_page(html)
    html = fetch_url(source_url, accept="text/html,application/xhtml+xml")
    details = parse_generic_vacancy_page(html, source_url)
    if should_use_playwright_fallback(html, details):
        try:
            rendered_page = render_page_with_playwright(source_url)
            rendered_details = parse_generic_vacancy_page(rendered_page.html, rendered_page.url or source_url)
            return merge_source_details(details, rendered_details, rendered_page.url or source_url)
        except Exception:
            pass
    return details


def merge_source_details(base: VacancySourceDetails, overlay: VacancySourceDetails, source_url: str) -> VacancySourceDetails:
    key_skills = overlay.key_skills or base.key_skills
    description_text = overlay.source_text or base.source_text
    description_markdown = overlay.source_markdown or base.source_markdown or description_text
    if key_skills and "\u041a\u043b\u044e\u0447\u0435\u0432\u044b\u0435 \u043d\u0430\u0432\u044b\u043a\u0438" not in description_text:
        description_text = build_enriched_source_text(
            overlay.source_text or base.source_text,
            key_skills,
            overlay.employment_type or base.employment_type,
            overlay.work_schedule or base.work_schedule,
            overlay.work_mode or base.work_mode,
        )
    if key_skills and "\u041a\u043b\u044e\u0447\u0435\u0432\u044b\u0435 \u043d\u0430\u0432\u044b\u043a\u0438" not in description_markdown:
        description_markdown = build_enriched_source_markdown(description_markdown, key_skills)
    return VacancySourceDetails(
        company=overlay.company or base.company,
        position=overlay.position or base.position,
        source_text=description_text,
        source_markdown=description_markdown,
        language=overlay.language or base.language,
        source_channel=overlay.source_channel or base.source_channel or infer_source_channel(source_url, description_text),
        country=overlay.country or base.country,
        city=overlay.city or base.city,
        work_mode=overlay.work_mode or base.work_mode,
        employment_type=overlay.employment_type or base.employment_type,
        work_schedule=overlay.work_schedule or base.work_schedule,
        key_skills=key_skills,
    )


def enrich_request(request: "IngestVacancyRequest") -> "IngestVacancyRequest":
    source_markdown = request.source_markdown.strip() or request.source_text.strip()
    if source_markdown:
        source_markdown = build_enriched_source_markdown(source_markdown, request.key_skills)
    source_channel = infer_source_channel(request.source_url, request.source_text, request.source_channel)
    request = replace(request, source_markdown=source_markdown, source_channel=source_channel)

    if not request.source_url.strip():
        if is_unspecified(request.country):
            request = replace(request, country="")
        if is_unspecified(request.work_mode):
            request = replace(request, work_mode="")
        return request

    needs_enrichment = (
        not request.company.strip()
        or not request.position.strip()
        or not request.source_text.strip()
        or is_unspecified(request.country)
        or is_unspecified(request.work_mode)
        or not request.key_skills
    )
    if not needs_enrichment:
        return request
    try:
        details = fetch_source_details(request.source_url.strip())
    except Exception as exc:
        missing_required = [name for name, value in (("company", request.company), ("position", request.position)) if not value.strip()]
        if missing_required:
            missing = ", ".join(missing_required)
            raise ValueError(
                f"Failed to fetch vacancy details from source_url {request.source_url.strip()}: {exc}. "
                f"Missing required fields: {missing}. Provide them manually or retry with a reachable URL."
            ) from exc
        return request

    language = request.language
    if not language.strip() and details.language:
        language = details.language

    country = request.country
    if is_unspecified(country):
        country = details.country

    work_mode = request.work_mode
    if is_unspecified(work_mode):
        work_mode = details.work_mode

    key_skills = request.key_skills or details.key_skills
    if request.source_markdown.strip():
        source_markdown = build_enriched_source_markdown(request.source_markdown.strip(), key_skills)
    elif details.source_markdown.strip():
        source_markdown = build_enriched_source_markdown(details.source_markdown.strip(), key_skills)
    else:
        source_markdown = build_enriched_source_markdown(details.source_text, key_skills)

    return replace(
        request,
        company=request.company.strip() or details.company,
        position=request.position.strip() or details.position,
        source_text=request.source_text.strip() or details.source_text,
        source_markdown=source_markdown,
        language=language,
        source_channel=request.source_channel.strip() or details.source_channel or infer_source_channel(request.source_url, details.source_text),
        country=country,
        city=request.city.strip() or details.city,
        work_mode=work_mode,
        employment_type=request.employment_type.strip() or details.employment_type,
        work_schedule=request.work_schedule.strip() or details.work_schedule,
        key_skills=key_skills,
    )


@dataclass
class IngestVacancyRequest:
    company: str = ""
    position: str = ""
    source_text: str = ""
    source_markdown: str = ""
    source_url: str = ""
    source_channel: str = ""
    source_type: str = ""
    language: str = ""
    country: str = ""
    city: str = ""
    work_mode: str = ""
    employment_type: str = ""
    work_schedule: str = ""
    key_skills: list[str] = field(default_factory=list)
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
        response_monitoring_path = layout.root / "response-monitoring.xlsx"
        excel_row = append_ingest_record(response_monitoring_path, build_response_monitoring_record(request, vacancy_id))
        meta_payload = load_simple_yaml(meta_path)
        meta_payload["excel_row"] = excel_row
        write_simple_yaml(meta_path, meta_payload)

        artifacts = [str(meta_path), str(source_path), str(analysis_path), str(adoptions_path), str(response_monitoring_path)]
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

    def _render_meta(self, request: IngestVacancyRequest, vacancy_id: str, timestamp: str, excel_row: int | None = None) -> str:
        country = request.country.strip() or "\u041d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d\u043e"
        work_mode = request.work_mode.strip() or "\u041d\u0435 \u0443\u043a\u0430\u0437\u0430\u043d\u043e"
        source_channel = request.source_channel.strip() or infer_source_channel(request.source_url, request.source_text)
        return "\n".join(
            [
                f"vacancy_id: {vacancy_id}",
                f"source_type: {request.normalized_source_type()}",
                f"source_url: {request.source_url or 'null'}",
                f"source_channel: {source_channel}",
                f"company: {request.company}",
                f"position: {request.position}",
                f"language: {request.language}",
                f"country: {country}",
                f"work_mode: {work_mode}",
                'is_active: "\u0414\u0430"',
                f"ingested_at: {timestamp}",
                "selected_resume: undecided",
                f"target_mode: {request.target_mode}",
                f"include_employer_channels: {str(request.include_employer_channels).lower()}",
                f"excel_row: {excel_row if excel_row is not None else 'null'}",
                "status: ingested",
                'notes: ""',
                "",
            ]
        )

    def _render_source(self, request: IngestVacancyRequest, vacancy_id: str) -> str:
        def display_value(value: str) -> str:
            cleaned = value.strip()
            return "нет данных" if is_unspecified(cleaned) else cleaned

        source_channel = request.source_channel or infer_source_channel(request.source_url, request.source_text)
        lines = [
            "# \u0418\u0441\u0442\u043e\u0447\u043d\u0438\u043a \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u0438",
            "",
            "## \u041f\u0430\u0441\u043f\u043e\u0440\u0442",
            "",
            f"- \u041a\u043e\u043c\u043f\u0430\u043d\u0438\u044f: {display_value(request.company)}",
            f"- \u041f\u043e\u0437\u0438\u0446\u0438\u044f: {display_value(request.position)}",
            f"- ID \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u0438: {vacancy_id}",
            f"- \u0418\u0441\u0445\u043e\u0434\u043d\u0430\u044f \u0441\u0441\u044b\u043b\u043a\u0430: {display_value(request.source_url)}",
            f"- \u0418\u0441\u0442\u043e\u0447\u043d\u0438\u043a: {display_value(source_channel)}",
            "",
            "## \u041f\u0430\u0440\u0430\u043c\u0435\u0442\u0440\u044b \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u0438",
            "",
        ]

        params = [
            ("\u0421\u0442\u0440\u0430\u043d\u0430", request.country),
            ("\u0413\u043e\u0440\u043e\u0434", request.city),
            ("\u0417\u0430\u043d\u044f\u0442\u043e\u0441\u0442\u044c", request.employment_type),
            ("\u0413\u0440\u0430\u0444\u0438\u043a", request.work_schedule),
            ("\u0424\u043e\u0440\u043c\u0430\u0442 \u0440\u0430\u0431\u043e\u0442\u044b", request.work_mode),
        ]
        lines.extend([f"- {label}: {display_value(value)}" for label, value in params])

        lines.extend(["", "## \u0418\u0441\u0445\u043e\u0434\u043d\u044b\u0439 \u0442\u0435\u043a\u0441\u0442", ""])
        if request.source_markdown.strip():
            lines.append(request.source_markdown.strip())
        elif request.source_text.strip():
            lines.append(request.source_text.strip())
        else:
            lines.append("<!-- \u0412\u0441\u0442\u0430\u0432\u044c \u0441\u044e\u0434\u0430 \u0438\u0441\u0445\u043e\u0434\u043d\u044b\u0439 \u0442\u0435\u043a\u0441\u0442 \u0432\u0430\u043a\u0430\u043d\u0441\u0438\u0438 \u0431\u0435\u0437 \u0438\u043d\u0442\u0435\u0440\u043f\u0440\u0435\u0442\u0430\u0446\u0438\u0438. -->")
        lines.append("")
        return "\n".join(lines)

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
