from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PLANS_DIR = REPO_ROOT / "plans"

# Existing plans created before the Russian-language policy guard. Do not add
# new files here; convert legacy plans to the Russian template when editing them.
LEGACY_ENGLISH_BOILERPLATE_PLANS = {
    "2026-04-21-prepare-screening-workflow.md",
    "2026-04-21-repository-reconstruction-and-backlog.md",
    "2026-04-21-root-artifacts-and-output-normalization.md",
    "2026-04-21-workflow-contract-alignment-and-safety.md",
    "2026-04-22-adoptions-review-and-acceptance-workflow.md",
    "2026-04-22-build-linkedin-workflow.md",
    "2026-04-22-current-stack-contract-remediation.md",
    "2026-04-22-current-workflow-completion-gate.md",
    "2026-04-22-implement-adoptions-review-and-acceptance-workflow.md",
    "2026-04-22-rebuild-master-workflow.md",
    "2026-04-22-rebuild-role-resume-workflow.md",
    "2026-04-23-export-resume-pdf-workflow.md",
    "2026-04-23-migrate-tests-to-pytest.md",
    "2026-04-24-analyze-vacancy-quality-upgrade.md",
    "2026-04-24-application-agent-config-docs.md",
    "2026-04-24-cli-llm-config-docs.md",
    "2026-04-24-responses-api-and-cli-entrypoint.md",
}

ENGLISH_BOILERPLATE_RE = re.compile(
    r"(?m)"
    r"^(?:##|###) (?:Objective|Background and context|Scope|In scope|Out of scope|"
    r"Assumptions|Risks and unknowns|External touchpoints|Milestones|Decision log|"
    r"Progress log|Current state|Completion summary)$"
    r"|^- (?:Title|Owner|Created|Last updated|Overall status|Status|Goal|"
    r"Deliverables|Acceptance criteria|Validation commands|Notes / discoveries|"
    r"Current milestone|Current status|Next step|Active blockers|Open questions):"
)


def test_new_plans_do_not_use_english_boilerplate() -> None:
    offenders: list[str] = []

    for plan_path in sorted(PLANS_DIR.glob("*.md")):
        if plan_path.name in LEGACY_ENGLISH_BOILERPLATE_PLANS:
            continue

        text = plan_path.read_text(encoding="utf-8")
        matches = ENGLISH_BOILERPLATE_RE.findall(text)
        if matches:
            offenders.append(plan_path.name)

    assert not offenders, (
        "New or updated plans must use the Russian template from plans/_template.md. "
        f"English boilerplate found in: {', '.join(offenders)}"
    )
