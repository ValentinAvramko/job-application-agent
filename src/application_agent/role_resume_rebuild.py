from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from application_agent.master_rebuild import (
    MANAGED_SECTION_HEADING as MASTER_MANAGED_SECTION_HEADING,
    ManagedMasterSignal,
    RECOMMENDATIONS_HEADING,
    ensure_trailing_newline,
    escape_table,
    normalize_newlines,
    parse_managed_master_signals,
)
from application_agent.review_state import normalize_text, split_markdown_row

MANAGED_SECTION_START = "<!-- application-agent:rebuild-role-resume:start -->"
MANAGED_SECTION_END = "<!-- application-agent:rebuild-role-resume:end -->"
MANAGED_SECTION_HEADING = "## Canonical Role Resume Signals"
MASTER_SIGNALS_HEADING = "### Approved Permanent Signals From MASTER"
ROLE_SIGNALS_HEADING = "### Role Shaping Signals"


@dataclass(frozen=True)
class RoleShapingSignal:
    text: str

    def normalized(self) -> RoleShapingSignal:
        return RoleShapingSignal(text=normalize_text(self.text))

    @property
    def key(self) -> str:
        return self.normalized().text.lower()


@dataclass(frozen=True)
class RebuildRoleResumeComputation:
    role_resume_text: str
    report_markdown: str
    changed: bool
    target_role: str
    added_master_signals: tuple[ManagedMasterSignal, ...]
    updated_master_signals: tuple[ManagedMasterSignal, ...]
    removed_master_signals: tuple[ManagedMasterSignal, ...]
    unchanged_master_signals: tuple[ManagedMasterSignal, ...]
    added_role_signals: tuple[RoleShapingSignal, ...]
    removed_role_signals: tuple[RoleShapingSignal, ...]
    unchanged_role_signals: tuple[RoleShapingSignal, ...]


def compute_rebuild_role_resume_projection(
    *,
    target_role: str,
    master_text: str,
    role_resume_text: str,
    role_signal_text: str = "",
) -> RebuildRoleResumeComputation:
    normalized_master = normalize_newlines(master_text)
    normalized_role_resume = normalize_newlines(role_resume_text)

    desired_master_signals = parse_managed_master_signals(normalized_master)
    desired_role_signals = parse_role_shaping_signals(role_signal_text)
    existing_master_signals, existing_role_signals = parse_managed_role_resume_state(normalized_role_resume)

    existing_master_by_key = {signal.key: signal for signal in existing_master_signals}
    desired_master_by_key = {signal.key: signal for signal in desired_master_signals}

    added_master = tuple(signal for signal in desired_master_signals if signal.key not in existing_master_by_key)
    updated_master = tuple(
        signal
        for signal in desired_master_signals
        if signal.key in existing_master_by_key and signal != existing_master_by_key[signal.key]
    )
    unchanged_master = tuple(
        signal
        for signal in desired_master_signals
        if signal.key in existing_master_by_key and signal == existing_master_by_key[signal.key]
    )
    removed_master = tuple(signal for signal in existing_master_signals if signal.key not in desired_master_by_key)

    existing_role_by_key = {signal.key: signal for signal in existing_role_signals}
    desired_role_by_key = {signal.key: signal for signal in desired_role_signals}

    added_role = tuple(signal for signal in desired_role_signals if signal.key not in existing_role_by_key)
    unchanged_role = tuple(
        signal
        for signal in desired_role_signals
        if signal.key in existing_role_by_key and signal == existing_role_by_key[signal.key]
    )
    removed_role = tuple(signal for signal in existing_role_signals if signal.key not in desired_role_by_key)

    next_role_resume_text = replace_managed_role_resume_section(
        role_resume_text=normalized_role_resume,
        master_signals=desired_master_signals,
        role_signals=desired_role_signals,
    )
    changed = next_role_resume_text != normalized_role_resume

    return RebuildRoleResumeComputation(
        role_resume_text=next_role_resume_text,
        report_markdown=render_rebuild_role_resume_report(
            target_role=target_role,
            added_master_signals=added_master,
            updated_master_signals=updated_master,
            removed_master_signals=removed_master,
            unchanged_master_signals=unchanged_master,
            added_role_signals=added_role,
            removed_role_signals=removed_role,
            unchanged_role_signals=unchanged_role,
            changed=changed,
        ),
        changed=changed,
        target_role=normalize_text(target_role),
        added_master_signals=added_master,
        updated_master_signals=updated_master,
        removed_master_signals=removed_master,
        unchanged_master_signals=unchanged_master,
        added_role_signals=added_role,
        removed_role_signals=removed_role,
        unchanged_role_signals=unchanged_role,
    )


