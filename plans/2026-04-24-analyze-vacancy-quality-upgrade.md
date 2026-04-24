# Analyze Vacancy Quality Upgrade

- Title: `analyze-vacancy quality upgrade`
- Slug: `2026-04-24-analyze-vacancy-quality-upgrade`
- Owner: `Codex`
- Created: `2026-04-24`
- Last updated: `2026-04-24 01:05`
- Overall status: `done`

## Objective

Upgrade `analyze-vacancy` from a shallow deterministic draft into a high-quality LLM-backed vacancy analysis workflow that:

- selects the best role resume from data-driven role profiles in `knowledge/roles/`;
- computes an explainable Russian-language fit score;
- renders a deep `analysis.md` with fit analysis, selected-resume rationale, two cover-letter variants and adaptation inputs;
- renders a richer `adoptions.md` with full draft resume edits for downstream review;
- keeps actual resume mutation in `rebuild-master` / `rebuild-role-resume`.

## Background and context

The current workflow reads a hardcoded role list, extracts up to eight requirement-like lines, scores them with a simple keyword matcher and writes a compact `analysis.md` plus a thin `adoptions.md`. This underperforms the legacy baseline prompt, especially for senior IT leadership roles.

The intended workflow split is now:

- `analyze-vacancy`: fit analysis, selected resume, cover letters, draft adaptation inputs.
- `intake-adoptions`: normalize vacancy-local adaptation drafts into root review stores.
- `prepare-screening`: interview preparation only.
- `rebuild-master` / `rebuild-role-resume`: apply accepted resume changes later.

The project test runner is `pytest`; new validation must use `python -m pytest`.

## Scope

### In scope

- Dedicated plan and workflow documentation update.
- Data-driven role catalog based on `knowledge/roles/*.md`.
- Initial role profiles for existing role resumes.
- Explainable scoring model with Russian output terms.
- LLM provider boundary and structured response validation.
- Updated `analysis.md` and `adoptions.md` contracts.
- `intake-adoptions` support for richer adaptation drafts.
- `prepare-screening` compatibility with the new analysis format.
- Pytest coverage and smoke-style validation.

### Out of scope

- Direct mutation of `resumes/*.md` from `analyze-vacancy`.
- Separate `cover-letter.md` artifact.
- Full agent-guided adoptions review redesign.
- Replacing `prepare-screening` with `analyze-vacancy`.

## Assumptions

- `knowledge/roles/` is the source of truth for available role profiles.
- Existing roles `CIO`, `CTO`, `HoE`, `HoD`, `EM` remain initial profiles only, not hardcoded workflow choices.
- LLM runtime is required for real `analyze-vacancy` runs; tests use fake provider.
- The first scoring implementation uses a documented hybrid of baseline prompt weighting and leadership-specific evidence checks.
- `OPENAI_API_KEY` plus model config are required for real OpenAI-compatible calls.

## Risks and unknowns

- Adding a real LLM boundary without the OpenAI SDK requires a small stdlib HTTP adapter and careful error handling.
- Role profiles are new root artifacts; missing or poor profiles can degrade selection quality.
- LLM output must be validated enough to avoid silent broken markdown.
- Existing downstream tests may assume the old section headings and need compatibility handling.

## External touchpoints

