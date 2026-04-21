from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from application_agent.normalization.source_channels import infer_source_channel, normalize_response_method


class SourceChannelTests(unittest.TestCase):
    def test_infer_source_channel_uses_data_driven_rules(self) -> None:
        self.assertEqual(infer_source_channel("https://hh.ru/vacancy/132114761", ""), "HeadHunter")
        self.assertEqual(infer_source_channel("https://career.habr.com/vacancies/1", ""), "Habr Career")
        self.assertEqual(infer_source_channel("https://company.example/jobs/1", ""), "Company Site")
        self.assertEqual(infer_source_channel("", "manual text"), "Manual")
        self.assertEqual(infer_source_channel("https://example.com/open-role", ""), "Website")

    def test_normalize_response_method_uses_data_driven_rules(self) -> None:
        self.assertEqual(normalize_response_method("HeadHunter", ""), "Сайт HH")
        self.assertEqual(normalize_response_method("", "https://linkedin.com/jobs/view/1"), "LinkedIn")
        self.assertEqual(normalize_response_method("", "https://company.example/careers/1"), "Сайт компании")
        self.assertEqual(normalize_response_method("manual", ""), "Другое")


if __name__ == "__main__":
    unittest.main()
