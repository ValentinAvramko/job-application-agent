from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass


NODE_RENDER_SCRIPT = r"""
const timeoutMs = parseInt(process.argv[1] || "20000", 10);
const targetUrl = process.argv[2];

async function main() {
  const { chromium } = require("playwright");
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  try {
    await page.goto(targetUrl, { waitUntil: "domcontentloaded", timeout: timeoutMs });
    await page.waitForLoadState("networkidle", { timeout: Math.min(timeoutMs, 10000) }).catch(() => {});
    await page.waitForTimeout(1000).catch(() => {});
    const payload = {
      url: page.url(),
      title: await page.title(),
      html: await page.content(),
    };
    console.log(JSON.stringify(payload));
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  const message = error && error.stack ? error.stack : String(error);
  console.error(message);
  process.exit(1);
});
"""


@dataclass(frozen=True)
class PlaywrightRenderedPage:
    html: str
    url: str = ""
    title: str = ""


def is_npx_available() -> bool:
    return shutil.which("npx") is not None


def render_page_with_playwright(source_url: str, *, timeout_ms: int = 20_000) -> PlaywrightRenderedPage:
    if not is_npx_available():
        raise RuntimeError("npx is not available")

    command = [
        "npx",
        "--yes",
        "--package",
        "playwright",
        "node",
        "-e",
        NODE_RENDER_SCRIPT,
        str(timeout_ms),
        source_url,
    ]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=max(30, int(timeout_ms / 1000) + 15),
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
        raise RuntimeError(f"Playwright render failed: {stderr}")

    stdout_lines = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
    if not stdout_lines:
        raise RuntimeError("Playwright render returned empty output")
    payload = json.loads(stdout_lines[-1])
    html = str(payload.get("html", "") or "")
    if not html.strip():
        raise RuntimeError("Playwright render returned empty html")
    return PlaywrightRenderedPage(
        html=html,
        url=str(payload.get("url", "") or ""),
        title=str(payload.get("title", "") or ""),
    )
