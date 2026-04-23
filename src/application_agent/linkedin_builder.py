from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from application_agent.master_rebuild import ensure_trailing_newline, normalize_newlines
from application_agent.review_state import normalize_text

CHECK_PREFIX = "CHECK:"
GAP_PREFIX = "GAP:"
OPTIONAL_PREFIX = "OPTIONAL:"
CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
LINKEDIN_RE = re.compile(r"https?://(?:[\w.-]+\.)?linkedin\.com/[^\s)>]+", re.IGNORECASE)
H2_RE = re.compile(r"^##\s+(?P<title>.+?)\s*$", re.MULTILINE)
H3_RE = re.compile(r"^###\s+(?P<title>.+?)\s*$", re.MULTILINE)
ABOUT_ALIASES = ("о себе", "about")
HIGHLIGHT_ALIASES = ("ключевые акценты", "ключевые достижения", "опыт работы")
SKILL_ALIASES = ("ключевые компетенции", "технологии и инструменты", "skills")


@dataclass(frozen=True)
class LinkedInTopCard:
    name: str
    headline: str
    current_position: str
    location: str
    public_linkedin: str


@dataclass(frozen=True)
class LinkedInCopyPack:
    language: str
    top_card: LinkedInTopCard
    about: str
    experience_highlights: tuple[str, ...]
    skills: tuple[str, ...]


@dataclass(frozen=True)
class FillingGuideEntry:
    section: str
    paste_this: str
    optional: str
    check_before_publishing: str


@dataclass(frozen=True)
class BuildLinkedInComputation:
    artifact_markdown: str
    changed: bool
    target_role: str
    executive_summary: tuple[str, ...]
    ru_pack: LinkedInCopyPack
    en_pack: LinkedInCopyPack
    filling_guide: tuple[FillingGuideEntry, ...]
    gaps: tuple[str, ...]


def apply_build_linkedin_projection(
    *,
    target_role: str,
    master_path: Path,
    role_resume_path: Path,
    profile_metadata_path: Path,
    output_path: Path,
) -> BuildLinkedInComputation:
    if not master_path.exists():
        raise FileNotFoundError(f"MASTER resume is missing: {master_path}")
    if not role_resume_path.exists():
        raise FileNotFoundError(f"Role resume is missing: {role_resume_path}")

    profile_metadata_text = profile_metadata_path.read_text(encoding="utf-8") if profile_metadata_path.exists() else ""
    existing_artifact_text = output_path.read_text(encoding="utf-8") if output_path.exists() else ""
    computation = compute_build_linkedin_projection(
        target_role=target_role,
        master_text=master_path.read_text(encoding="utf-8"),
        role_resume_text=role_resume_path.read_text(encoding="utf-8"),
        profile_metadata_text=profile_metadata_text,
        existing_artifact_text=existing_artifact_text,
    )

    if computation.changed:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(computation.artifact_markdown, encoding="utf-8", newline="\n")

    return computation


