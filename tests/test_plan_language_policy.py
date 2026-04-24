from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLANS_DIR = REPO_ROOT / "plans"

ENGLISH_BOILERPLATE_RE = re.compile(
    r"(?m)"
    r"^(?:##|###) (?:Objective|Background and context|Scope|In scope|Out of scope|"
    r"Assumptions|Risks and unknowns|External touchpoints|Milestones|Decision log|"
    r"Progress log|Current state|Completion summary)$"
    r"|^- (?:Title|Owner|Created|Last updated|Overall status|Status|Goal|"
    r"Deliverables|Acceptance criteria|Validation commands|Notes / discoveries|"
    r"Current milestone|Current status|Next step|Active blockers|Open questions):"
)


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
