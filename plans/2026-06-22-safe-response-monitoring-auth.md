# Безопасная обработка auth/anti-bot при проверке response-monitoring

- Название: `check-response-monitoring`: безопасная обработка auth/anti-bot
- Slug: `2026-06-22-safe-response-monitoring-auth`
- Ответственный: `Codex`
- Создан: `2026-06-22`
- Обновлен: `2026-06-22 14:39`
- Общий статус: `done`

## Цель

`check-response-monitoring` больше не деактивирует активные вакансии только потому, что автоматическая проверка получила login/password screen, HTTP `401/403` или другой auth/anti-bot ответ, хотя обычный браузер пользователя открывает вакансию. Такие случаи должны оставаться активными и попадать в warning/manual-check.

## Контекст

Код команды находится в `./tooling/application-agent`. Реальный запуск `2026-06-22` деактивировал 57 из 58 активных строк `response-monitoring.xlsx`, почти все с причиной `login/password screen detected`, хотя ручная проверка пользователем показала, что несколько ссылок открываются и активны.

Текущее поведение задается в `src/application_agent/workflows/vacancy_sources.py`: `VacancySourceCheckResult.should_deactivate` включает `auth_required`, а `classify_http_error` возвращает `auth_required` для `401/403`. Workflow `src/application_agent/workflows/check_response_monitoring.py` пишет `D=Нет`, когда `should_deactivate` истинно.

Внешний артефакт `response-monitoring.xlsx` уже изменен предыдущим запуском. В рамках этого плана workbook не исправляется автоматически, чтобы не смешивать изменение логики и восстановление данных.

## Границы

### Входит в scope

- Изменить правило деактивации: только уверенные `inactive` и `not_found` переводят строку в `Нет`.
- Оставить `auth_required` диагностическим статусом, но логировать его как `WARNING` без изменения workbook.
- Добавить/обновить тесты для login/password screen, HTTP `403`, workflow warnings и JS-rendered `job not found`.
- Зафиксировать результаты в этом плане.

### Не входит в scope

- Автоматическое восстановление уже измененного `response-monitoring.xlsx`.
- Live-прогон по всем внешним вакансиям без `--dry-run`.
- Полная переработка browser fingerprint/cookies для HH, LinkedIn и карьерных сайтов.

## Допущения

- HTTP `404/410` и явные inactive/not-found markers остаются достаточным основанием для деактивации.
- Login/auth/anti-bot страница означает "автоматическая проверка не смогла подтвердить статус", а не "вакансия закрыта".
- Для JS-heavy страниц допустимо использовать существующий Playwright fallback и распознавать явные rendered not-found markers.

## Риски и неизвестные

- Часть действительно закрытых вакансий за login/auth wall останется активной до ручной проверки.
- Расширение generic not-found markers должно быть узким, чтобы не повторить ложные деактивации по скрытым шаблонам.
- Live-доступ к внешним сайтам нестабилен и не должен быть обязательным для unit validation.

## Внешние точки касания

- `response-monitoring.xlsx` в корне workspace - проверка / не обновление - текущий реальный workbook уже изменен прошлым запуском; этот milestone не должен вносить новые изменения.
- `agent_memory/runtime/check-response-monitoring/` в корне workspace - чтение - использовался для диагностики причины массовой деактивации.

## Этапы

### M1. Консервативная деактивация

- Статус: `done`
- Цель:
  - Исключить `auth_required` из автоматической деактивации и сделать его warning.
- Артефакты:
  - `src/application_agent/workflows/vacancy_sources.py`
  - `src/application_agent/workflows/check_response_monitoring.py`
  - `tests/test_ingest_workflow.py`
  - `plans/2026-06-22-safe-response-monitoring-auth.md`
- Критерии приемки:
  - Login/password HTML и HTTP `403` не дают `should_deactivate=True`.
  - Workflow не обновляет workbook для `auth_required`, но пишет `WARNING`.
  - HTTP `404/410` продолжает деактивировать.
  - Rendered `job not found` продолжает деактивировать JS-heavy страницы.
- Команды валидации:
  - `pytest tests\test_ingest_workflow.py`
  - `pytest tests`
- Заметки:
  - `auth_required` исключен из `should_deactivate`.
  - Workflow логирует `auth_required` как `WARNING` и не обновляет workbook.
  - Добавлены rendered not-found markers для JS-heavy страниц вроде Ashby.
  - Реальный workbook не менялся этим изменением.
  - `pytest tests\test_ingest_workflow.py`: 40 passed.
  - `pytest tests`: 112 passed.

## Журнал решений

- `2026-06-22 14:36` - `auth_required` переводится из hard-deactivation в warning/manual-check, потому что пользователь подтвердил, что ссылки, помеченные checker-ом как login/password, вручную открываются и активны.
- `2026-06-22 14:39` - Уверенная автоматическая деактивация оставлена только для `inactive` и `not_found`; `auth_required` теперь требует ручной проверки.

## Журнал прогресса

- `2026-06-22 14:36` - План создан. Статус: `in_progress`.
- `2026-06-22 14:39` - M1 реализован и проверен targeted/full tests. Статус: `done`.

## Текущее состояние

- Текущий milestone: `none`
- Текущий статус: `done`
- Следующий шаг: `подготовить handoff пользователю`
- Активные блокеры:
  - нет
- Открытые вопросы:
  - нет

## Итог завершения

Поставлено:

- `auth_required` больше не деактивирует строки `response-monitoring.xlsx`.
- `check-response-monitoring` пишет `WARNING` для auth/login/anti-bot случаев вместо изменения `D=Активна`.
- HTTP `404/410` и явные inactive/not-found markers продолжают деактивировать.
- Для JS-heavy страниц добавлены узкие rendered markers `job not found` / `posting not found`.

Проверено:

- `pytest tests\test_ingest_workflow.py`: 40 passed.
- `pytest tests`: 112 passed.

Остаточный риск:

- Уже измененный предыдущим запуском root `response-monitoring.xlsx` нужно восстанавливать отдельным осознанным действием.
