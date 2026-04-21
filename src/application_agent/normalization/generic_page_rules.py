from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources


@lru_cache(maxsize=1)
def load_generic_page_rules() -> dict[str, set[str]]:
    payload = json.loads(resources.files("application_agent.data").joinpath("generic_page_rules.json").read_text(encoding="utf-8"))
    return {
        "ui_noise_lines": {str(item).strip().lower() for item in payload.get("ui_noise_lines", [])},
        "company_stopwords": {str(item).strip().lower() for item in payload.get("company_stopwords", [])},
    }


GENERIC_PAGE_RULES = load_generic_page_rules()
GENERIC_UI_NOISE_LINES = GENERIC_PAGE_RULES["ui_noise_lines"]
GENERIC_COMPANY_STOPWORDS = GENERIC_PAGE_RULES["company_stopwords"]
