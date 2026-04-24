# Application Agent Config Docs

- Title: `Application Agent config docs`
- Slug: `2026-04-24-application-agent-config-docs`
- Owner: `Codex`
- Created: `2026-04-24`
- Last updated: `2026-04-24 10:57`
- Overall status: `done`

## Objective

The root workspace contains a usable `agent_memory/config/application-agent.json`, and the tool README documents every currently supported key plus the recommended LLM defaults for the current `analyze-vacancy` implementation.

## Background and context

The previous change added config loading for `analyze-vacancy`, but it did not create the root config file and the README only showed a short example. The current OpenAI provider uses the Chat Completions endpoint, sends `temperature`, and expects JSON object output. It does not yet support Responses API-only options such as reasoning effort.

## Scope

### In scope

- Create `agent_memory/config/application-agent.json` in the root workspace.
- Expand `tooling/application-agent/README.md` with a config parameter reference.
- Document the recommended `llm_*` defaults and why they fit the current workflow.
- Answer whether ChatGPT Plus tokens can be used instead of API billing.

### Out of scope

- Migrating the provider from Chat Completions to Responses API.
- Adding new `llm_*` runtime keys beyond the already supported config contract.
- Storing API keys in repository files.

## Assumptions

- The config file should contain only non-secret runtime defaults.
- The most compatible model recommendation should respect the current code path, not only the newest model list.

## Risks and unknowns

- OpenAI model availability changes over time; final answer should cite current official docs checked during the task.
- If the project later migrates to Responses API, the model recommendation should be revisited.

## External touchpoints

- `agent_memory/config/application-agent.json` - generation - root workspace runtime defaults.

## Milestones

### M1. Config file and docs

- Status: `done`
- Goal:
  - Add a concrete config and document its supported fields.
- Deliverables:
  - Root config JSON.
  - README config reference.
- Acceptance criteria:
  - Config is valid JSON.
  - README lists supported keys and precedence.
  - README explains why the default model is chosen.
- Validation commands:
  - `python -m pytest tests/test_cli.py`
  - `python -m json.tool agent_memory/config/application-agent.json`
- Notes / discoveries:
  - Current provider still uses Chat Completions, so config should not advertise unsupported Responses-only options.
  - OpenAI's current model docs list GPT-5.4 as the flagship model and GPT-5.4 mini/nano as cost/latency variants, but the current provider implementation has not yet migrated to Responses API.

## Decision log

- `2026-04-24 10:53` - Use `gpt-4.1` as the default config model for now because it is the safest fit for the current Chat Completions JSON-object implementation; document GPT-5.4 family as a future recommendation after provider migration.

## Progress log

- `2026-04-24 10:53` - Plan created. Status: `in_progress`.
- `2026-04-24 10:56` - Created root `agent_memory/config/application-agent.json` and expanded README config reference.
- `2026-04-24 10:57` - Validation passed: `python -m json.tool agent_memory/config/application-agent.json`; `python -m pytest tests/test_cli.py` - 12 passed.

## Current state

- Current milestone: `M1`
- Current status: `done`
- Next step: `Commit and push submodule and root updates.`
- Active blockers:
  - нет
- Open questions:
  - нет

## Completion summary

Delivered:

- Created root workspace config at `agent_memory/config/application-agent.json`.
- Expanded `README.md` with supported config keys, precedence, recommended `llm_*` values, and current implementation constraints.
- Verified JSON validity and CLI tests.

Validated:

- `python -m json.tool agent_memory/config/application-agent.json`
- `python -m pytest tests/test_cli.py` - 12 passed

Follow-up tasks:

- Consider a separate provider migration from Chat Completions to Responses API before adding `llm_reasoning_effort` or making GPT-5.4-family models the default.

Residual risks:

- OpenAI model availability changes over time; revisit the recommendation when changing the provider or model.
