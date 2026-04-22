from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

from application_agent.review_state import AcceptedSignal, AcceptedSignalsStore, normalize_text, split_markdown_row

MANAGED_SECTION_START = "<!-- application-agent:rebuild-master:start -->"
MANAGED_SECTION_END = "<!-- application-agent:rebuild-master:end -->"
MANAGED_SECTION_HEADING = "## Approved Permanent Signals"
RECOMMENDATIONS_HEADING = "## Рекомендации"


@dataclass(frozen=True)
class ManagedMasterSignal:
    signal: str
    source_vacancy: str
    rationale: str
    updated_at: str

    @classmethod
    def from_accepted(cls, signal: AcceptedSignal) -> ManagedMasterSignal:
        return cls(
            signal=normalize_text(signal.signal),
            source_vacancy=normalize_text(signal.source_vacancy),
            rationale=normalize_text(signal.rationale),
            updated_at=normalize_text(signal.updated_at),
        )

    @property
    def key(self) -> str:
        return self.signal.lower()


@dataclass(frozen=True)
class RebuildMasterComputation:
    master_text: str
    report_markdown: str
    changed: bool
    added_signals: tuple[ManagedMasterSignal, ...]
    updated_signals: tuple[ManagedMasterSignal, ...]
    removed_signals: tuple[ManagedMasterSignal, ...]
    unchanged_signals: tuple[ManagedMasterSignal, ...]


def compute_rebuild_master_projection(
    *, master_text: str, accepted_signals: list[AcceptedSignal]
) -> RebuildMasterComputation:
    normalized_master = normalize_newlines(master_text)
    existing = parse_managed_master_signals(normalized_master)
    desired = desired_master_signals(accepted_signals)

    existing_by_key = {signal.key: signal for signal in existing}
    desired_by_key = {signal.key: signal for signal in desired}

    added = tuple(signal for signal in desired if signal.key not in existing_by_key)
    updated = tuple(
        signal
        for signal in desired
        if signal.key in existing_by_key and signal != existing_by_key[signal.key]
    )
    unchanged = tuple(
        signal
        for signal in desired
        if signal.key in existing_by_key and signal == existing_by_key[signal.key]
    )
    removed = tuple(signal for signal in existing if signal.key not in desired_by_key)

    next_master_text = replace_managed_master_section(normalized_master, desired)
    changed = next_master_text != normalized_master

    return RebuildMasterComputation(
        master_text=next_master_text,
        report_markdown=render_rebuild_master_report(
            added_signals=added,
            updated_signals=updated,
            removed_signals=removed,
            unchanged_signals=unchanged,
            changed=changed,
        ),
        changed=changed,
        added_signals=added,
        updated_signals=updated,
        removed_signals=removed,
        unchanged_signals=unchanged,
    )


def apply_rebuild_master_projection(
    *, master_path: Path, accepted_path: Path, report_path: Path | None = None
) -> RebuildMasterComputation:
    if not master_path.exists():
        raise FileNotFoundError(f"MASTER resume is missing: {master_path}")

    accepted_store = AcceptedSignalsStore.load(accepted_path)
    computation = compute_rebuild_master_projection(
        master_text=master_path.read_text(encoding="utf-8"),
        accepted_signals=accepted_store.records(),
    )

    if computation.changed:
        master_path.write_text(computation.master_text, encoding="utf-8", newline="\n")

    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(computation.report_markdown, encoding="utf-8", newline="\n")

    return computation


def desired_master_signals(accepted_signals: list[AcceptedSignal]) -> tuple[ManagedMasterSignal, ...]:
    rows = [
        ManagedMasterSignal.from_accepted(signal)
        for signal in accepted_signals
        if normalize_text(signal.target).lower() == "master.md"
    ]
    deduped: dict[str, ManagedMasterSignal] = {}
    for row in rows:
        deduped[row.key] = row
    return tuple(sorted(deduped.values(), key=lambda item: item.key))


