# Восстановление модульного prompt layer `analyze-vacancy`

- Название: `восстановление модульного prompt layer analyze-vacancy`
- Slug: `2026-04-28-analyze-vacancy-prompt-layer-restoration`
- Ответственный: `Codex`
- Создан: `2026-04-28`
- Обновлен: `2026-04-28 23:59`
- Общий статус: `done`

## Цель

Восстановить качество `analyze-vacancy` до уровня мастер-промпта `promts/promt-analyze-vacancies-and-respond.md`, не сжимая его в короткую памятку.

После завершения workflow будет собирать модульный prompt bundle из отдельных runtime prompt-файлов: системная роль, orchestration задачи, выбор резюме, контракт анализа, контракт письма, контракт адаптации резюме и отдельная рамка humanizer-pass.

## Контекст

Текущий `analyze-vacancy` уже имеет техническую защиту от mojibake, отдельный humanizer-pass, подпись из `profile/contact-regions.yml`, `cover_letter_evidence` и quality-mode config. Остаточный риск находится в prompt-content layer: root overrides стали слишком короткими и не наследуют полный смысловой контракт мастер-промпта.

Код workflow находится в `./tooling/application-agent`, но реальные root overrides лежат в корневом workspace в `agent_memory/prompts/analyze-vacancy/`.

## Границы

### Входит в scope

- Расширение `AnalyzePromptBundle` до модульного набора prompt-файлов.
- Синхронизация packaged defaults и root overrides.
- Перенос содержательных блоков мастер-промпта в runtime prompts без примитивизации.
- Использование отдельного `humanizer-pass.ru.md` вместо hardcoded task-specific humanizer instructions в коде.
- Policy tests для защиты prompt layer от повторного упрощения.

### Не входит в scope

- Изменение JSON schema результата за пределами уже существующего `cover_letter_evidence`.
- Создание отдельного пользовательского артефакта для `cover_letter_evidence`.
- Выделение новых CLI-шагов `analyze-vacancy`.
- Переписывание workflow адаптации резюме за пределами prompt contract.

## Допущения

- `promts/promt-analyze-vacancies-and-respond.md` является содержательным source of truth.
- Root overrides и packaged defaults на этом этапе должны иметь одинаковый набор файлов и одинаковые обязательные блоки.
- `humanize-russian-business-text` остается источником редакторской политики; prompt `humanizer-pass.ru.md` только задает рамку отдельного прохода.

## Риски и неизвестные

- Слишком длинный prompt payload может увеличить стоимость и длительность OpenAI-вызова.
- Семантический golden test не доказывает качество письма полностью, но ловит повторную потерю ключевых признаков варианта 5.
- Если root override и fallback разойдутся после этой задачи, реальные и тестовые запуски снова будут жить по разным контрактам.

## Внешние точки касания

- `agent_memory/prompts/analyze-vacancy/` - обновление - live root prompt overrides для реального `analyze-vacancy`.
- `promts/promt-analyze-vacancies-and-respond.md` - чтение - источник смыслового контракта.
- `vacancies/20260423-fintehrobot-head-of-development-rukovoditel-razrabotki/` - проверка / генерация - smoke и ручная оценка качества.

## Этапы

### M1. Модульный prompt bundle

- Статус: `done`
- Цель:
  - Расширить runtime prompt bundle и OpenAI payload до модульного набора.
- Артефакты:
  - `src/application_agent/workflows/analyze_vacancy.py`
  - `src/application_agent/data/prompts/analyze-vacancy/`
  - `agent_memory/prompts/analyze-vacancy/`
- Критерии приемки:
  - Workflow загружает все prompt modules.
  - Root override сохраняет приоритет над packaged fallback.
  - Humanizer-pass использует prompt file, а не hardcoded task-specific instructions.
- Команды валидации:
  - `python -m pytest tests/test_analyze_workflow.py -q`
- Заметки:
  - `AnalyzePromptBundle` расширен до модульного набора; OpenAI payload передает отдельные контракты выбора резюме, анализа, письма и адаптации.
  - Humanizer-pass использует `humanizer-pass.ru.md` как system prompt.
  - После расширения prompt payload основной OpenAI timeout увеличен до 600 секунд, humanizer timeout - до 300 секунд.

### M2. Prompt policy tests

- Статус: `done`
- Цель:
  - Защитить runtime prompts от повторной примитивизации.
