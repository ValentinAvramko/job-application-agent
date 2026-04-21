from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from application_agent.integrations.playwright_renderer import PlaywrightRenderedPage, render_page_with_playwright


class PlaywrightRendererTests(unittest.TestCase):
    def test_render_page_with_playwright_parses_json_output(self) -> None:
        completed = type(
            "Completed",
            (),
            {
                "returncode": 0,
                "stdout": json.dumps({"html": "<html><body>Hello</body></html>", "url": "https://example.com", "title": "Example"}),
                "stderr": "",
            },
        )()

        with patch("application_agent.integrations.playwright_renderer.is_npx_available", return_value=True), patch(
            "application_agent.integrations.playwright_renderer.subprocess.run",
            return_value=completed,
        ):
            result = render_page_with_playwright("https://example.com")

        self.assertEqual(
            result,
            PlaywrightRenderedPage(
                html="<html><body>Hello</body></html>",
                url="https://example.com",
                title="Example",
            ),
        )

    def test_render_page_with_playwright_requires_npx(self) -> None:
        with patch("application_agent.integrations.playwright_renderer.is_npx_available", return_value=False):
            with self.assertRaisesRegex(RuntimeError, "npx is not available"):
                render_page_with_playwright("https://example.com")
