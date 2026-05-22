# Команда `check-response-monitoring`

- Название: `check-response-monitoring`
- Slug: `2026-05-21-check-response-monitoring`
- Ответственный: `Codex`
- Создан: `2026-05-21`
- Обновлен: `2026-05-21 14:14`
- Общий статус: `done`

## Цель

Добавить runtime workflow и CLI-команду `check-response-monitoring`, которая проверяет активные строки в корневом `response-monitoring.xlsx`, обновляет `Активна` и `Обновлена` по данным страниц вакансий, выводит журнал изменений в консоль и сохраняет тот же журнал в файл.

## Контекст

Код инструмента находится в `./tooling/application-agent`. Существующий модуль `src/application_agent/integrations/response_monitoring.py` уже умеет читать лист `Данные`, добавлять строки ingest и обновлять колонку `E=Обновлена`. Существующий слой `src/application_agent/workflows/vacancy_sources.py` уже умеет извлекать дату публикации/обновления для HH и generic `JobPosting`.

Задача добавляет отдельный maintenance workflow, который читает и потенциально обновляет корневой `response-monitoring.xlsx`. Реальный workbook не должен изменяться во время разработки, кроме явного запуска новой команды пользователем или smoke-теста на копии.

## Границы

### Входит в scope

- CLI/workflow `check-response-monitoring` с опциями `--log-file` и `--dry-run`.
- Пакетное обновление `D=Активна` и `E=Обновлена` в `response-monitoring.xlsx`.
- Классификация результата проверки страницы: активна, неактивна, требует авторизации, временный сбой, дата не найдена.
- Логирование всех изменений и предупреждений в консоль и файл.
- Unit/CLI tests для workbook helpers, source status и команды.

### Не входит в scope

- Автоматический запуск проверки по расписанию.
- Изменение схемы `response-monitoring.xlsx` или добавление новых колонок.
- Массовая проверка реального workbook как часть тестов.
- Обход авторизации или хранение credentials для сайтов вакансий.

## Допущения

- `401`, `403`, `404`, `410`, явные inactive/archived markers и login/password screen переводят строку в `Активна = Нет`.
- Timeout, DNS/connect errors, `429` и `5xx` считаются временными сбоями и не меняют `Активна`.
- Если дата страницы не извлечена, `Обновлена` не меняется и в лог пишется warning.
- Для `--dry-run` команда выполняет все проверки и пишет лог, но workbook не изменяет.

## Риски и неизвестные

- Live-доступ к HH и карьерным сайтам может давать `403`, rate limit или отличаться от тестовых HTML/API fixtures.
- HTML-маркеры login/password и inactive pages неполные; реализация должна быть консервативной и покрыта расширяемыми helper functions.
- Низкоуровневая запись XLSX должна сохранить существующие стили и колонки `A:Q`.

## Внешние точки касания

- `response-monitoring.xlsx` в корне workspace - чтение / обновление / проверка - источник активных строк и целевой файл обновления.
- `agent_memory/runtime/check-response-monitoring/` в корне workspace - генерация - место хранения логов запусков.

## Этапы

### M1. План и контракты helpers

- Статус: `done`
- Цель:
  - Зафиксировать план, добавить workbook helpers и source status classification.
- Артефакты:
  - `plans/2026-05-21-check-response-monitoring.md`
  - `src/application_agent/integrations/response_monitoring.py`
  - `src/application_agent/workflows/vacancy_sources.py`
  - `tests/test_ingest_workflow.py`
- Критерии приемки:
  - Активные строки читаются с нормализованным значением `Обновлена`.
  - Пакетное обновление меняет `D` и `E` без затрагивания остальных колонок.
  - Source status helpers различают inactive/auth/not found/transient cases.
- Команды валидации:
  - `pytest tests\test_ingest_workflow.py`
- Заметки:
  - `pytest tests\test_ingest_workflow.py`: 33 passed.

### M2. Workflow, CLI и документация

- Статус: `done`
- Цель:
  - Добавить workflow, CLI-команду, регистрацию и README.
- Артефакты:
  - `src/application_agent/workflows/check_response_monitoring.py`
  - `src/application_agent/workflows/registry.py`
  - `src/application_agent/cli.py`
  - `README.md`
  - `tests/test_cli.py`
- Критерии приемки:
  - `list-workflows` показывает `check-response-monitoring`.
  - Команда пишет лог, выводит тот же лог в консоль и поддерживает `--dry-run`.
  - Workflow пишет runtime memory run и возвращает log artifact.
- Команды валидации:
  - `pytest tests\test_cli.py`
- Заметки:
  - `pytest tests\test_ingest_workflow.py`: 35 passed.
  - `pytest tests\test_cli.py`: 14 passed.

### M3. Полная проверка и завершение

- Статус: `done`
- Цель:
  - Проверить весь набор тестов, обновить план и проверить diff/status.
- Артефакты:
  - `plans/2026-05-21-check-response-monitoring.md`