- Артефакты:
  - `tests/test_prompt_contract_policy.py`
- Критерии приемки:
  - Тесты проверяют наличие всех modules в root и fallback.
  - Тесты проверяют обязательные блоки, отсутствие placeholders и mojibake.
  - Тесты проверяют, что `humanizer-pass.ru.md` не дублирует skill.
- Команды валидации:
  - `python -m pytest tests/test_prompt_contract_policy.py -q`
- Заметки:
  - Добавлены проверки полного набора prompt modules, синхронизации root/fallback, обязательных маркеров, mojibake, служебных маркеров и недублирования skill в humanizer prompt.

### M3. Semantic quality fixture

- Статус: `done`
- Цель:
  - Добавить проверку письма по Fintehrobot на смысловые признаки варианта 5.
- Артефакты:
  - `tests/test_analyze_workflow.py`
- Критерии приемки:
  - Проверяется HoE / engineering organization framing.
  - Проверяется подтвержденная фактура про 30+ инженеров, delivery, reliability, DORA и platform context.
  - Проверяется честная обработка fintech-domain gap.
  - Запрещаются шаблонная самореклама, пересказ вакансии и unsupported claims.
- Команды валидации:
  - `python -m pytest tests/test_analyze_workflow.py -q`
  - `python -m pytest tests -q`
- Заметки:
  - В `test_analyze_workflow.py` добавлена семантическая проверка Fintehrobot fixture на HoE framing, 30+/35+ scope, DORA/platform evidence и запрет явных рекламных claims.

## Журнал решений

- `2026-04-28 23:55` - Prompt layer делается модульным, а не расширяется только в трех старых файлах. - Это упростит поддержку контрактов и будущую декомпозицию workflow на отдельные шаги.
- `2026-04-28 23:55` - `cover_letter_evidence` остается внутри `analysis.md`, без отдельного пользовательского артефакта. - Пользовательская ценность отдельного файла неочевидна, а встроенный раздел сохраняет проверяемость.
- `2026-04-28 23:55` - Humanizer-pass prompt не должен дублировать skill. - Skill остается источником редакторской политики, prompt задает только рамку отдельного прохода.
- `2026-04-28 23:56` - После расширения prompt payload увеличены timeout OpenAI-вызовов. - Реальный quality-mode с модульным prompt не уложился в 240 секунд. - Основной pass теперь допускает до 600 секунд, humanizer-pass до 300 секунд.

## Журнал прогресса

- `2026-04-28 23:55` - План создан. Статус: `in_progress`.
- `2026-04-28 23:56` - M1-M3 реализованы: добавлены prompt modules, обновлен OpenAI payload, root overrides синхронизированы с packaged defaults, добавлены policy и semantic tests. Targeted validation: `15 passed`.
- `2026-04-28 23:57` - Full suite после реализации: `95 passed`.
- `2026-04-28 23:58` - Первый реальный smoke run дошел до OpenAI, но упал по timeout 240 секунд; после увеличения timeout повторный smoke run завершился успешно.
- `2026-04-28 23:59` - Ручная проверка smoke: HoE выбран, `cover_letter_evidence` есть, подпись ровно две, `humanizer_pass_applied: true`, финтех-gap обозначен явно, ключевая фактура письма присутствует. Статус: `done`.

## Текущее состояние

- Текущий milestone: `M3`
- Текущий статус: `done`
- Следующий шаг: `Выполнить финальный полный pytest перед commit/push`
- Активные блокеры:
  - нет
- Открытые вопросы:
  - нет

## Итог завершения

Поставлено:

- модульный runtime prompt bundle для `analyze-vacancy`;
- синхронизированные root overrides и packaged defaults;
- отдельный `humanizer-pass.ru.md` вместо hardcoded task-specific humanizer instructions;
- prompt policy tests;
- semantic Fintehrobot fixture;
- увеличенные timeout для quality-mode OpenAI-вызовов.

Провалидировано:

- `python -m pytest tests/test_prompt_contract_policy.py tests/test_analyze_workflow.py -q` -> `15 passed`;
- `python -m pytest tests -q` -> `95 passed`;
- реальный `analyze-vacancy` по Fintehrobot завершился успешно после увеличения timeout.

Остаточный риск: качество письма по-прежнему требует человеческого review перед отправкой, но prompt layer больше не является короткой выжимкой и защищен policy tests от повторной примитивизации.
