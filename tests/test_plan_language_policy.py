from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLANS_DIR = REPO_ROOT / "plans"
README_PATH = REPO_ROOT / "README.md"

ENGLISH_BOILERPLATE_RE = re.compile(
    r"(?m)"
    r"^(?:##|###) (?:Objective|Background and context|Scope|In scope|Out of scope|"
    r"Assumptions|Risks and unknowns|External touchpoints|Milestones|Decision log|"
    r"Progress log|Current state|Completion summary)$"
    r"|^- (?:Title|Owner|Created|Last updated|Overall status|Status|Goal|"
    r"Deliverables|Acceptance criteria|Validation commands|Notes / discoveries|"
    r"Current milestone|Current status|Next step|Active blockers|Open questions):"
)

REQUIRED_PLAN_HEADINGS = [
    "## Цель",
    "## Контекст",
    "## Границы",
    "### Входит в scope",
    "### Не входит в scope",
    "## Допущения",
    "## Риски и неизвестные",
    "## Внешние точки касания",
    "## Этапы",
    "## Журнал решений",
    "## Журнал прогресса",
    "## Текущее состояние",
    "## Итог завершения",
]

README_ENGLISH_PROCESS_PHRASES = [
    "Quality mode note:",
    "For Russian output,",
    "The pass is a required quality gate",
    "final cover-letter runs should use",
]


def test_plans_do_not_use_english_boilerplate() -> None:
    offenders: list[str] = []

    for plan_path in sorted(PLANS_DIR.glob("*.md")):
        text = plan_path.read_text(encoding="utf-8")
        matches = ENGLISH_BOILERPLATE_RE.findall(text)
        if matches:
            offenders.append(plan_path.name)

    assert not offenders, (
        "Plans must use the Russian template from plans/_template.md. "
        f"English boilerplate found in: {', '.join(offenders)}"
    )


def test_plans_include_required_russian_structure() -> None:
    offenders: list[str] = []

    for plan_path in sorted(PLANS_DIR.glob("*.md")):
        if plan_path.name == "_template.md":
            continue
        text = plan_path.read_text(encoding="utf-8")
        missing = [heading for heading in REQUIRED_PLAN_HEADINGS if heading not in text]
        if missing:
            offenders.append(f"{plan_path.name}: {', '.join(missing)}")

    assert not offenders, (
        "Plans must follow the required Russian structure from plans/_template.md. "
        f"Missing sections: {'; '.join(offenders)}"
    )


def test_readme_has_no_english_process_insertions() -> None:
    text = README_PATH.read_text(encoding="utf-8")
    offenders = [phrase for phrase in README_ENGLISH_PROCESS_PHRASES if phrase in text]

    assert not offenders, (
        "README process/documentation text must be in Russian; English is allowed only for technical identifiers. "
        f"Found phrases: {', '.join(offenders)}"
    )