def compute_build_linkedin_projection(
    *,
    target_role: str,
    master_text: str,
    role_resume_text: str,
    profile_metadata_text: str = "",
    existing_artifact_text: str = "",
) -> BuildLinkedInComputation:
    normalized_target_role = normalize_text(target_role)
    if not normalized_target_role:
        raise ValueError("Target role is required for build-linkedin.")

    normalized_master = normalize_newlines(master_text)
    normalized_role_resume = normalize_newlines(role_resume_text)
    master_scalar_map = extract_front_matter_scalar_map(normalized_master)
    profile_scalar_map = load_nested_scalar_map(profile_metadata_text)
    surface_map = dict(master_scalar_map)
    surface_map.update(profile_scalar_map)

    master_body = strip_front_matter(normalized_master)
    role_resume_body = strip_front_matter(normalized_role_resume)
    role_name_fallback, role_title = extract_resume_identity(role_resume_body)
    master_name_fallback, _ = extract_resume_identity(master_body)

    ru_name = resolve_ru_name(surface_map, role_name_fallback, master_name_fallback)
    en_name = resolve_en_name(surface_map, role_name_fallback, master_name_fallback)
    ru_location = resolve_ru_location(surface_map, role_resume_body, master_body)
    en_location = resolve_en_location(surface_map, role_resume_body, master_body)
    public_linkedin = resolve_public_linkedin(surface_map, role_resume_body, master_body)
    current_position_ru = resolve_current_position_ru(role_resume_body, master_body)
    current_position_en = resolve_current_position_en(current_position_ru)

    about_ru_source = extract_first_matching_section(role_resume_body, ABOUT_ALIASES) or extract_first_matching_section(
        master_body, ABOUT_ALIASES
    )
    about_ru = about_ru_source or f"{GAP_PREFIX} About section is missing in the current resume inputs."
    about_en = resolve_english_copy(
        source_text=about_ru,
        missing_message="English About copy is missing in the current inputs.",
        translate_message="Prepare English About from the approved RU source below without adding new facts.",
    )

    ru_highlights = merge_unique_strings(
        extract_highlight_bullets(role_resume_body, limit=4) + extract_highlight_bullets(master_body, limit=4)
    )
    if not ru_highlights:
        ru_highlights = (f"{GAP_PREFIX} no factual experience bullets were found in MASTER or the role resume.",)
    en_highlights = tuple(render_english_list_item(item) for item in ru_highlights)

    ru_skills = merge_unique_strings(
        extract_skill_entries(role_resume_body, limit=10) + extract_skill_entries(master_body, limit=10)
    )
    if not ru_skills:
        ru_skills = (f"{CHECK_PREFIX} curate the skills section from the approved resume inputs before publishing.",)
    en_skills = tuple(render_english_list_item(item) for item in ru_skills)

    ru_pack = LinkedInCopyPack(
        language="RU",
        top_card=LinkedInTopCard(
            name=ru_name,
            headline=role_title or normalized_target_role,
            current_position=current_position_ru,
            location=ru_location,
            public_linkedin=public_linkedin,
        ),
        about=about_ru,
        experience_highlights=ru_highlights,
        skills=ru_skills,
    )
    en_pack = LinkedInCopyPack(
        language="EN",
        top_card=LinkedInTopCard(
            name=en_name,
            headline=normalized_target_role,
            current_position=current_position_en,
            location=en_location,
            public_linkedin=public_linkedin,
        ),
        about=about_en,
        experience_highlights=en_highlights,
        skills=en_skills,
    )

    private_contacts = resolve_private_contacts(surface_map, role_resume_body, master_body)
    executive_summary = build_executive_summary(
        target_role=normalized_target_role,
        role_title=role_title or normalized_target_role,
        profile_metadata_present=bool(profile_metadata_text.strip()),
    )
    filling_guide = build_filling_guide(
        ru_pack=ru_pack,
        en_pack=en_pack,
        private_contacts=private_contacts,
    )
    gaps = build_gap_list(
        profile_metadata_present=bool(profile_metadata_text.strip()),
        ru_pack=ru_pack,
        en_pack=en_pack,
    )
    artifact_markdown = render_build_linkedin_artifact(
        target_role=normalized_target_role,
        executive_summary=executive_summary,
        ru_pack=ru_pack,
        en_pack=en_pack,
        filling_guide=filling_guide,
        gaps=gaps,
    )
    normalized_existing = normalize_newlines(existing_artifact_text) if existing_artifact_text else ""
    changed = artifact_markdown != normalized_existing

    return BuildLinkedInComputation(
        artifact_markdown=artifact_markdown,
        changed=changed,
        target_role=normalized_target_role,
        executive_summary=executive_summary,
        ru_pack=ru_pack,
        en_pack=en_pack,
        filling_guide=filling_guide,
        gaps=gaps,
    )


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
    return normalize_text(stripped)


def extract_resume_identity(markdown: str) -> tuple[str, str]:
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line.startswith("# "):
            continue
        value = normalize_text(line[2:])
        parts = re.split(r"\s+[—-]\s+", value, maxsplit=1)
        if len(parts) == 2:
            return (normalize_text(parts[0]), normalize_text(parts[1]))
        return ("", value)
    return ("", "")


def resolve_ru_name(surface_map: dict[str, str], *fallbacks: str) -> str:
    value = pick_localized_value(surface_map, ("public_name", "full_name", "name"), ("ru", "kz"))
    return value or first_non_empty(*fallbacks) or f"{CHECK_PREFIX} confirm the public display name."


def resolve_en_name(surface_map: dict[str, str], *fallbacks: str) -> str:
    value = pick_localized_value(surface_map, ("public_name", "full_name", "name"), ("eu", "en"))
    if value:
        return value
    fallback = first_non_empty(*fallbacks)
    if fallback and not contains_cyrillic(fallback):
        return fallback
    return f"{CHECK_PREFIX} English public name variant is missing in the current inputs."