def apply_rebuild_role_resume_projection(
    *,
    target_role: str,
    master_path: Path,
    role_resume_path: Path,
    role_signal_path: Path,
    report_path: Path | None = None,
) -> RebuildRoleResumeComputation:
    if not master_path.exists():
        raise FileNotFoundError(f"MASTER resume is missing: {master_path}")
    if not role_resume_path.exists():
        raise FileNotFoundError(f"Role resume is missing: {role_resume_path}")

    role_signal_text = role_signal_path.read_text(encoding="utf-8") if role_signal_path.exists() else ""
    computation = compute_rebuild_role_resume_projection(
        target_role=target_role,
        master_text=master_path.read_text(encoding="utf-8"),
        role_resume_text=role_resume_path.read_text(encoding="utf-8"),
        role_signal_text=role_signal_text,
    )

    if computation.changed:
        role_resume_path.write_text(computation.role_resume_text, encoding="utf-8", newline="\n")

    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(computation.report_markdown, encoding="utf-8", newline="\n")

    return computation


def parse_role_shaping_signals(markdown: str) -> tuple[RoleShapingSignal, ...]:
    signals: dict[str, RoleShapingSignal] = {}
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line.startswith("- "):
            continue
        value = normalize_text(line[2:])
        if not value or value.lower() == "none":
            continue
        signal = RoleShapingSignal(text=value).normalized()
        signals[signal.key] = signal
    return tuple(sorted(signals.values(), key=lambda item: item.key))


def parse_managed_role_resume_state(role_resume_text: str) -> tuple[tuple[ManagedMasterSignal, ...], tuple[RoleShapingSignal, ...]]:
    block_range = find_managed_role_resume_section(role_resume_text)
    if block_range is None:
        return ((), ())

    block = role_resume_text[block_range[0] : block_range[1]]
    master_block = extract_subsection(
        block,
        start_heading=MASTER_SIGNALS_HEADING,
        end_heading=ROLE_SIGNALS_HEADING,
    )
    role_block = extract_subsection(block, start_heading=ROLE_SIGNALS_HEADING)

    master_rows = parse_master_signal_rows(master_block)
    role_signals = parse_role_signal_rows(role_block)
    return (master_rows, role_signals)


def parse_master_signal_rows(markdown: str) -> tuple[ManagedMasterSignal, ...]:
    table_lines = [line.strip() for line in markdown.splitlines() if line.strip().startswith("|")]
    if len(table_lines) < 2:
        return ()

    rows: list[ManagedMasterSignal] = []
    for line in table_lines[2:]:
        cells = split_markdown_row(line)
        if len(cells) != 4:
            continue
        if not any(cell.strip() for cell in cells):
            continue
        rows.append(
            ManagedMasterSignal(
                signal=normalize_text(cells[0]),
                source_vacancy=normalize_text(cells[1]),
                rationale=normalize_text(cells[2]),
                updated_at=normalize_text(cells[3]),
            )
        )
    deduped = {row.key: row for row in rows}
    return tuple(sorted(deduped.values(), key=lambda item: item.key))


def parse_role_signal_rows(markdown: str) -> tuple[RoleShapingSignal, ...]:
    signals: dict[str, RoleShapingSignal] = {}
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if not line.startswith("- "):
            continue
        value = normalize_text(line[2:])
        if not value or value.lower() == "none":
            continue
        signal = RoleShapingSignal(text=value).normalized()
        signals[signal.key] = signal
    return tuple(sorted(signals.values(), key=lambda item: item.key))


def render_managed_role_resume_section(
    *, master_signals: tuple[ManagedMasterSignal, ...], role_signals: tuple[RoleShapingSignal, ...]
) -> str:
    if not master_signals and not role_signals:
        return ""

    lines = [
        MANAGED_SECTION_START,
        MANAGED_SECTION_HEADING,
        "",
        f"_Source: {MASTER_MANAGED_SECTION_HEADING} in `resumes/MASTER.md` plus optional `knowledge/roles/<role>.md`._",
        "",
        MASTER_SIGNALS_HEADING,
        "",
        "| Signal | Source Vacancy | Rationale | Updated At |",
        "| --- | --- | --- | --- |",
        *render_master_signal_rows(master_signals),
        "",
        ROLE_SIGNALS_HEADING,
        "",
        *render_role_signal_rows(role_signals),
        "",
        MANAGED_SECTION_END,
    ]
    return "\n".join(lines)


def replace_managed_role_resume_section(
    *,
    role_resume_text: str,
    master_signals: tuple[ManagedMasterSignal, ...],
    role_signals: tuple[RoleShapingSignal, ...],
) -> str:
    rendered_section = render_managed_role_resume_section(master_signals=master_signals, role_signals=role_signals)
    block_range = find_managed_role_resume_section(role_resume_text)

    if block_range is not None:
        prefix = role_resume_text[: block_range[0]]
        suffix = role_resume_text[block_range[1] :]
        return stitch_role_resume_text(prefix=prefix, managed_section=rendered_section, suffix=suffix)

    if not rendered_section:
        return ensure_trailing_newline(role_resume_text)

    insert_at = find_insert_position(role_resume_text)
    prefix = role_resume_text[:insert_at]
    suffix = role_resume_text[insert_at:]
    return stitch_role_resume_text(prefix=prefix, managed_section=rendered_section, suffix=suffix)


