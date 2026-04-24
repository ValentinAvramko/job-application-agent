# CLI LLM Config And Docs

- Title: `CLI LLM config and docs`
- Slug: `2026-04-24-cli-llm-config-docs`
- Owner: `Codex`
- Created: `2026-04-24`
- Last updated: `2026-04-24 10:50`
- Overall status: `done`

## Objective

`analyze-vacancy` can be run with stable LLM defaults from a workspace config file, and the README / workflow runbook clearly explain required parameters, optional parameters, and LLM setup.

## Background and context

Current CLI documents the quick start as `analyze-vacancy --vacancy-id ...`, but the default `llm_provider=openai` also requires `OPENAI_API_KEY` and an LLM model. The workflow code has an environment fallback for `APPLICATION_AGENT_LLM_MODEL`, but users cannot place runtime defaults in a workspace config file.

The user hit `AnalyzeVacancyError: OPENAI_API_KEY is required for llm_provider=openai.` after running `analyze-vacancy` with only `--vacancy-id`.

## Scope

### In scope

- Add a small CLI config loader for workflow defaults.
- Support `analyze-vacancy` LLM defaults from a workspace config file.
- Preserve explicit CLI options as higher priority than config values.
- Update README and `agent_memory/workflows/analyze-vacancy.md` documentation.
- Add tests for config loading / precedence.

### Out of scope

- Secret storage or automatic API key management.
- Changing the OpenAI request implementation.
- Changing analysis output quality or prompt structure.

## Assumptions

- API keys remain environment variables, not committed config values.
- A JSON config is enough because the CLI already uses JSON output and the stdlib parser needs no new dependency.
- Default config path should live in the private workspace root, not inside the public tool repository.

## Risks and unknowns

- Existing users may rely on CLI defaults; defaults must remain backward compatible.
- Config parsing errors must be explicit enough to diagnose quickly.

## External touchpoints

- `agent_memory/workflows/analyze-vacancy.md` in the root workspace - update documentation for the workflow contract.
- `agent_memory/config/application-agent.json` in the root workspace - documented runtime config path, not created automatically with secrets.

## Milestones

### M1. CLI config support

- Status: `done`
- Goal:
  - Let `analyze-vacancy` consume LLM defaults from config.
- Deliverables:
  - CLI config loader.
  - `--config` global option and default config lookup.
  - CLI tests.
- Acceptance criteria:
  - Explicit CLI values override config values.
  - Missing config is allowed.
  - Malformed config fails clearly.
- Validation commands:
  - `python -m pytest tests/test_cli.py`
- Notes / discoveries:
  - Existing env fallback for `APPLICATION_AGENT_LLM_MODEL` remains in workflow layer.
  - Config is loaded only for `analyze-vacancy`, so optional config issues do not block unrelated commands.

### M2. Documentation

- Status: `done`
- Goal:
  - Make required inputs and LLM setup visible before the user runs the command.
- Deliverables:
  - Updated `README.md`.
  - Updated root workflow runbook.
- Acceptance criteria:
  - README shows `OPENAI_API_KEY`, model config, config file path, and a fake-provider smoke example.
  - Workflow runbook separates required and optional parameters.
- Validation commands:
  - `python -m pytest tests/test_cli.py`
- Notes / discoveries:
  - README now documents `OPENAI_API_KEY`, model sources, config path, CLI precedence, and fake-provider smoke runs.
  - Root workflow runbook now separates required and optional inputs.

## Decision log

- `2026-04-24 10:39` - Use workspace-local JSON config at `agent_memory/config/application-agent.json` so runtime defaults stay outside the public tool repo and require no new dependency.
- `2026-04-24 10:45` - Keep API keys out of config; only provider/model/temperature and workflow defaults belong in the JSON file.

## Progress log

- `2026-04-24 10:39` - Plan created. Status: `in_progress`.
- `2026-04-24 10:44` - Implemented config support and CLI tests. `python -m pytest tests/test_cli.py`: 12 passed.
- `2026-04-24 10:45` - Updated README and root runbook. `python -m pytest tests`: 84 passed.
- `2026-04-24 10:50` - Published submodule commit `46aebad` and root commit `3dd7696`; left unrelated root untracked file `archive/analyze_01.md` untouched.

## Current state

- Current milestone: `M2`
- Current status: `done`
- Next step: `No further action; task is complete.`
- Active blockers:
  - нет
- Open questions:
  - нет

## Completion summary

Delivered:

- CLI support for workspace config defaults at `agent_memory/config/application-agent.json`.
- `analyze-vacancy` LLM defaults can now come from config, while explicit CLI arguments still override config values.
- README and root workflow documentation now explain required parameters and LLM setup.
- Tests added for config defaults, CLI precedence, and invalid JSON config diagnostics.

Validated:

- `python -m pytest tests/test_cli.py` — 12 passed.
- `python -m pytest tests` — 84 passed.

Follow-up tasks:

- none

Residual risks:

- `include_employer_channels` can be enabled by config or CLI flag; there is no explicit negative CLI flag to override a config value back to false.

Root artifacts touched:

- `agent_memory/workflows/analyze-vacancy.md`