- Критерии приемки:
  - Targeted и full tests проходят.
  - Реальный `response-monitoring.xlsx` не изменен.
  - План содержит результаты валидации и итог.
- Команды валидации:
  - `pytest tests`
  - `git diff --stat`
  - `git status --short --branch`
- Заметки:
  - Первый `pytest tests`: 1 failure в `tests/test_memory_store.py`, expectation не включал новый workflow в runtime catalog.
  - После обновления expectation `pytest tests`: 107 passed.
  - `git diff -- response-monitoring.xlsx`: пусто, рабочий workbook не изменен.

## Журнал решений

- `2026-05-21 13:46` - Команда называется `check-response-monitoring`; недоступность из-за login/password screen считается причиной деактивации, временные сетевые сбои только логируются.
- `2026-05-21 14:08` - Новый workflow добавлен в runtime catalog; тест memory store обновлен под расширенный список workflow.

## Журнал прогресса

- `2026-05-21 13:46` - План создан. Статус: `in_progress`.
- `2026-05-21 13:55` - M1 завершен: добавлены helpers для `D/E`, нормализация даты `E`, source status classification и тесты. Валидация: `pytest tests\test_ingest_workflow.py` - 33 passed. Статус: `in_progress`.
- `2026-05-21 14:03` - M2 завершен: добавлены workflow, CLI, registry, README и тесты dry-run/console log. Валидация: `pytest tests\test_ingest_workflow.py` - 35 passed; `pytest tests\test_cli.py` - 14 passed. Статус: `in_progress`.
- `2026-05-21 14:08` - M3 завершен: полный набор тестов прошел после обновления expectation runtime catalog. Валидация: `pytest tests` - 107 passed. Статус: `done`.

## Текущее состояние

- Текущий milestone: `none`
- Текущий статус: `done`
- Следующий шаг: `проверить финальный diff/status и подготовить handoff`
- Активные блокеры:
  - нет
- Открытые вопросы:
  - нет

## Итог завершения

Поставлено:

- CLI/workflow `check-response-monitoring` с `--log-file` и `--dry-run`.
- Пакетное обновление `D=Активна` и `E=Обновлена` для активных строк `response-monitoring.xlsx`.
- Source status classification для active/inactive/auth/not_found/transient/warning cases.
- Журнал проверки, который выводится в консоль новой CLI-команды и сохраняется в файл.
- Документация README и тестовое покрытие для helpers, workflow, CLI и runtime catalog.

Проверено:

- `pytest tests\test_ingest_workflow.py`: 35 passed.
- `pytest tests\test_cli.py`: 14 passed.
- `pytest tests`: 107 passed.
- `git diff -- response-monitoring.xlsx`: пусто.

Дальнейшие действия:

- Smoke-проверку на копии реального `response-monitoring.xlsx` можно выполнить отдельно, если нужен фактический прогон по внешним сайтам.

## Исправление `2026-05-22`: пропуск архивного HH-статуса в видимом заголовке

Проблема: строка `351` в реальном `response-monitoring.xlsx` с URL `https://hh.ru/vacancy/132520570` осталась активной, хотя ручная проверка показывает архивный статус. Точечное воспроизведение показало, что HH API может вернуть `403`, после чего HTML fallback доступен и парсится как активная страница, несмотря на видимый текст `В архиве с 22 мая 2026` в `h1` и `title`.

Решение: сохранить защиту от ложной деактивации по скрытым HH HTML-шаблонам, но добавить отдельную HH-проверку архивного статуса только по видимым верхнеуровневым сигналам страницы (`title` и `h1`). Общий поиск inactive-маркеров по всему HTML для HH не возвращается.

Проверка:

- `pytest tests\test_ingest_workflow.py`: 37 passed.
- `python job-application-agent.py --root ../.. check-response-monitoring --dry-run --log-file agent_memory/runtime/check-response-monitoring/20260522-fix-dry-run.log`: `processed=72 deactivated=11 updated_dates=0 unchanged=61 warnings=0`, workbook не изменён.
- `pytest tests`: 109 passed.

Текущее состояние:

- Текущий milestone: `M4`
- Текущий статус: `done`
- Следующий шаг: проверить diff/status и подготовить handoff
- Активные блокеры: нет

## Исправление `2026-05-21`: ложная деактивация HH

Проблема: dry-run по реальному `response-monitoring.xlsx` предложил деактивировать большинство активных HH-вакансий с причиной `inactive vacancy marker detected`. Выборочная ручная проверка показала, что эти вакансии открываются и активны.

Решение: для HH HTML fallback не использовать общий поиск inactive-маркеров по всему HTML. HH-страницы могут содержать текст архивной страницы в скрытых шаблонах или служебных блоках. Деактивация HH должна опираться на `archived=true` из HH API, `404/410`, а также auth/login-сигналы; если API вернул `401/403`, но HTML страницы доступен, строка остается активной.

Проверка:

- `pytest tests\test_ingest_workflow.py`: 36 passed.
- `pytest tests`: 108 passed.