def find_managed_role_resume_section(role_resume_text: str) -> tuple[int, int] | None:
    start = role_resume_text.find(MANAGED_SECTION_START)
    if start == -1:
        return None
    end = role_resume_text.find(MANAGED_SECTION_END, start)
    if end == -1:
        raise ValueError("Managed rebuild-role-resume section start marker exists without end marker.")
    return (start, end + len(MANAGED_SECTION_END))


def extract_subsection(block: str, *, start_heading: str, end_heading: str | None = None) -> str:
    start_match = re.search(rf"(?m)^{re.escape(start_heading)}\s*$", block)
    if not start_match:
        return ""
    start = start_match.end()
    if end_heading is None:
        return block[start:]

    end_match = re.search(rf"(?m)^{re.escape(end_heading)}\s*$", block[start:])
    if not end_match:
        return block[start:]
    return block[start : start + end_match.start()]


def find_insert_position(role_resume_text: str) -> int:
    match = re.search(rf"(?m)^{re.escape(RECOMMENDATIONS_HEADING)}\s*$", role_resume_text)
    if match:
        return match.start()
    return len(role_resume_text)


def stitch_role_resume_text(*, prefix: str, managed_section: str, suffix: str) -> str:
    parts = [part.strip("\n") for part in (prefix, managed_section, suffix) if part.strip("\n")]
    if not parts:
        return "\n"
    return "\n\n".join(parts).rstrip() + "\n"


def render_rebuild_role_resume_report(
    *,
    target_role: str,
    added_master_signals: tuple[ManagedMasterSignal, ...],
    updated_master_signals: tuple[ManagedMasterSignal, ...],
    removed_master_signals: tuple[ManagedMasterSignal, ...],
    unchanged_master_signals: tuple[ManagedMasterSignal, ...],
    added_role_signals: tuple[RoleShapingSignal, ...],
    removed_role_signals: tuple[RoleShapingSignal, ...],
    unchanged_role_signals: tuple[RoleShapingSignal, ...],
    changed: bool,
) -> str:
    lines = [
        "# Rebuild Role Resume Report",
        "",
        "## Summary",
        "",
        f"- Target Role: {normalize_text(target_role)}",
        f"- Changed: {'yes' if changed else 'no'}",
        f"- Master Signals Added: {len(added_master_signals)}",
        f"- Master Signals Updated: {len(updated_master_signals)}",
        f"- Master Signals Removed: {len(removed_master_signals)}",
        f"- Master Signals Unchanged: {len(unchanged_master_signals)}",
        f"- Role Signals Added: {len(added_role_signals)}",
        f"- Role Signals Removed: {len(removed_role_signals)}",
        f"- Role Signals Unchanged: {len(unchanged_role_signals)}",
        "",
        "## Added Master Signals",
        "",
        *render_report_master_section(added_master_signals),
        "",
        "## Updated Master Signals",
        "",
        *render_report_master_section(updated_master_signals),
        "",
        "## Removed Master Signals",
        "",
        *render_report_master_section(removed_master_signals),
        "",
        "## Unchanged Master Signals",
        "",
        *render_report_master_section(unchanged_master_signals),
        "",
        "## Added Role Signals",
        "",
        *render_report_role_section(added_role_signals),
        "",
        "## Removed Role Signals",
        "",
        *render_report_role_section(removed_role_signals),
        "",
        "## Unchanged Role Signals",
        "",
        *render_report_role_section(unchanged_role_signals),
        "",
    ]
    return "\n".join(lines)


def render_master_signal_rows(signals: tuple[ManagedMasterSignal, ...]) -> list[str]:
    if not signals:
        return ["|  |  |  |  |"]
    return [
        "| "
        + " | ".join(
            [
                escape_table(signal.signal),
                escape_table(signal.source_vacancy),
                escape_table(signal.rationale),
                escape_table(signal.updated_at),
            ]
        )
        + " |"
        for signal in signals
    ]


def render_role_signal_rows(signals: tuple[RoleShapingSignal, ...]) -> list[str]:
    if not signals:
        return ["- none"]
    return [f"- {signal.text}" for signal in signals]


def render_report_master_section(signals: tuple[ManagedMasterSignal, ...]) -> list[str]:
    if not signals:
        return ["- none"]
    return [
        "- "
        + " | ".join(
            [
                signal.signal,
                signal.source_vacancy or "n/a",
                signal.rationale or "n/a",
                signal.updated_at or "n/a",
            ]
        )
        for signal in signals
    ]


def render_report_role_section(signals: tuple[RoleShapingSignal, ...]) -> list[str]:
    if not signals:
        return ["- none"]
    return [f"- {signal.text}" for signal in signals]
