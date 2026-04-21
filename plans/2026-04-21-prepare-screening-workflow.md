# Prepare Screening Workflow

- Title: `prepare-screening workflow`
- Slug: `2026-04-21-prepare-screening-workflow`
- Owner: `Codex`
- Created: `2026-04-21`
- Last updated: `2026-04-21 19:15`
- Overall status: `blocked`

## Objective

Добавить в `application-agent` отдельный workflow `prepare-screening`, который по уже ingest/analyze-подготовленной вакансии собирает воспроизводимый screening-пакет в `vacancies/<vacancy_id>/screening.md`, обновляет runtime memory и регистрируется в CLI/catalog без неявных side effects за пределами уже принятого vacancy-local контура.

## Background and context

После завершения `2026-04-21-workflow-contract-alignment-and-safety.md` первой целевой операцией для расширения workflow catalog выбран `prepare-screening`. Текущая кодовая база умеет:

- создавать vacancy scaffold через `ingest-vacancy`;
- выбирать role resume и формировать `analysis.md` / `adoptions.md` через `analyze-vacancy`;
- хранить task memory и историю запусков в `agent_memory/runtime/`;
- показывать только registry-backed workflow через `list-workflows`.

Подтверждённые факты по текущему состоянию:

- `prepare-screening` пока присутствует только в root-spec `C:\Users\avramko\OneDrive\Documents\Career\plans\resume-agent-spec.md`;
- workflow registry и CLI пока не знают о новой операции;
- реальные `analysis.md` в `vacancies/` могут содержать только scaffold, поэтому содержимое screening-документа должно быть полезным даже при частично заполненном анализе;
- существующий код `analyze_vacancy.py` уже содержит переиспользуемые helpers для выбора resume и чтения vacancy source, что снижает риск дублирования логики.

## Scope

### In scope

- новый workflow-модуль `prepare_screening.py` с детерминированной генерацией `screening.md`;
- обновление CLI, workflow registry и workflow catalog;
- обновление `meta.yml`, task memory и `workflow-runs.json` в рамках нового workflow;
- unit/smoke tests для happy path и guardrails;
- минимальная документация по новому workflow в кодовом репозитории и private workflow contract.

### Out of scope

- генерация PDF, LinkedIn и role/master resume артефактов;
- перенос vacancy-local `adoptions.md` в отдельный корневой pipeline;
- изменение Excel/response-monitoring contract;
- LLM-генерация или сетевые интеграции для подготовки screening.

## Assumptions

- `prepare-screening` запускается только после существующего vacancy-local контура, то есть на вакансии уже есть как минимум `meta.yml` и `analysis.md`;
- если `selected_resume` не передан явно, workflow может переиспользовать выбор из `meta.yml` или текущую эвристику `choose_resume`;
- screening-артефакт должен оставаться текстовым markdown-документом рядом с другими vacancy-local файлами;
- новым terminal status для `meta.yml` можно безопасно считать `screening_prepared`.

## Risks and unknowns

- реальные `analysis.md` часто неполные, поэтому screening-шаблон может оказаться слишком общим без аккуратных fallback-секций;
- если workflow начнёт слишком сильно зависеть от текущего формата `analysis.md`, дальнейшая эволюция анализа станет рискованной;
- workflow catalog уже содержит смешение roadmap и реализованных команд, поэтому нужно обновлять только реально доступный runtime contract;
- возможны скрытые ожидания к структуре `screening.md` со стороны будущих workflow, хотя отдельного downstream контракта пока нет.

## External touchpoints