def resolve_ru_location(surface_map: dict[str, str], role_resume_body: str, master_body: str) -> str:
    value = pick_localized_value(surface_map, ("public_location", "location"), ("ru", "kz"))
    return value or extract_location_from_markdown(role_resume_body) or extract_location_from_markdown(master_body) or (
        f"{CHECK_PREFIX} confirm the public location."
    )


def resolve_en_location(surface_map: dict[str, str], role_resume_body: str, master_body: str) -> str:
    value = pick_localized_value(surface_map, ("public_location", "location"), ("eu", "en"))
    if value:
        return value
    fallback = extract_location_from_markdown(role_resume_body) or extract_location_from_markdown(master_body)
    if fallback and not contains_cyrillic(fallback):
        return fallback
    return f"{CHECK_PREFIX} English location variant is missing in the current inputs."


def resolve_public_linkedin(surface_map: dict[str, str], role_resume_body: str, master_body: str) -> str:
    value = first_non_empty(
        surface_map.get("public_links.linkedin"),
        surface_map.get("links.linkedin"),
        surface_map.get("public.linkedin"),
        surface_map.get("linkedin"),
        surface_map.get("linkedin_url"),
        extract_linkedin_from_markdown(role_resume_body),
        extract_linkedin_from_markdown(master_body),
    )
    return value or f"{OPTIONAL_PREFIX} add the public LinkedIn URL after the profile is created."


def resolve_current_position_ru(role_resume_body: str, master_body: str) -> str:
    return extract_current_position(role_resume_body) or extract_current_position(master_body) or (
        f"{CHECK_PREFIX} confirm the current position line from the latest experience entry."
    )


def resolve_current_position_en(current_position_ru: str) -> str:
    if is_marker_value(current_position_ru):
        return current_position_ru
    if not contains_cyrillic(current_position_ru):
        return current_position_ru
    return f"{CHECK_PREFIX} translate the current position line from the approved RU source: {current_position_ru}"


def resolve_private_contacts(surface_map: dict[str, str], role_resume_body: str, master_body: str) -> dict[str, str]:
    return {
        "email": first_non_empty(
            pick_localized_value(surface_map, ("contacts.email", "email"), ("eu", "en", "ru", "kz")),
            extract_email_from_markdown(role_resume_body),
            extract_email_from_markdown(master_body),
        ),
        "phone": first_non_empty(
            pick_localized_value(surface_map, ("contacts.phone", "phone"), ("eu", "en", "ru", "kz")),
            extract_labeled_contact(role_resume_body, "телефон"),
            extract_labeled_contact(master_body, "телефон"),
        ),
        "telegram": first_non_empty(
            surface_map.get("contacts.telegram"),
            surface_map.get("telegram"),
            extract_telegram_from_markdown(role_resume_body),
            extract_telegram_from_markdown(master_body),
        ),
        "whatsapp": first_non_empty(
            pick_localized_value(surface_map, ("contacts.whatsapp", "whatsapp"), ("eu", "en", "ru", "kz")),
            extract_labeled_contact(role_resume_body, "whatsapp"),
            extract_labeled_contact(master_body, "whatsapp"),
        ),
    }


def build_executive_summary(*, target_role: str, role_title: str, profile_metadata_present: bool) -> tuple[str, ...]:
    metadata_source = "`profile/contact-regions.yml`" if profile_metadata_present else "resume fallbacks only"
    return (
        f"Primary positioning target: {target_role}.",
        f"Default RU headline stays at the approved role title: {role_title}.",
        "Factual source of truth: `resumes/MASTER.md`; positioning overlay: the selected role resume.",
        f"Public profile surface source: {metadata_source}.",
        "Private contacts stay in the filling guide only and are never auto-promoted into public copy blocks.",
    )


