# Конфигурируемый русский prompt contract и обязательный skill

- Название: `конфигурируемый русский prompt contract и обязательный skill`
- Slug: `2026-04-24-configurable-russian-prompt-skill-contract`
- Ответственный: `Codex`
- Создан: `2026-04-24`
- Обновлен: `2026-04-24 16:30`
- Общий статус: `done`

## Цель

Сделать так, чтобы `analyze-vacancy` не хранил текстовые prompt-инструкции в Python-коде, использовал русскоязычные prompt-файлы и обязательно подмешивал skill `humanize-russian-business-text` при генерации русскоязычных текстовых результатов.

## Контекст

Предыдущая правка закрепила часть правил письма в `build_cover_letter_contract`, но это не удовлетворяет product contract:

- skill должен использоваться строго обязательно;
- skill должен применяться не только к сопроводительным письмам, а ко всем русскоязычным текстам, которые генерирует агент;
- prompt-тексты должны быть редактируемыми без правки Python-модуля;
- legacy prompt сейчас подробнее и полезнее короткого contract в коде;
- prompt-тексты на английском для русскоязычного workflow нежелательны.

## Границы

### Входит в scope

- Вынести runtime prompt-тексты `analyze-vacancy` в русскоязычные конфигурационные `.md`-файлы.
- Добавить root override-layer `agent_memory/prompts/analyze-vacancy/`.
- Загружать skill `humanize-russian-business-text` как обязательный runtime input для русскоязычного результата.
- Дать возможность переопределить путь к skill через CLI/config.
- Обновить тесты и workflow docs.

### Не входит в scope

- Полный перенос всех deterministic templates всех workflow в prompt config.
- Переписывание уже созданных `analysis.md`.
- Автоматическое редактирование самого skill-файла.

## Допущения

- Для текущей задачи достаточно закрыть LLM-backed генерацию `analyze-vacancy`, потому что именно она создаёт письма и rich русскоязычные текстовые блоки.
- Базовые prompt-файлы могут поставляться вместе с пакетом, а root `agent_memory/prompts/analyze-vacancy/` может переопределять их без изменения кода.
- Если язык результата русский и skill-файл не найден, workflow должен завершаться явной ошибкой.

## Риски и неизвестные

- Полная обязательность skill для всех будущих workflow потребует отдельного общего prompt/service слоя.
- Передача полного skill-текста увеличивает размер LLM input, но это сознательно выбранная зависимость.

## Внешние точки касания

- `C:\Users\avramko\OneDrive\Documents\Career\agent_memory\prompts\analyze-vacancy\` - обновление - root override prompt-файлы.
- `C:\Users\avramko\OneDrive\Documents\Career\agent_memory\config\application-agent.json` - обновление - путь к обязательному skill.
- `C:\Users\avramko\.agents\skills\humanize-russian-business-text\SKILL.md` - чтение - обязательный runtime skill для русскоязычной генерации.
- `C:\Users\avramko\OneDrive\Documents\Career\agent_memory\workflows\analyze-vacancy.md` - обновление - operator-facing contract.

## Этапы

### M1. Prompt-файлы и обязательный skill для analyze-vacancy

- Статус: `done`
- Цель:
  - Перенести prompt-тексты в файлы, подключить обязательный skill и покрыть поведение тестами.
- Артефакты:
  - `src/application_agent/data/prompts/analyze-vacancy/*.md`
  - `src/application_agent/workflows/analyze_vacancy.py`
  - `src/application_agent/cli.py`
  - `tests/test_analyze_workflow.py`
  - `tests/test_cli.py`
  - `agent_memory/prompts/analyze-vacancy/*.md`
  - `agent_memory/config/application-agent.json`
  - `agent_memory/workflows/analyze-vacancy.md`
- Критерии приемки:
  - в `analyze_vacancy.py` не остаётся длинного английского prompt/contract текста;
  - LLM payload содержит текст skill и русскоязычные prompt-файлы;
  - root prompt override работает без изменения кода;
  - отсутствие skill для русского результата даёт явную ошибку;
  - full pytest suite проходит.
- Команды валидации:
  - `python -m pytest tests/test_analyze_workflow.py tests/test_cli.py`
  - `python -m pytest tests`
- Заметки:
  - prompt-тексты вынесены в `src/application_agent/data/prompts/analyze-vacancy/*.md` и root overrides `agent_memory/prompts/analyze-vacancy/*.md`;
  - `analyze-vacancy` загружает root override, если он есть, иначе packaged default;
  - для русского результата workflow обязательно читает skill `humanize-russian-business-text` и передаёт его текст в LLM payload;
  - CLI/config поддерживает `russian_text_skill_path`;
  - full validation: `python -m pytest tests` -> `89 passed`.

## Журнал решений

- `2026-04-24 16:05` - Базовые prompt-файлы хранятся в package data, root `agent_memory/prompts/analyze-vacancy/` имеет приоритет. - Это даёт рабочие defaults и возможность оперативно менять prompt без правки кода.
- `2026-04-24 16:05` - Skill передаётся в LLM payload целиком. - Это соответствует требованию строгого использования подробных правил skill.

## Журнал прогресса

- `2026-04-24 16:05` - План создан, M1 начат. - Валидация pending. - Статус: `in_progress`.
- `2026-04-24 16:30` - M1 завершён: prompt-файлы, обязательная загрузка skill, CLI/config, docs и tests обновлены. - Валидация: `python -m pytest tests/test_analyze_workflow.py tests/test_cli.py` -> `24 passed`; `python -m pytest tests` -> `89 passed`. - Статус: `done`.

## Текущее состояние

- Текущий milestone: `M1`
- Текущий статус: `done`
- Следующий шаг: `Следующих implementation steps по этому плану нет.`
- Активные блокеры:
  - нет
- Открытые вопросы:
  - нет

## Итог завершения

- Runtime prompt-тексты `analyze-vacancy` вынесены из Python-кода в русскоязычные markdown-файлы.
- Root `agent_memory/prompts/analyze-vacancy/` теперь является оперативно редактируемым prompt override-layer.
- Skill `humanize-russian-business-text` стал обязательным runtime input для русскоязычной генерации.
- `agent_memory/config/application-agent.json` содержит путь к skill.
- Валидация завершена: targeted tests и full pytest suite проходят.
