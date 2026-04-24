# Application Agent config docs

- Название: `Application Agent config docs`
- Slug: `2026-04-24-application-agent-config-docs`
- Ответственный: `Codex`
- Создан: `2026-04-24`
- Обновлен: `2026-04-24 10:57`
- Общий статус: `done`

## Цель

В root workspace есть рабочий `agent_memory/config/application-agent.json`, а README инструмента документирует каждый поддерживаемый ключ и рекомендуемые LLM defaults для текущей реализации `analyze-vacancy`.

## Контекст

Предыдущая правка добавила config loading для `analyze-vacancy`, но не создала root config file, а README показывал только короткий пример. На тот момент OpenAI provider использовал Chat Completions endpoint, отправлял `temperature` и ожидал JSON object output. Он еще не поддерживал Responses API-only options, например reasoning effort.

## Границы

### Входит в scope

- Создать `agent_memory/config/application-agent.json` в root workspace.
- Расширить `tooling/application-agent/README.md` reference по config parameters.
- Документировать рекомендуемые `llm_*` defaults и почему они подходят текущему workflow.
- Ответить, можно ли использовать ChatGPT Plus tokens вместо API billing.

### Не входит в scope

- Миграция provider с Chat Completions на Responses API.
- Добавление новых `llm_*` runtime keys сверх уже поддержанного config contract.
- Хранение API keys в repository files.

## Допущения

- Config file должен содержать только non-secret runtime defaults.
- Наиболее совместимая model recommendation должна учитывать текущий code path, а не только самый новый model list.

## Риски и неизвестные

- OpenAI model availability меняется со временем; финальный ответ должен ссылаться на текущие official docs, проверенные во время задачи.
- Если проект позже мигрирует на Responses API, model recommendation нужно пересмотреть.

## Внешние точки касания

- `agent_memory/config/application-agent.json` - генерация - root workspace runtime defaults.

## Этапы

### M1. Config file и docs

- Статус: `done`
- Цель:
  - Добавить конкретный config и документировать поддерживаемые поля.
- Артефакты:
  - Root config JSON.
  - README config reference.
- Критерии приемки:
  - Config является валидным JSON.
  - README перечисляет supported keys и precedence.
  - README объясняет, почему выбран default model.
- Команды валидации:
  - `python -m pytest tests/test_cli.py`
  - `python -m json.tool agent_memory/config/application-agent.json`
- Заметки / находки:
  - Текущий provider все еще использует Chat Completions, поэтому config не должен рекламировать unsupported Responses-only options.
  - Текущие OpenAI model docs указывают GPT-5.4 как flagship model, а GPT-5.4 mini/nano как варианты для cost/latency, но текущая provider implementation еще не мигрировала на Responses API.

## Журнал решений

- `2026-04-24 10:53` - Использовать `gpt-4.1` как default config model на этот момент, потому что это самый безопасный вариант для текущей Chat Completions JSON-object implementation; GPT-5.4 family документировать как будущую рекомендацию после provider migration.

## Журнал прогресса

- `2026-04-24 10:53` - План создан. Статус: `in_progress`.
- `2026-04-24 10:56` - Создан root `agent_memory/config/application-agent.json` и расширен README config reference.
- `2026-04-24 10:57` - Валидация прошла: `python -m json.tool agent_memory/config/application-agent.json`; `python -m pytest tests/test_cli.py` - 12 passed.

## Текущее состояние

- Текущий milestone: `M1`
- Текущий статус: `done`
- Следующий шаг: `Выполнить commit и push submodule и root updates.`
- Активные блокеры:
  - нет
- Открытые вопросы:
  - нет

## Итог завершения

Поставлено:

- Создан root workspace config по пути `agent_memory/config/application-agent.json`.
- `README.md` расширен supported config keys, precedence, recommended `llm_*` values и current implementation constraints.
- Проверены JSON validity и CLI tests.

Провалидировано:

- `python -m json.tool agent_memory/config/application-agent.json`
- `python -m pytest tests/test_cli.py` - 12 passed

Последующие задачи:

- Рассмотреть отдельную provider migration с Chat Completions на Responses API перед добавлением `llm_reasoning_effort` или переводом GPT-5.4-family models в default.

Остаточные риски:

- OpenAI model availability меняется со временем; recommendation нужно пересматривать при изменении provider или model.