def build_filling_guide(
    *,
    ru_pack: LinkedInCopyPack,
    en_pack: LinkedInCopyPack,
    private_contacts: dict[str, str],
) -> tuple[FillingGuideEntry, ...]:
    return (
        FillingGuideEntry(
            section="Name",
            paste_this=f"RU: {ru_pack.top_card.name}\nEN: {en_pack.top_card.name}",
            optional="none",
            check_before_publishing="Confirm that the public spelling matches the profile owner preference.",
        ),
        FillingGuideEntry(
            section="Headline",
            paste_this=f"RU: {ru_pack.top_card.headline}\nEN: {en_pack.top_card.headline}",
            optional="Choose one language for the public profile.",
            check_before_publishing="Keep the headline aligned with the selected target role and avoid adding new claims.",
        ),
        FillingGuideEntry(
            section="Current Position",
            paste_this=f"RU: {ru_pack.top_card.current_position}\nEN: {en_pack.top_card.current_position}",
            optional="none",
            check_before_publishing="Validate the title/company formatting against the latest role entry before publishing.",
        ),
        FillingGuideEntry(
            section="Location",
            paste_this=f"RU: {ru_pack.top_card.location}\nEN: {en_pack.top_card.location}",
            optional="none",
            check_before_publishing="Confirm the public location and relocation wording for the selected market.",
        ),
        FillingGuideEntry(
            section="Public LinkedIn URL",
            paste_this=ru_pack.top_card.public_linkedin,
            optional="Skip until the profile URL is finalized.",
            check_before_publishing="Use only the final public profile link; do not expose private channels here.",
        ),
        FillingGuideEntry(
            section="About",
            paste_this=f"RU:\n{ru_pack.about}\n\nEN:\n{en_pack.about}",
            optional="Use the RU or EN block that matches the public profile language.",
            check_before_publishing="If a block is marked CHECK, translate or confirm it manually without adding facts.",
        ),
        FillingGuideEntry(
            section="Experience",
            paste_this="RU:\n" + "\n".join(f"- {item}" for item in ru_pack.experience_highlights) + "\n\nEN:\n"
            + "\n".join(f"- {item}" for item in en_pack.experience_highlights),
            optional="Trim the list to the strongest 4-8 bullets per role if LinkedIn length becomes a problem.",
            check_before_publishing="Keep dates and employment facts unchanged from the resume inputs.",
        ),
        FillingGuideEntry(
            section="Skills",
            paste_this="RU:\n" + "\n".join(f"- {item}" for item in ru_pack.skills) + "\n\nEN:\n"
            + "\n".join(f"- {item}" for item in en_pack.skills),
            optional="Pin only the skills that match the chosen target role.",
            check_before_publishing="Remove duplicates and any skill that cannot be defended from the current resume inputs.",
        ),
        FillingGuideEntry(
            section="Private Email",
            paste_this=format_private_contact(private_contacts.get("email")),
            optional="Leave blank if the email should stay private.",
            check_before_publishing="Do not expose a private email unless the owner explicitly approves it.",
        ),
        FillingGuideEntry(
            section="Private Phone",
            paste_this=format_private_contact(private_contacts.get("phone")),
            optional="Leave blank if the phone should stay private.",
            check_before_publishing="Do not expose a private phone number unless the owner explicitly approves it.",
        ),
        FillingGuideEntry(
            section="Telegram",
            paste_this=format_private_contact(private_contacts.get("telegram")),
            optional="Leave blank if Telegram should stay private.",
            check_before_publishing="Confirm whether Telegram belongs in the public profile at all.",
        ),
        FillingGuideEntry(
            section="WhatsApp",
            paste_this=format_private_contact(private_contacts.get("whatsapp")),
            optional="Leave blank if WhatsApp should stay private.",
            check_before_publishing="Confirm whether WhatsApp belongs in the public profile at all.",
        ),
    )


def build_gap_list(
    *,
    profile_metadata_present: bool,
    ru_pack: LinkedInCopyPack,
    en_pack: LinkedInCopyPack,
) -> tuple[str, ...]:
    gaps: list[str] = []
    if not profile_metadata_present:
        gaps.append(f"{CHECK_PREFIX} profile/contact-regions.yml is missing; public profile surface falls back to resume inputs only.")
    for value in (
        en_pack.top_card.name,
        ru_pack.top_card.location,
        en_pack.top_card.location,
        ru_pack.top_card.current_position,
        en_pack.top_card.current_position,
        ru_pack.about,
    ):
        if value.startswith((CHECK_PREFIX, GAP_PREFIX)):
            gaps.append(value)
    if contains_cyrillic(ru_pack.about):
        gaps.append(f"{CHECK_PREFIX} English narrative copy is missing in the current inputs; translate the approved RU sections before publishing.")
    for item in ru_pack.experience_highlights:
        if item.startswith((CHECK_PREFIX, GAP_PREFIX)):
            gaps.append(item)
    return tuple(dedupe_preserve_order(gaps) or [f"{OPTIONAL_PREFIX} no blocking data gaps were detected for the current deterministic draft."])