- `C:\Users\avramko\OneDrive\Documents\Career\knowledge\roles\` - update - add initial role profiles and read them during role selection.
- `C:\Users\avramko\OneDrive\Documents\Career\templates\knowledge\role-signal.template.md` - read - format reference for role profiles.
- `C:\Users\avramko\OneDrive\Documents\Career\agent_memory\workflows\analyze-vacancy.md` - update - operator-facing workflow contract.
- `C:\Users\avramko\OneDrive\Documents\Career\vacancies\` - generated/updated by workflow - richer `analysis.md` and `adoptions.md`.

## Milestones

### M1. Plan, Role Catalog, And Contract Baseline

- Status: `done`
- Goal:
  - Create this plan, add initial role profiles and update the analyze workflow contract.
- Deliverables:
  - `knowledge/roles/CIO.md`, `CTO.md`, `HoE.md`, `HoD.md`, `EM.md`
  - updated `agent_memory/workflows/analyze-vacancy.md`
  - this plan
- Acceptance criteria:
  - role profiles exist for current role resumes;
  - plan and workflow docs describe data-driven role selection and rich output contract;
  - no production code changes are started before baseline is documented.
- Validation commands:
  - `Get-ChildItem ..\..\knowledge\roles -File`
  - `Get-Content -Raw ..\..\agent_memory\workflows\analyze-vacancy.md`
- Notes / discoveries:
  - initial profiles were added for the five existing role resumes;
  - `agent_memory/workflows/analyze-vacancy.md` now describes the rich analysis and role catalog contract.

### M2. Evidence, Scoring, LLM Boundary, And Analysis Rendering

- Status: `done`
- Goal:
  - Replace shallow heuristic analysis with role-profile evidence, explainable scoring and LLM-backed package rendering.
- Deliverables:
  - updated `analyze_vacancy.py`
  - LLM provider boundary
  - CLI options for LLM settings
  - pytest coverage for role catalog, scoring, selection and LLM boundary
- Acceptance criteria:
  - roles are loaded from `knowledge/roles/*.md`;
  - missing matching resume is reported as diagnostic and excluded;
  - no valid role profile produces an explicit error;
  - real OpenAI-compatible provider requires API key/model;
  - fake provider can produce deterministic structured analysis for tests;
  - `analysis.md` has three large blocks.
- Validation commands:
  - `python -m pytest tests/test_analyze_workflow.py`
- Notes / discoveries:
  - implemented role catalog loading from `knowledge/roles/*.md`, ignoring `README.md`;
  - real provider is OpenAI-compatible via stdlib HTTP and fails explicitly without `OPENAI_API_KEY` / model;
  - fake provider renders deterministic structured packages for tests and smoke runs;
  - selection now combines requirement fit, role profile match, senior scope alignment, weak title signal and risky-claim penalty.

### M3. Rich Adoptions Intake And Screening Compatibility

- Status: `done`
- Goal:
  - Preserve richer `adoptions.md` content through intake and keep `prepare-screening` compatible with the new analysis contract.
- Deliverables:
  - updated `intake_adoptions.py`
  - updated `prepare_screening.py`
  - pytest coverage for richer adoptions and screening compatibility
- Acceptance criteria:
  - `intake-adoptions` preserves summary, skills and experience draft edits;
  - `NEW DATA NEEDED` items still sync into questions ledger;
  - `prepare-screening` reads useful signals from new analysis format.
- Validation commands:
  - `python -m pytest tests/test_adoptions_intake_workflow.py tests/test_prepare_screening_workflow.py`
- Notes / discoveries:
  - `intake-adoptions` now imports both bullet lists and richer markdown table rows from vacancy-local `adoptions.md`;
  - `prepare-screening` reads new `###` analysis subsections and uses `full/partial/none/unclear` coverage semantics.

### M4. Full Validation And Real Scenario Check

- Status: `done`
- Goal:
  - Validate the upgraded workflow on the full pytest suite and a real vacancy scenario with fake or configured LLM provider.
- Deliverables:
  - updated plan status and completion summary
  - final docs/test sync if needed
- Acceptance criteria:
  - full pytest suite passes;
  - a real vacancy smoke run can produce rich `analysis.md` and `adoptions.md` with a configured provider;
  - remaining risks are documented.
- Validation commands:
  - `python -m pytest tests`
  - `python run_agent.py --root ../.. analyze-vacancy --vacancy-id 20260423-fintehrobot-head-of-development-rukovoditel-razrabotki --llm-provider fake --llm-model test`
- Notes / discoveries:
  - full pytest suite passed: `80 passed`;
  - real Fintehrobot smoke run with fake provider selected `HoE` after adding scope-alignment scoring;
  - intake and prepare-screening smoke runs completed on the same real vacancy.

## Decision log

- `2026-04-24 00:00` - `knowledge/roles/*.md` is the role catalog source. - User clarified the role list is not fixed and must come from role profiles. - The implementation must remove hardcoded role selection as the source of truth.
- `2026-04-24 00:00` - Scoring must use Russian-facing terms and be finalized as part of implementation. - User requested an additional analysis instead of blindly copying the baseline formula. - The selected model is documented in tests and output labels.
- `2026-04-24 00:00` - New validation uses pytest. - The project already migrated from unittest to pytest. - All new test commands use `python -m pytest`.
- `2026-04-24 01:00` - Senior IT leadership scoring uses a hybrid model: requirement fit is primary, role profile and scope alignment are secondary, title is weak. - This prevents `Head of Development` wording from overriding an engineering-organization role such as Fintehrobot. - Selection remains data-driven through role profile signals rather than a fixed role list.

## Progress log

- `2026-04-24 00:00` - Plan created from the approved implementation request. - Validation pending. - Status: `in_progress`.
- `2026-04-24 00:10` - M1 completed: added initial root role profiles and updated the analyze-vacancy workflow contract. - Validation: `Get-ChildItem ..\..\knowledge\roles -File`; `Get-Content -Raw ..\..\agent_memory\workflows\analyze-vacancy.md`. - Status: `in_progress`.
- `2026-04-24 01:05` - M2-M4 completed: implemented LLM-backed analyze pipeline, rich adoptions intake, screening compatibility and CLI LLM options. - Validation: `python -m pytest tests/test_analyze_workflow.py`; `python -m pytest tests/test_adoptions_intake_workflow.py tests/test_prepare_screening_workflow.py tests/test_cli.py`; `python -m pytest tests`; real smoke for analyze/intake/prepare-screening on Fintehrobot. - Status: `done`.

## Current state

- Current milestone: `M4`
- Current status: `done`
- Next step: `No implementation step remains for this plan; monitor real LLM output quality on the next non-fake analyze-vacancy run.`
- Active blockers:
  - none
- Open questions:
  - none

## Completion summary

- Delivered data-driven role catalog selection, explainable scoring, LLM provider boundary, rich `analysis.md`, full draft `adoptions.md`, intake table preservation and screening compatibility.
- Validated with pytest only: targeted analyze/intake/prepare/CLI tests and full `python -m pytest tests` (`80 passed`).
- Real scenario smoke on `20260423-fintehrobot-head-of-development-rukovoditel-razrabotki` now selects `HoE`, writes the three-block analysis, imports adoptions and prepares screening.
- Residual risk: the fake provider is deterministic and useful for contract validation, but the first real OpenAI-compatible run should be reviewed for tone and factual-boundary quality.
