from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from application_agent.normalization.countries import (
    infer_country_name_from_text,
    normalize_country_code,
    normalize_country_name,
    resolve_country_name_from_hh_id,
)


class CountryCatalogTests(unittest.TestCase):
    def test_normalize_country_name_prefers_localized_display_name(self) -> None:
        self.assertEqual(normalize_country_name("KZ"), "Казахстан")
        self.assertEqual(normalize_country_name("DEU"), "Германия")
        self.assertEqual(normalize_country_name("Belarus"), "Беларусь")
        self.assertEqual(normalize_country_name("Россия"), "Россия")

    def test_normalize_country_code_resolves_aliases(self) -> None:
        self.assertEqual(normalize_country_code("KZ"), "KZ")
        self.assertEqual(normalize_country_code("Kazakhstan"), "KZ")
        self.assertEqual(normalize_country_code("Казахстан"), "KZ")
        self.assertEqual(normalize_country_code("Белоруссия"), "BY")

    def test_resolve_country_name_from_hh_id_uses_catalog_data(self) -> None:
        self.assertEqual(resolve_country_name_from_hh_id("1"), "Россия")
        self.assertEqual(resolve_country_name_from_hh_id("16"), "Беларусь")

    def test_infer_country_name_from_text_uses_catalog_hints(self) -> None:
        self.assertEqual(infer_country_name_from_text("Зарплата от 5000 бел. руб."), "Беларусь")
        self.assertEqual(infer_country_name_from_text("Оформление по ТК, офис в Астане, зарплата в тенге"), "Казахстан")


if __name__ == "__main__":
    unittest.main()