def render_build_linkedin_artifact(
    *,
    target_role: str,
    executive_summary: tuple[str, ...],
    ru_pack: LinkedInCopyPack,
    en_pack: LinkedInCopyPack,
    filling_guide: tuple[FillingGuideEntry, ...],
    gaps: tuple[str, ...],
) -> str:
    lines = [
        f"# LinkedIn Draft Pack for {target_role}",
        "",
        "## Executive Summary",
        "",
        *[f"- {item}" for item in executive_summary],
        "",
        "## Ready-to-Paste RU Pack",
        "",
        *render_copy_pack(ru_pack),
        "",
        "## Ready-to-Paste EN Pack",
        "",
        *render_copy_pack(en_pack),
        "",
        "## Field-by-Field Filling Guide",
        "",
        *render_filling_guide(filling_guide),
        "",
        "## GAP List",
        "",
        *[f"- {item}" for item in gaps],
        "",
    ]
    return ensure_trailing_newline("\n".join(lines))


def render_copy_pack(pack: LinkedInCopyPack) -> list[str]:
    return [
        "### Intro / Top Card",
        "",
        f"- Name: {pack.top_card.name}",
        f"- Headline: {pack.top_card.headline}",
        f"- Current Position: {pack.top_card.current_position}",
        f"- Location: {pack.top_card.location}",
        f"- Public LinkedIn URL: {pack.top_card.public_linkedin}",
        "",
        "### About",
        "",
        pack.about,
        "",
        "### Experience Highlights",
        "",
        *[f"- {item}" for item in pack.experience_highlights],
        "",
        "### Skills",
        "",
        *[f"- {item}" for item in pack.skills],
    ]


def render_filling_guide(entries: tuple[FillingGuideEntry, ...]) -> list[str]:
    lines: list[str] = []
    for entry in entries:
        lines.extend(
            [
                f"### {entry.section}",
                "",
                "Paste this:",
                entry.paste_this,
                "",
                f"Optional: {entry.optional}",
                f"Check before publishing: {entry.check_before_publishing}",
                "",
            ]
        )
    if lines:
        lines.pop()
    return lines


def extract_first_matching_section(markdown: str, aliases: tuple[str, ...]) -> str:
    for alias in aliases:
        section = extract_h2_section(markdown, alias)
        if section:
            return section
    return ""


def extract_h2_section(markdown: str, alias: str) -> str:
    current_title = ""
    collected: list[str] = []
    capturing = False
    for raw_line in markdown.splitlines():
        match = H2_RE.match(raw_line.strip())
        if match:
            current_title = normalize_heading(match.group("title"))
            if capturing and alias not in current_title:
                break
            capturing = alias in current_title
            continue
        if capturing:
            collected.append(raw_line.rstrip())
    return ensure_trailing_newline("\n".join(trim_blank_lines(collected))).strip()


def extract_highlight_bullets(markdown: str, *, limit: int) -> tuple[str, ...]:
    values: list[str] = []
    for alias in HIGHLIGHT_ALIASES:
        section = extract_h2_section(markdown, alias)
        if not section:
            continue
        values.extend(extract_bullet_items(section))
        if len(values) >= limit:
            break
    return tuple(dedupe_preserve_order(values)[:limit])


def extract_skill_entries(markdown: str, *, limit: int) -> tuple[str, ...]:
    values: list[str] = []
    for alias in SKILL_ALIASES:
        section = extract_h2_section(markdown, alias)
        if not section:
            continue
        values.extend(extract_bullet_items(section))
        values.extend(extract_inline_markdown_values(section))
        if len(values) >= limit:
            break
    return tuple(dedupe_preserve_order(values)[:limit])


def extract_bullet_items(section: str) -> list[str]:
    values: list[str] = []
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line.startswith("- "):
            continue
        cleaned = clean_markdown_inline(line[2:])
        if cleaned:
            values.append(cleaned)
    return values


