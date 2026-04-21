from __future__ import annotations


UNSPECIFIED_VALUES = {"", "не указано", "n/a", "null"}
DISPLAY_NO_DATA = "нет данных"
DISPLAY_UNSPECIFIED = "Не указано"


def is_unspecified(value: str) -> bool:
    return value.strip().lower() in UNSPECIFIED_VALUES


def display_or_no_data(value: str) -> str:
    cleaned = value.strip()
    return DISPLAY_NO_DATA if is_unspecified(cleaned) else cleaned


def display_or_unspecified(value: str) -> str:
    cleaned = value.strip()
    return DISPLAY_UNSPECIFIED if is_unspecified(cleaned) else cleaned