def parse_managed_master_signals(master_text: str) -> tuple[ManagedMasterSignal, ...]:
    block_range = find_managed_master_section(master_text)
    if block_range is None:
        return ()

    block = master_text[block_range[0] : block_range[1]]
    table_lines = [line.strip() for line in block.splitlines() if line.strip().startswith("|")]
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


def render_managed_master_section(signals: tuple[ManagedMasterSignal, ...]) -> str:
    if not signals:
        return ""

    lines = [
        MANAGED_SECTION_START,
        MANAGED_SECTION_HEADING,
        "",
        "| Signal | Source Vacancy | Rationale | Updated At |",
        "| --- | --- | --- | --- |",
    ]
    lines.extend(
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
    )
    lines.extend(["", MANAGED_SECTION_END])
    return "\n".join(lines)


def replace_managed_master_section(master_text: str, signals: tuple[ManagedMasterSignal, ...]) -> str:
    rendered_section = render_managed_master_section(signals)
    block_range = find_managed_master_section(master_text)

    if block_range is not None:
        prefix = master_text[: block_range[0]]
        suffix = master_text[block_range[1] :]
        return stitch_master_text(prefix=prefix, managed_section=rendered_section, suffix=suffix)

    if not rendered_section:
        return ensure_trailing_newline(master_text)

    insert_at = find_insert_position(master_text)
    prefix = master_text[:insert_at]
    suffix = master_text[insert_at:]
    return stitch_master_text(prefix=prefix, managed_section=rendered_section, suffix=suffix)


def find_managed_master_section(master_text: str) -> tuple[int, int] | None:
    start = master_text.find(MANAGED_SECTION_START)
    if start == -1:
        return None
    end = master_text.find(MANAGED_SECTION_END, start)
    if end == -1:
        raise ValueError("Managed rebuild-master section start marker exists without end marker.")
    return (start, end + len(MANAGED_SECTION_END))


def find_insert_position(master_text: str) -> int:
    match = re.search(rf"(?m)^{re.escape(RECOMMENDATIONS_HEADING)}\s*$", master_text)
    if match:
        return match.start()
    return len(master_text)


def stitch_master_text(*, prefix: str, managed_section: str, suffix: str) -> str:
    parts = [part.strip("\n") for part in (prefix, managed_section, suffix) if part.strip("\n")]
    if not parts:
        return "\n"
    return "\n\n".join(parts).rstrip() + "\n"


def render_rebuild_master_report(
    *,
    added_signals: tuple[ManagedMasterSignal, ...],
    updated_signals: tuple[ManagedMasterSignal, ...],
    removed_signals: tuple[ManagedMasterSignal, ...],
    unchanged_signals: tuple[ManagedMasterSignal, ...],
    changed: bool,
) -> str:
    lines = [
        "# Rebuild Master Report",
        "",
        "## Summary",
        "",
        f"- Changed: {'yes' if changed else 'no'}",
        f"- Added: {len(added_signals)}",
        f"- Updated: {len(updated_signals)}",
        f"- Removed: {len(removed_signals)}",
        f"- Unchanged: {len(unchanged_signals)}",
        "",
        "## Added",
        "",
        *render_report_section(added_signals),
        "",
        "## Updated",
        "",
        *render_report_section(updated_signals),
        "",
        "## Removed",
        "",
        *render_report_section(removed_signals),
        "",
        "## Unchanged",
        "",
        *render_report_section(unchanged_signals),
        "",
    ]
    return "\n".join(lines)


def render_report_section(signals: tuple[ManagedMasterSignal, ...]) -> list[str]:
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


def escape_table(value: str) -> str:
    return normalize_text(value).replace("|", "\\|").replace("\n", " ")


def normalize_newlines(value: str) -> str:
    return ensure_trailing_newline(value.replace("\r\n", "\n"))


def ensure_trailing_newline(value: str) -> str:
    return value.rstrip("\n") + "\n"