def extract_inline_markdown_values(section: str) -> list[str]:
    values: list[str] = []
    for raw_line in section.splitlines():
        line = clean_markdown_inline(raw_line)
        if ":" not in line:
            continue
        _, tail = line.split(":", maxsplit=1)
        for item in tail.split(","):
            cleaned = normalize_text(item)
            if cleaned:
                values.append(cleaned)
    return values


def extract_current_position(markdown: str) -> str:
    experience = extract_h2_section(markdown, "опыт работы")
    if not experience:
        return ""
    company = ""
    for raw_line in experience.splitlines():
        line = raw_line.strip()
        h3_match = H3_RE.match(line)
        if h3_match:
            company = normalize_text(h3_match.group("title"))
            continue
        if line.startswith("**") and line.endswith("**"):
            title = clean_markdown_inline(line)
            if company:
                return f"{title} — {company}"
            return title
    return ""


def extract_location_from_markdown(markdown: str) -> str:
    for raw_line in markdown.splitlines():
        line = clean_markdown_inline(raw_line)
        if ":" not in line:
            continue
        if "город/страна" in line.lower() or line.lower().startswith("location"):
            _, value = line.split(":", maxsplit=1)
            return normalize_text(value)
    return ""


def extract_email_from_markdown(markdown: str) -> str:
    match = EMAIL_RE.search(markdown)
    return normalize_text(match.group(0)) if match else ""


def extract_linkedin_from_markdown(markdown: str) -> str:
    match = LINKEDIN_RE.search(markdown)
    return normalize_text(match.group(0)) if match else ""


def extract_telegram_from_markdown(markdown: str) -> str:
    match = re.search(r"@\w+", markdown)
    return normalize_text(match.group(0)) if match else ""


def extract_labeled_contact(markdown: str, label: str) -> str:
    needle = label.lower()
    for raw_line in markdown.splitlines():
        line = clean_markdown_inline(raw_line)
        if ":" not in line:
            continue
        if needle not in line.lower():
            continue
        _, value = line.split(":", maxsplit=1)
        return normalize_text(value)
    return ""


def pick_localized_value(surface_map: dict[str, str], base_keys: tuple[str, ...], locales: tuple[str, ...]) -> str:
    for base_key in base_keys:
        for locale in locales:
            value = surface_map.get(f"{base_key}.{locale}")
            if value:
                return value
        direct = surface_map.get(base_key)
        if direct:
            return direct
    return ""


def first_non_empty(*values: str) -> str:
    for value in values:
        normalized = normalize_text(value)
        if normalized:
            return normalized
    return ""


def resolve_english_copy(*, source_text: str, missing_message: str, translate_message: str) -> str:
    if source_text.startswith(GAP_PREFIX):
        return source_text
    if not contains_cyrillic(source_text):
        return source_text
    return f"{CHECK_PREFIX} {translate_message}\n\n{source_text}" if source_text else f"{CHECK_PREFIX} {missing_message}"


def render_english_list_item(item: str) -> str:
    if item.startswith((CHECK_PREFIX, GAP_PREFIX, OPTIONAL_PREFIX)):
        return item
    if not contains_cyrillic(item):
        return item
    return f"{CHECK_PREFIX} translate: {item}"


def format_private_contact(value: str | None) -> str:
    normalized = normalize_text(value)
    if not normalized:
        return f"{OPTIONAL_PREFIX} leave blank unless the owner wants to publish a private channel."
    return f"{OPTIONAL_PREFIX} {normalized}"


def contains_cyrillic(value: str) -> bool:
    return bool(CYRILLIC_RE.search(value))


def is_marker_value(value: str) -> bool:
    return value.startswith((CHECK_PREFIX, GAP_PREFIX, OPTIONAL_PREFIX))


def clean_markdown_inline(value: str) -> str:
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", value)
    cleaned = re.sub(r"`(.*?)`", r"\1", cleaned)
    cleaned = cleaned.replace("<", "").replace(">", "")
    return normalize_text(cleaned)


def merge_unique_strings(values: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    return tuple(dedupe_preserve_order(values))


def dedupe_preserve_order(values: tuple[str, ...] | list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = normalize_text(value)
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def trim_blank_lines(lines: list[str]) -> list[str]:
    start = 0
    end = len(lines)
    while start < end and not lines[start].strip():
        start += 1
    while end > start and not lines[end - 1].strip():
        end -= 1
    return lines[start:end]


def normalize_heading(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\wА-Яа-яЁё]+", " ", value.lower())).strip()
