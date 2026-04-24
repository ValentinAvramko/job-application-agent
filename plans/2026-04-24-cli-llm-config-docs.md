# CLI LLM config и docs

- Название: `CLI LLM config и docs`
- Slug: `2026-04-24-cli-llm-config-docs`
- Ответственный: `Codex`
- Создан: `2026-04-24`
- Обновлен: `2026-04-24 10:50`
- Общий статус: `done`

## Цель

`analyze-vacancy` можно запускать со стабильными LLM-дефолтами из workspace config-файла, а README и workflow runbook ясно объясняют обязательные параметры, опциональные параметры и LLM setup.

## Контекст

До этой правки CLI документировал quick start как `analyze-vacancy --vacancy-id ...`, но default `llm_provider=openai` также требовал `OPENAI_API_KEY` и LLM model. В workflow-коде был environment fallback для `APPLICATION_AGENT_LLM_MODEL`, но пользователь не мог хранить runtime defaults в workspace config-файле.

Пользователь получил `AnalyzeVacancyError: OPENAI_API_KEY is required for llm_provider=openai.` после запуска `analyze-vacancy` только с `--vacancy-id`.

## Границы

### Входит в scope

- Добавить небольшой CLI config loader для workflow defaults.
- Поддержать LLM defaults для `analyze-vacancy` из workspace config-файла.
- Сохранить более высокий приоритет явных CLI options над config values.
- Обновить документацию в README и `agent_memory/workflows/analyze-vacancy.md`.
- Добавить tests для config loading и precedence.

### Не входит в scope

- Secret storage или automatic API key management.
- Изменение OpenAI request implementation.
- Изменение качества analysis output или prompt structure.

## Допущения

- API keys остаются environment variables, а не committed config values.
- JSON config достаточно, потому что CLI уже использует JSON output, а stdlib parser не требует новой зависимости.
- Default config path должен жить в private workspace root, а не внутри public tool repository.

## Риски и неизвестные

- Existing users могут полагаться на CLI defaults; defaults должны остаться backward compatible.
- Config parsing errors должны быть достаточно явными для быстрой диагностики.

## Внешние точки касания

- `agent_memory/workflows/analyze-vacancy.md` в root workspace - обновление documentation для workflow contract.
- `agent_memory/config/application-agent.json` в root workspace - documented runtime config path, не создается автоматически с secrets.

## Этапы

### M1. Поддержка CLI config

- Статус: `done`
- Цель:
  - Позволить `analyze-vacancy` читать LLM defaults из config.
- Артефакты:
  - CLI config loader.
  - Global option `--config` и default config lookup.
  - CLI tests.
- Критерии приемки:
  - Явные CLI values переопределяют config values.
  - Missing config допустим.
  - Malformed config падает понятной ошибкой.
- Команды валидации:
  - `python -m pytest tests/test_cli.py`
- Заметки / находки:
  - Existing env fallback для `APPLICATION_AGENT_LLM_MODEL` остается на workflow layer.
  - Config загружается только для `analyze-vacancy`, поэтому optional config issues не блокируют unrelated commands.

### M2. Документация

- Статус: `done`
- Цель:
  - Сделать required inputs и LLM setup видимыми до запуска команды.
- Артефакты:
  - Обновленный `README.md`.
  - Обновленный root workflow runbook.
- Критерии приемки:
  - README показывает `OPENAI_API_KEY`, model config, config file path и fake-provider smoke example.
  - Workflow runbook разделяет required и optional parameters.
- Команды валидации:
  - `python -m pytest tests/test_cli.py`
- Заметки / находки:
  - README теперь документирует `OPENAI_API_KEY`, model sources, config path, CLI precedence и fake-provider smoke runs.
  - Root workflow runbook теперь разделяет required и optional inputs.

## Журнал решений

- `2026-04-24 10:39` - Использовать workspace-local JSON config по пути `agent_memory/config/application-agent.json`, чтобы runtime defaults оставались вне public tool repo и не требовали новой зависимости.
- `2026-04-24 10:45` - Не хранить API keys в config; в JSON file должны быть только provider/model/temperature и workflow defaults.

## Журнал прогресса

- `2026-04-24 10:39` - План создан. Статус: `in_progress`.
- `2026-04-24 10:44` - Реализованы config support и CLI tests. `python -m pytest tests/test_cli.py`: 12 passed.
- `2026-04-24 10:45` - Обновлены README и root runbook. `python -m pytest tests`: 84 passed.
- `2026-04-24 10:50` - Опубликованы submodule commit `46aebad` и root commit `3dd7696`; unrelated root untracked file `archive/analyze_01.md` оставлен нетронутым.

## Текущее состояние

- Текущий milestone: `M2`
- Текущий статус: `done`
- Следующий шаг: `Дальнейших действий по этому плану нет; задача завершена.`
- Активные блокеры:
  - нет
- Открытые вопросы:
  - нет

## Итог завершения

Поставлено:

- CLI support для workspace config defaults по пути `agent_memory/config/application-agent.json`.
- LLM defaults для `analyze-vacancy` теперь могут приходить из config; явные CLI arguments по-прежнему переопределяют config values.
- README и root workflow documentation объясняют required parameters и LLM setup.
- Добавлены tests для config defaults, CLI precedence и invalid JSON config diagnostics.

Провалидировано:

- `python -m pytest tests/test_cli.py` - 12 passed.
- `python -m pytest tests` - 84 passed.

Последующие задачи:

- нет

Остаточные риски:

- `include_employer_channels` можно включить через config или CLI flag; явного negative CLI flag, чтобы переопределить config value обратно в false, нет.

Затронутые root-артефакты:

- `agent_memory/workflows/analyze-vacancy.md`
