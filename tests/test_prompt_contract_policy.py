from __future__ import annotations

from pathlib import Path

import pytest

from application_agent.workflows.analyze_vacancy import ANALYZE_PROMPT_FILES, is_probable_mojibake


REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PROMPT_DIR = REPO_ROOT / "src" / "application_agent" / "data" / "prompts" / "analyze-vacancy"
ROOT_PROMPT_DIR = REPO_ROOT.parents[1] / "agent_memory" / "prompts" / "analyze-vacancy"

REQUIRED_MARKERS = {
    "system.ru.md": [
        "Иерархия источников",
        "Factual boundaries",
        "MASTER",
        "humanize-russian-business-text",
    ],
    "task.ru.md": [
        "Обязательные действия",
        "target_mode",
        "cover_letter_evidence",
        "TEMP, PERM и NEW DATA NEEDED",
    ],
    "resume-selection.ru.md": [
        "Контракт выбора ролевого резюме",
        "must-have",
        "MASTER policy",
        "HoE",
    ],
    "analysis-contract.ru.md": [
        "Fit-анализ",
        "Сильные стороны",
        "Позиционирование",
        "доменный gap",
    ],
    "cover-letter-contract.ru.md": [
        "Главная задача письма",
        "Выбор фактуры",
        "Standard version",
        "Проверка качества",
    ],
    "resume-adaptation-contract.ru.md": [
        "Контракт draft-входов",
        "TEMP, PERM и NEW DATA NEEDED",
        "Summary",
        "Experience",
    ],
    "humanizer-pass.ru.md": [
        "Рамка отдельного humanizer-pass",
        "humanize-russian-business-text",
        "Источник редакторской политики",
        "Верни только валидный JSON",
    ],
}

FORBIDDEN_PROMPT_FRAGMENTS = [
    "[Имя]",
    "[Telegram]",
    "{{",
    "}}",
    "TODO",
]


def test_packaged_prompt_modules_are_complete_and_substantive() -> None:
    expected_files = sorted(ANALYZE_PROMPT_FILES.values())
    actual_files = sorted(path.name for path in PACKAGE_PROMPT_DIR.glob("*.ru.md"))

    assert actual_files == expected_files

    for filename in expected_files:
        text = read_prompt(PACKAGE_PROMPT_DIR / filename)
        assert len(text) >= 900, f"{filename} is too short for a runtime prompt contract."
        assert not is_probable_mojibake(text), f"{filename} contains probable mojibake."
        assert_no_forbidden_fragments(filename, text)
        for marker in REQUIRED_MARKERS[filename]:
            assert marker in text, f"{filename} is missing required marker: {marker}"


def test_root_prompt_overrides_are_synchronized_with_packaged_defaults() -> None:
    if not ROOT_PROMPT_DIR.exists():
        pytest.skip("Root prompt overrides are not present in this checkout.")

    for filename in sorted(ANALYZE_PROMPT_FILES.values()):
        package_text = read_prompt(PACKAGE_PROMPT_DIR / filename)
        root_text = read_prompt(ROOT_PROMPT_DIR / filename)

        assert root_text == package_text, f"{filename} root override differs from packaged default."


def test_humanizer_pass_prompt_is_only_an_envelope_for_the_skill() -> None:
    text = read_prompt(PACKAGE_PROMPT_DIR / "humanizer-pass.ru.md")

    assert "humanize-russian-business-text" in text
    assert "Не переписывай его правила" in text
    assert "Источник редакторской политики" in text
    assert "Жанровые ориентиры" not in text
    assert "Базовые правила" not in text
    assert len(text) < 2500


def read_prompt(path: Path) -> str:
    assert path.exists(), f"Missing prompt file: {path}"
    return path.read_text(encoding="utf-8")


def assert_no_forbidden_fragments(filename: str, text: str) -> None:
    offenders = [fragment for fragment in FORBIDDEN_PROMPT_FRAGMENTS if fragment in text]
    assert not offenders, f"{filename} contains forbidden prompt fragments: {', '.join(offenders)}"
