# Prepare Screening Workflow

- Название: `prepare-screening workflow`
- Slug: `2026-04-21-prepare-screening-workflow`
- Ответственный: `Codex`
- Создан: `2026-04-21`
- Обновлен: `2026-04-22 11:08`
- Общий статус: `done`

## Цель

Добавить в `application-agent` отдельный workflow `prepare-screening`, который по уже ingest/analyze-подготовленной вакансии собирает воспроизводимый screening-пакет в `vacancies/<vacancy_id>/screening.md`, обновляет runtime memory и регистрируется в CLI/catalog без неявных side effects за пределами vacancy-local контура.

## Контекст

M1 этого плана уже реализовал ядро `prepare-screening` как vacancy-local artifact workflow. Однако после пересмотра master plan продолжение работы по этому плану больше не считается следующим этапом.

Текущая кодовая база умеет:

- создавать vacancy scaffold через `ingest-vacancy`;
- выбирать role resume и формировать `analysis.md` / `adoptions.md` через `analyze-vacancy`;
- хранить task memory и историю запусков в `agent_memory/runtime/`;
- показывать registry-backed workflow через `list-workflows`.

Подтвержденные факты:

- M1 уже дал работающий `prepare_screening.py` и unit coverage;
- `prepare-screening` пока не встроен в CLI/catalog/operator-facing surface;
- master plan теперь требует сначала завершить repository cleanup и затем определить completion gate для `bootstrap` / `ingest-vacancy` / `analyze-vacancy`;
- поэтому M2/M3 этого плана не должны возобновляться до завершения M3/M4 master plan.

## Границы

### Входит в scope

- новый workflow-модуль `prepare_screening.py` с детерминированной генерацией `screening.md`;
- обновление CLI, workflow registry и workflow catalog;
- обновление `meta.yml`, task memory и `workflow-runs.json` в рамках нового workflow;
- unit/smoke tests для happy path и guardrails;
- минимальная документация по новому workflow в кодовом репозитории и private workflow contract.

### Не входит в scope

- генерация PDF, LinkedIn и role/master resume артефактов;
- перенос vacancy-local `adoptions.md` в отдельный корневой pipeline;
- изменение Excel/response-monitoring contract;
- продолжение реализации до завершения repository cleanup и current workflow completion gate.

## Допущения

- `prepare-screening` запускается только после существующего vacancy-local контура, то есть на вакансии уже есть как минимум `meta.yml` и `analysis.md`;
- если `selected_resume` не передан явно, workflow может переиспользовать выбор из `meta.yml` или текущую эвристику `choose_resume`;
- screening-артефакт остается текстовым markdown-документом рядом с другими vacancy-local файлами;
- новый terminal status для `meta.yml` можно безопасно считать `screening_prepared`.

## Риски и неизвестные

- реальные `analysis.md` часто неполные, поэтому screening-шаблон может оказаться слишком общим без аккуратных fallback-секций;
- если workflow слишком сильно зависит от текущего формата `analysis.md`, дальнейшая эволюция анализа станет рискованной;
- возобновление этого плана раньше времени снова смешает feature expansion с cleanup и текущими незавершенностями existing workflows.

## Внешние точки касания