- `C:\Users\avramko\OneDrive\Documents\Career\vacancies\` - чтение / обновление / проверка - источник vacancy-local артефактов и место записи `screening.md`.
- `C:\Users\avramko\OneDrive\Documents\Career\CV\` - чтение / проверка - источник role resume для self-intro, talking points и risk prompts.
- `C:\Users\avramko\OneDrive\Documents\Career\agent_memory\runtime\` - чтение / обновление / проверка - task memory и workflow run history.
- `C:\Users\avramko\OneDrive\Documents\Career\agent_memory\workflows\` - обновление / проверка - private contract для нового workflow.
- `C:\Users\avramko\OneDrive\Documents\Career\plans\resume-agent-spec.md` - чтение / проверка - upstream roadmap и минимальный продуктовый контракт.

## Milestones

### M1. Core Workflow And Artifact Contract

- Status: `done`
- Goal:
  - реализовать ядро `prepare-screening`, которое читает vacancy/resume артефакты и пишет `screening.md` вместе с runtime updates.
- Deliverables:
  - `src/application_agent/workflows/prepare_screening.py`
  - `tests/test_prepare_screening_workflow.py`
  - обновлённые supporting helpers / imports при необходимости
- Acceptance criteria:
  - `prepare-screening` создаёт `vacancies/<vacancy_id>/screening.md` с предсказуемыми секциями;
  - workflow обновляет `meta.yml` и runtime memory без git/Excel side effects;
  - при отсутствии нужных vacancy artifacts workflow возвращает точные ошибки, а не падает с traceback.
- Validation commands:
  - `python -m unittest tests.test_prepare_screening_workflow`
  - `python -m unittest tests.test_analyze_workflow tests.test_prepare_screening_workflow`
- Notes / discoveries:
  - Реализация допускает полезный fallback даже при placeholder-версии `analysis.md`: если секции анализа пустые, screening-пакет собирается из raw vacancy source, эвристики выбора resume и bullet-ов из role resume.
  - Новый workflow пока обновляет только vacancy-local `meta.yml` и `screening.md`; Excel и git-side effects не добавлялись, чтобы не нарушать safety boundary из предыдущего плана.

### M2. CLI, Catalog, And Operator Surface

- Status: `blocked`
- Goal:
  - встроить новый workflow в registry/catalog/CLI и синхронизировать operator-facing contract.
- Deliverables:
  - обновлённые `src/application_agent/cli.py`, `src/application_agent/workflows/registry.py`, `src/application_agent/config.py`
  - CLI tests
  - документация в `README.md` и `agent_memory/workflows/prepare-screening.md`
- Acceptance criteria:
  - `list-workflows` показывает `prepare-screening`;
  - `run_agent.py --root ../.. prepare-screening --vacancy-id <id>` работает через CLI entrypoint;
  - docs описывают реальный локальный side-effect boundary и required inputs.
- Validation commands:
  - `python run_agent.py --root ../.. list-workflows`
  - `python -m unittest tests.test_cli tests.test_prepare_screening_workflow`
- Notes / discoveries:
  - пока нет

### M3. Full Validation And Real-Scenario Smoke Check

- Status: `planned`
- Goal:
  - прогнать end-to-end validation на полном наборе тестов и одном реальном vacancy-local сценарии, затем зафиксировать итоговый контракт.
- Deliverables:
  - обновлённый план со status/decision/progress log
  - при необходимости корректировки шаблона `screening.md` после smoke-check
  - completion summary
- Acceptance criteria:
  - весь test suite проходит после добавления workflow;
  - реальный smoke run создаёт/обновляет `screening.md` без нарушения safety boundary;
  - план фиксирует дальнейший `Next step` без запроса к пользователю.
- Validation commands:
  - `python -m unittest discover -s tests`
  - `python run_agent.py --root ../.. prepare-screening --vacancy-id 20260421-fintehrobot-head-of-development-rukovoditel-razrabotki`
- Notes / discoveries:
  - пока нет

## Decision log

- `2026-04-21 18:24` - Новый implementation plan выделен отдельно от safety-плана. - `prepare-screening` уже определён как следующий workflow в backlog и не должен смешиваться с общими repository cleanup задачами. - Это позволяет закрывать реализацию milestone-by-milestone с собственными validation commands и commit boundary.
- `2026-04-21 19:10` - Для M1 выбран vacancy-local markdown artifact `screening.md` с deterministic fallback-логикой вместо зависимости от полностью заполненного `analysis.md`. - Реальные вакансии уже содержат placeholder-analysis, и блокировать workflow на этом этапе было бы слишком хрупко. - Это делает `prepare-screening` полезным сразу после ingest/analyze и уменьшает риск ложных падений на неполных исторических данных.
- `2026-04-21 19:15` - После завершения M1 выполнение плана поставлено на паузу по запросу пользователя. - Следующий технический шаг уже определён, но продолжать M2 без явного возобновления не нужно. - План переходит в состояние `blocked`, чтобы пауза была отражена в source of truth.

## Progress log

- `2026-04-21 18:24` - План создан на основе safety backlog, root-spec и текущей структуры workflow registry/CLI. - Валидация на этапе планирования: контекст собран из `resume-agent-spec.md`, `src/application_agent/workflows/registry.py`, `src/application_agent/cli.py`, `src/application_agent/config.py`, реальных vacancy/resume артефактов. - Status: `planned`.
- `2026-04-21 19:10` - M1 реализовал `PrepareScreeningWorkflow`, прямые runtime/meta updates и отдельный test module с happy path, placeholder-analysis fallback и stale vacancy guardrail. - `python -m unittest tests.test_prepare_screening_workflow` -> `3 tests, OK`; `python -m unittest tests.test_analyze_workflow tests.test_prepare_screening_workflow` -> `5 tests, OK`. - Status: `done`.
- `2026-04-21 19:15` - После успешного завершения M1 план переведён в паузу по запросу пользователя до отдельного сигнала на возобновление. - Дополнительная валидация не требовалась, так как код и план уже были в зелёном состоянии перед паузой. - Status: `blocked`.

## Current state

- Current milestone: `M2`
- Current status: `blocked`
- Next step: `Возобновить план с M2: интегрировать prepare-screening в CLI, workflow registry и catalog, затем обновить operator-facing docs.`
- Active blockers:
  - План поставлен на паузу по запросу пользователя.
- Open questions:
  - Нужно ли в будущем выделять более формальный downstream contract для структуры `screening.md`, если от него будут зависеть следующие workflow?

## Completion summary

Заполняется после завершения всех milestones.
