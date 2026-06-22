# Исправление ложной auth-классификации HH

- Название: `Исправление ложной auth-классификации HH`
- Slug: `2026-06-22-hh-auth-form-classification`
- Ответственный: `Codex`
- Создан: `2026-06-22`
- Обновлен: `2026-06-22`
- Общий статус: `completed`

## Цель

Активные HH-вакансии со встроенной auth-формой внутри страницы больше не получают `auth_required` и не деактивируются, если HTML содержит полноценные признаки страницы вакансии.

## Контекст

Активные страницы HH могут содержать встроенную форму авторизации (`data-qa="auth-form"`) рядом с полноценным контентом вакансии. Текущая общая HTML-классификация видит такую форму и возвращает `auth_required`, что приводит к массовой деактивации активных HH-вакансий.

Проблема не в HTTP `401/403`: эти коды для HH API остаются только поводом перейти на HTML fallback. Ошибка возникает уже на HTML-странице, где одновременно есть активный vacancy content и embedded auth UI.

## Границы

### Входит в scope

- HH-aware HTML-классификация в `vacancy_sources.py`.
- Regression tests для активной HH-страницы с embedded auth form и для HH login-only страницы.
- Dry-run smoke для `check-response-monitoring` без изменения workbook.

### Не входит в scope

- Изменение публичных CLI/API.
- Изменение контракта `VacancySourceCheckResult.should_deactivate`.
- Восстановление или редактирование `response-monitoring.xlsx`.
- Работа с untracked `response-monitoring — копия.xlsx`.

## Допущения

- Массовая ложная деактивация связана с активными HH-страницами, где есть embedded auth form.
- Реальные login-only/auth-only HH страницы без vacancy content можно по-прежнему классифицировать как `auth_required`.
- `401/403` от HH API остаются fallback-сценарием и сами по себе не являются причиной деактивации в этой правке.

## Риски и неизвестные

- HH может изменить разметку `data-qa="vacancy-description"`; тогда потребуется расширить набор active vacancy signals.
- Dry-run зависит от доступности внешних сайтов и может дать transient результаты, не связанные с кодом.

## Внешние точки касания

- `../../response-monitoring.xlsx` - только чтение через dry-run - проверить реальный monitoring workflow без записи workbook.
- `../../agent_memory/runtime/check-response-monitoring/` - генерация dry-run лога - сохранить smoke-результат.
- `../../response-monitoring — копия.xlsx` - не трогать - untracked пользовательский файл вне scope.

## Этапы

### M1. HH-aware классификация

- Статус: `completed`
- Цель:
  - Не считать активную HH-страницу login-screen только из-за embedded auth form.
- Артефакты:
  - `src/application_agent/workflows/vacancy_sources.py`
  - `tests/test_ingest_workflow.py`
- Критерии приемки:
  - HH HTML с `data-qa="vacancy-description"`, `title/h1` и `data-qa="auth-form"` возвращает `active`.
  - HH login-only HTML без vacancy description возвращает `auth_required`.
  - Archived API, archived heading, HTTP `404/410` и transient errors сохраняют прежнее поведение.
- Команды валидации:
  - `pytest tests\test_ingest_workflow.py`
  - `pytest tests`
  - `python job-application-agent.py --root ..\.. check-response-monitoring --dry-run --log-file agent_memory/runtime/check-response-monitoring/<timestamp>-auth-form-fix-dry-run.log`
- Заметки:
  - Workbook не должен изменяться.

## Журнал решений

- `2026-06-22` - Решено не менять `should_deactivate` и не переопределять `401/403`; исправление ограничено HH HTML-классификацией.
- `2026-06-22` - Active HH signal задан как vacancy description marker плюс непустой `h1` или vacancy-like `title`.

## Журнал прогресса

- `2026-06-22` - План создан. Статус: `in_progress`.
- `2026-06-22` - Добавлены HH-aware helper и regression tests.
- `2026-06-22` - `pytest tests\test_ingest_workflow.py` прошёл: 39 passed.
- `2026-06-22` - `pytest tests` прошёл: 111 passed.
- `2026-06-22` - Dry-run с сетевым доступом прошёл; HH active rows больше не получают `reason=login/password screen detected`.
- `2026-06-22` - `ruff check src/application_agent/workflows/vacancy_sources.py tests/test_ingest_workflow.py` прошёл.

## Текущее состояние

- Текущий milestone: `M1`
- Текущий статус: `completed`
- Следующий шаг: `Закоммитить и отправить изменения.`
- Активные блокеры:
  - нет
- Открытые вопросы:
  - нет

## Итог завершения

Реализована HH-aware HTML-классификация: активная HH-страница с `data-qa="vacancy-description"` и `h1` или vacancy-like `title` не считается login-screen из-за embedded auth form. Login-only HH HTML без vacancy content сохраняет `auth_required`.

Проверки:

- `pytest tests\test_ingest_workflow.py` - 39 passed.
- `pytest tests` - 111 passed.
- `ruff check src/application_agent/workflows/vacancy_sources.py tests/test_ingest_workflow.py` - passed.
- `python job-application-agent.py --root ..\.. check-response-monitoring --dry-run --log-file agent_memory/runtime/check-response-monitoring/2026-06-22-auth-form-fix-dry-run-network.log` - workbook не обновлялся; HH active rows классифицированы как `active`.