- `C:\Users\avramko\OneDrive\Documents\Career\vacancies\` — чтение / обновление / проверка — источник vacancy-local артефактов и место записи `screening.md`;
- `C:\Users\avramko\OneDrive\Documents\Career\resumes\` — чтение / проверка — источник role resume для self-intro и talking points;
- `C:\Users\avramko\OneDrive\Documents\Career\agent_memory\runtime\` — чтение / обновление / проверка — task memory и workflow run history;
- `C:\Users\avramko\OneDrive\Documents\Career\agent_memory\workflows\` — обновление / проверка — private contract для нового workflow;
- `C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\plans\2026-04-21-repository-reconstruction-and-backlog.md` — чтение / проверка — текущая очередность реализации и dependency gate;
- `C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\plans\2026-04-21-workflow-contract-alignment-and-safety.md` — чтение / проверка — safety boundary и current workflow contract.

## Этапы

### M1. Core Workflow And Artifact Contract

- Статус: `done`
- Цель:
  - реализовать ядро `prepare-screening`, которое читает vacancy/resume артефакты и пишет `screening.md` вместе с runtime updates.
- Артефакты:
  - `src/application_agent/workflows/prepare_screening.py`
  - `tests/test_prepare_screening_workflow.py`
  - обновленные supporting helpers / imports при необходимости
- Критерии приемки:
  - `prepare-screening` создает `vacancies/<vacancy_id>/screening.md` с предсказуемыми секциями;
  - workflow обновляет `meta.yml` и runtime memory без git/Excel side effects;
  - при отсутствии нужных vacancy artifacts workflow возвращает точные ошибки, а не падает с traceback.
- Команды валидации:
  - `python -m unittest tests.test_prepare_screening_workflow`
  - `python -m unittest tests.test_analyze_workflow tests.test_prepare_screening_workflow`
- Заметки / находки:
  - реализация допускает полезный fallback даже при placeholder-версии `analysis.md`;
  - новый workflow пока обновляет только vacancy-local `meta.yml` и `screening.md`.

### M2. CLI, Catalog, And Operator Surface

- Статус: `done`
- Цель:
  - встроить новый workflow в registry/catalog/CLI и синхронизировать operator-facing contract.
- Артефакты:
  - обновленные `src/application_agent/cli.py`, `src/application_agent/workflows/registry.py`, `src/application_agent/config.py`
  - CLI tests
  - документация в `README.md` и `agent_memory/workflows/prepare-screening.md`
- Критерии приемки:
  - `list-workflows` показывает `prepare-screening`;
  - `run_agent.py --root ../.. prepare-screening --vacancy-id <id>` работает через CLI entrypoint;
  - docs описывают реальный локальный side-effect boundary и required inputs.
- Команды валидации:
  - `python run_agent.py --root ../.. list-workflows`
  - `python -m unittest tests.test_cli tests.test_prepare_screening_workflow`
- Заметки / находки:
  - выполнение milestone намеренно отложено до завершения M3/M4 master plan.

### M3. Full Validation And Real-Scenario Smoke Check

- Статус: `done`
- Цель:
  - прогнать end-to-end validation на полном наборе тестов и одном реальном vacancy-local сценарии, затем зафиксировать итоговый контракт.
- Артефакты:
  - обновленный план со status/decision/progress log
  - при необходимости корректировки шаблона `screening.md` после smoke-check
  - completion summary
- Критерии приемки:
  - весь test suite проходит после добавления workflow;
  - реальный smoke run создает/обновляет `screening.md` без нарушения safety boundary;
  - план фиксирует дальнейший `Next step` без запроса к пользователю.
- Команды валидации:
  - `python -m unittest discover -s tests`
  - `python run_agent.py --root ../.. prepare-screening --vacancy-id 20260421-fintehrobot-head-of-development-rukovoditel-razrabotki`
- Заметки / находки:
  - milestone нельзя начинать до возобновления плана после master-plan gate.

## Журнал решений

- `2026-04-21 18:24` — Новый implementation plan выделен отдельно от safety-плана. — Это позволяло закрывать реализацию milestone-by-milestone с собственными validation commands. — На тот момент `prepare-screening` еще считался первым кандидатом на feature expansion.
- `2026-04-21 19:10` — Для M1 выбран vacancy-local markdown artifact `screening.md` с deterministic fallback-логикой вместо жесткой зависимости от полностью заполненного `analysis.md`. — Это делает workflow полезным даже на historical/placeholder-analysis данных. — M1 удалось закрыть без Excel/git side effects.
- `2026-04-21 19:15` — После завершения M1 выполнение плана поставлено на паузу по запросу пользователя. — План переведен в `blocked`, чтобы пауза была отражена в source of truth. — M2 не продолжается без явного возобновления.
- `2026-04-21 19:51` — После обновления master plan `prepare-screening` больше не считается следующим execution step. — До его продолжения должны быть завершены repository cleanup и current workflow completion gate. — План остается `blocked` уже не только из-за паузы, но и из-за новой последовательности реализации.
- `2026-04-22 10:26` — Master M4 завершён, поэтому dependency gate для продолжения `prepare-screening` снят. — Это не делает план автоматически следующим шагом без переоценки очередности remaining workflows, но переводит его из `blocked` обратно в `planned`. — Дальше план должен рассматриваться уже внутри master M5.
- `2026-04-22 10:41` — После revalidation внутри master M5 этот plan подтверждён как следующий remaining-workflow execution step. — Основание: `prepare-screening` уже имеет реализованное ядро и unit coverage, а остальные planned workflows всё ещё зависят от незакрытых root/product contracts. — M2 можно возобновлять без изменения scope.
- `2026-04-22 10:58` — M2 закрыт: `prepare-screening` добавлен в runtime registry, CLI parser и `WORKFLOW_CATALOG`, а operator-facing surface синхронизирован через `README.md` и `agent_memory/workflows/prepare-screening.md`. — Это делает workflow видимым через `list-workflows` и доступным через `run_agent.py --root ../.. prepare-screening ...` без расширения side-effect boundary. — Следующий шаг смещён на полную validation и реальный smoke run.
- `2026-04-22 11:08` — M3 закрыт: full `unittest` baseline прошёл (`43 tests, OK`), а реальный smoke run на `20260421-fintehrobot-head-of-development-rukovoditel-razrabotki` создал новый `screening.md`, обновил `meta.yml` до `screening_prepared` и записал запуск в runtime memory. — Это подтверждает, что workflow работоспособен не только в isolated tests, но и на реальном vacancy-local контуре без Excel/git side effects. — План целиком можно переводить в `done` и возвращать в master M5.

## Журнал прогресса

- `2026-04-21 18:24` — План создан на основе safety findings, текущей структуры workflow registry/CLI и реальных vacancy/resume артефактов. — Статус: `planned`.
- `2026-04-21 19:10` — M1 реализовал `PrepareScreeningWorkflow`, прямые runtime/meta updates и отдельный test module с happy path, placeholder-analysis fallback и stale vacancy guardrail. — `python -m unittest tests.test_prepare_screening_workflow` -> `3 tests, OK`; `python -m unittest tests.test_analyze_workflow tests.test_prepare_screening_workflow` -> `5 tests, OK`. — Статус: `done`.
- `2026-04-21 19:15` — После успешного завершения M1 план переведен в паузу по запросу пользователя. — Дополнительная валидация не требовалась, так как код и план уже были в зеленом состоянии перед паузой. — Статус: `blocked`.
- `2026-04-21 19:51` — План синхронизирован с новой master-plan последовательностью. — Дополнительной кодовой валидации не проводилось, так как менялась только очередность реализации. — Статус: `blocked`.
- `2026-04-22 10:26` — План переведён из `blocked` в `planned` после закрытия master M4 и remediation по current stack. — Следующий шаг теперь не ждать completion gate, а переоценить, остается ли `prepare-screening` первым кандидатом в M5 ordered planning. — Статус: `planned`.
- `2026-04-22 10:41` — Переоценка в master M5 завершена: `prepare-screening` остаётся первым исполнимым workflow в очереди, поэтому M2 переведён в активную реализацию. — Дополнительной продуктовой развилки на этом шаге не обнаружено; работа продолжается через CLI/catalog/operator integration. — Статус: `in_progress`.
- `2026-04-22 10:58` — M2 завершён: targeted validation (`python -m unittest tests.test_cli tests.test_memory_store tests.test_prepare_screening_workflow`) прошла, а `python run_agent.py --root ../.. list-workflows` теперь показывает `prepare-screening` рядом с остальными runtime workflows. — План переводится на M3 full validation и real-scenario smoke check. — Статус: `in_progress`.
- `2026-04-22 11:08` — M3 завершён: `python -m unittest discover -s tests` остаётся зелёным, а реальный `prepare-screening` smoke run отработал на существующей вакансии и создал `vacancies/20260421-fintehrobot-head-of-development-rukovoditel-razrabotki/screening.md`. — План завершён полностью; следующий execution step должен вернуться в master M5 и открыть следующий remaining-workflow plan. — Статус: `done`.

## Текущее состояние

- Текущий milestone: `M3`
- Текущий статус: `done`
- Следующий шаг: `Вернуться в master plan M5 и открыть dedicated plan для следующего workflow-кандидата `rebuild-master`, начиная с contract/source-of-truth clarification по permanent signals и accepted adoptions.`
- Активные блокеры:
  - нет
- Открытые вопросы:
  - Нужен ли более формальный downstream contract для структуры `screening.md`, если от него будут зависеть следующие workflow?

## Итог завершения

- Поставлено:
  - ядро `prepare-screening` с vacancy-local `screening.md` и runtime updates;
  - runtime wiring в CLI, registry и `WORKFLOW_CATALOG`;
  - operator-facing documentation в `README.md` и `agent_memory/workflows/prepare-screening.md`.
- Провалидировано:
  - `python -m unittest tests.test_prepare_screening_workflow`
  - `python -m unittest tests.test_cli tests.test_memory_store tests.test_prepare_screening_workflow`
  - `python -m unittest discover -s tests`
  - `python run_agent.py --root ../.. list-workflows`
  - `python run_agent.py --root ../.. prepare-screening --vacancy-id 20260421-fintehrobot-head-of-development-rukovoditel-razrabotki`
- Оставшиеся follow-up задачи:
  - при необходимости формализовать downstream contract для структуры `screening.md`, если на него начнут опираться следующие workflow;
  - решить, нужен ли отдельный review/normalization слой для ручной доработки screening-пакета.
- Остаточные риски:
  - реальный `screening.md` по-прежнему строится от текущего формата `analysis.md`, поэтому крупная перестройка анализа потребует синхронного обновления этого workflow.
- Были ли затронуты артефакты корневого репозитория:
  - да: создан `vacancies/20260421-fintehrobot-head-of-development-rukovoditel-razrabotki/screening.md`, обновлены `meta.yml`, runtime memory и private workflow contract в `agent_memory/workflows/prepare-screening.md`.
