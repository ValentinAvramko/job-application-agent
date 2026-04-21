from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources


def normalize_lookup_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


@dataclass(frozen=True)
class CountryEntry:
    alpha2: str
    alpha3: str
    name_en: str
    name_ru: str
    aliases: tuple[str, ...]
    hh_ids: tuple[str, ...]
    text_hints: tuple[str, ...]

    @property
    def default_name(self) -> str:
        return self.name_ru or self.name_en


class CountryCatalog:
    def __init__(self, entries: tuple[CountryEntry, ...]) -> None:
        self.entries = entries
        self.by_code = {entry.alpha2: entry for entry in entries}
        self.by_hh_id: dict[str, CountryEntry] = {}
        self.by_alias: dict[str, CountryEntry] = {}
        self.text_hints: list[tuple[str, CountryEntry]] = []

        for entry in entries:
            for hh_id in entry.hh_ids:
                self.by_hh_id[normalize_lookup_key(hh_id)] = entry

            aliases = {
                entry.alpha2,
                entry.alpha3,
                entry.name_en,
                entry.name_ru,
                *entry.aliases,
            }
            for alias in aliases:
                if not alias:
                    continue
                self.by_alias[normalize_lookup_key(alias)] = entry

            for hint in entry.text_hints:
                if hint:
                    self.text_hints.append((normalize_lookup_key(hint), entry))

    def resolve(self, value: str) -> CountryEntry | None:
        key = normalize_lookup_key(value)
        if not key:
            return None
        return self.by_alias.get(key)

    def resolve_name(self, value: str) -> str:
        entry = self.resolve(value)
        if entry is not None:
            return entry.default_name
        return value.strip()

    def resolve_code(self, value: str) -> str:
        entry = self.resolve(value)
        return entry.alpha2 if entry is not None else ""

    def resolve_hh_country_id(self, value: str) -> str:
        entry = self.by_hh_id.get(normalize_lookup_key(value))
        return entry.default_name if entry is not None else ""

    def infer_name_from_text(self, text: str) -> str:
        normalized_text = normalize_lookup_key(text)
        if not normalized_text:
            return ""
        for hint, entry in self.text_hints:
            if hint in normalized_text:
                return entry.default_name
        return ""


@lru_cache(maxsize=1)
def load_country_catalog() -> CountryCatalog:
    raw_entries = json.loads(resources.files("application_agent.data").joinpath("iso_countries.json").read_text(encoding="utf-8"))
    metadata = json.loads(resources.files("application_agent.data").joinpath("country_metadata.json").read_text(encoding="utf-8"))

    entries: list[CountryEntry] = []
    for item in raw_entries:
        alpha2 = str(item["alpha2"]).upper()
        overlay = metadata.get(alpha2, {})
        entries.append(
            CountryEntry(
                alpha2=alpha2,
                alpha3=str(item["alpha3"]).upper(),
                name_en=str(item["name"]).strip(),
                name_ru=str(overlay.get("name_ru", "")).strip(),
                aliases=tuple(str(value).strip() for value in overlay.get("aliases", [])),
                hh_ids=tuple(str(value).strip() for value in overlay.get("hh_ids", [])),
                text_hints=tuple(str(value).strip() for value in overlay.get("text_hints", [])),
            )
        )
    return CountryCatalog(tuple(entries))


COUNTRY_CATALOG = load_country_catalog()


def normalize_country_name(value: str) -> str:
    return COUNTRY_CATALOG.resolve_name(value)


def normalize_country_code(value: str) -> str:
    return COUNTRY_CATALOG.resolve_code(value)


def resolve_country_name_from_hh_id(value: str) -> str:
    return COUNTRY_CATALOG.resolve_hh_country_id(value)


def infer_country_name_from_text(text: str) -> str:
    return COUNTRY_CATALOG.infer_name_from_text(text)
