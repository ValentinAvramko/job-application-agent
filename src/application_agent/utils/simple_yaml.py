from __future__ import annotations

from pathlib import Path


def load_simple_yaml(path: Path) -> dict[str, object]:
    payload: dict[str, object] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        key, raw_value = stripped.split(":", maxsplit=1)
        payload[key.strip()] = parse_simple_scalar(raw_value.strip())
    return payload


def parse_simple_scalar(value: str) -> object:
    if value == "null":
        return None
    if value in {"true", "false"}:
        return value == "true"
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    return value


def write_simple_yaml(path: Path, payload: dict[str, object]) -> None:
    preferred_order = [
        "vacancy_id",
        "source_type",
        "source_url",
        "source_channel",
        "company",
        "position",
        "language",
        "country",
        "work_mode",
        "is_active",
        "ingested_at",
        "analyzed_at",
        "selected_resume",
        "target_mode",
        "include_employer_channels",
        "excel_row",
        "status",
        "notes",
    ]
    keys = [key for key in preferred_order if key in payload] + [key for key in payload if key not in preferred_order]
    lines = [f"{key}: {dump_simple_scalar(payload[key])}" for key in keys]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def dump_simple_scalar(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return str(value).lower()
    if value == "":
        return '""'
    return str(value)
