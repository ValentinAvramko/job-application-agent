# Workflow Contract Alignment And Safety

- Title: `Workflow contract alignment and safety`
- Slug: `2026-04-21-workflow-contract-alignment-and-safety`
- Owner: `Codex`
- Created: `2026-04-21`
- Last updated: `2026-04-21 17:08`
- Overall status: `in_progress`

## Objective

Собрать единый, проверяемый контракт для уже реализованных workflow (`bootstrap`, `ingest-vacancy`, `analyze-vacancy`) и связанных side effects так, чтобы код, документация, runtime memory, Excel-обновления и git-публикация не противоречили друг другу и не создавали скрытых рисков для private workspace.

## Background and context

Текущая реализация в `tooling/application-agent/src` уже включает:

- CLI entrypoint и workflow registry;
- `JsonMemoryStore` для runtime-файлов;
- `ingest-vacancy` с генерацией vacancy scaffold, обновлением памяти и записью в `response-monitoring.xlsx`;
- `analyze-vacancy` с выбором ролевого резюме, fit-эвристикой и генерацией vacancy-local analysis/adoptions;
- extraction/parsing stack для HH и generic career pages;
- Playwright fallback через `npx playwright`.

Подтвержденное тестами состояние:

- `python -m unittest discover -s tests` проходит;
- тесты покрывают ingest/analyze workflow, memory store, source channel normalization, country catalog, Playwright renderer и CLI autopush behavior.

Подтвержденные проблемы контракта:

- CLI `ingest-vacancy` после успешного workflow всегда вызывает `autopush_ingest_artifacts`, то есть делает `git add`, `git commit`, `git push`;
- design-материалы в корне ожидают подтверждение пользователя перед публикацией и описывают ручной git flow через `tooling/git/*.ps1`;
- `agent_memory/workflows/ingest-vacancy.md` отстает от кода и до сих пор трактует Excel-интеграцию как future work;
- runtime-файлы содержат ссылки на вакансии, которых больше нет в `vacancies/`, значит отсутствует явный контракт на cleanup/reconciliation;
- current workflow catalog ограничен тремя командами, хотя root-spec описывает больший целевой набор операций.

## Scope

### In scope

- contract matrix для `bootstrap`, `ingest-vacancy`, `analyze-vacancy`;
- правила мутаций root-артефактов: `vacancies/`, `agent_memory/runtime/`, `response-monitoring.xlsx`;
- правила git-side effects и границы автоматической публикации;
- политика работы с stale runtime state и отсутствующими vacancy-артефактами;
- backlog по расширению workflow catalog после стабилизации текущего контура.

### Out of scope

- реализация новых feature workflow в этом плане;
- наполнение root knowledge/profile/adoptions реальными данными;
- редизайн PDF/LinkedIn output pipeline;
- изменение исторических архивов в корне без отдельной необходимости.

## Assumptions

- `unittest`, а не `pytest`, является текущим воспроизводимым validation path в этом репозитории;
- текущие `src/` и `tests/` точнее отражают фактическое поведение, чем часть устаревших root-документов;
- если auto-commit/auto-push будет сохранен, это должно быть явно признано проектным решением и отражено во всех runbook/контрактах;
- дальнейшее расширение workflow catalog безопасно только после стабилизации контрактов текущих трех команд.

## Risks and unknowns

- скрытая публикация private-артефактов может нарушать ожидания пользователя и manual release flow;
- изменение contract boundary может сломать уже используемый daily flow, если не будет подтверждено тестами и runbook;
- неясно, нужно ли удалять, архивировать или игнорировать stale runtime entries при отсутствии vacancy folders;
- неясно, является ли `response-monitoring.xlsx` обязательным hard dependency для ingest или должен поддерживаться degradable mode;
- Playwright fallback зависит от наличия `npx` и внешней сетевой среды, что повышает риск нестабильных реальных прогонов.

## External touchpoints

- `C:\Users\avramko\OneDrive\Documents\Career\vacancies\` — чтение / обновление / проверка — scaffold и анализ вакансий являются прямыми результатами workflow.
- `C:\Users\avramko\OneDrive\Documents\Career\agent_memory\runtime\` — чтение / обновление / проверка — task/project/user memory и журнал запусков.
- `C:\Users\avramko\OneDrive\Documents\Career\agent_memory\workflows\` — чтение / обновление / проверка — workflow contracts в private-layer documentation.
- `C:\Users\avramko\OneDrive\Documents\Career\response-monitoring.xlsx` — чтение / обновление / проверка — ingest side effect и внешний контракт Excel.
- `C:\Users\avramko\OneDrive\Documents\Career\CV\` — чтение / проверка — `analyze-vacancy` выбирает и читает ролевые резюме отсюда.
- `C:\Users\avramko\OneDrive\Documents\Career\tooling\git\` — чтение / обновление / проверка — intended git flow и публикационные скрипты.
- `C:\Users\avramko\OneDrive\Documents\Career\tooling\run-ingest-analyze.md` и `tooling\git-workflow.md` — чтение / обновление / проверка — runbook и CLI expectations.

## Milestones

### M1. Current Contract Matrix And Contradiction Ledger

- Status: `done`
- Goal:
  - описать current state для CLI-команд, workflow artifacts, memory updates, Excel writes и git-side effects;
  - зафиксировать все подтвержденные противоречия между кодом, тестами и документацией.
- Deliverables:
  - matrix `command -> inputs -> outputs -> side effects -> validation -> contradictions`;
  - приоритизированный contradiction ledger;
  - список решений, требующих product/owner confirmation.
- Acceptance criteria:
  - для `bootstrap`, `ingest-vacancy`, `analyze-vacancy` перечислены все подтвержденные side effects;
  - явно отмечены конфликты по auto-publish, Excel-контракту, stale runtime и outdated docs;
  - можно продолжать работу без повторного чтения всего репозитория.
- Validation commands:
  - `python run_agent.py --root ../.. list-workflows`
  - `python run_agent.py --root ../.. show-memory`
  - `python -m unittest discover -s tests`
- Notes / discoveries:
  - Current contract matrix:

    | Command | Confirmed inputs | Confirmed outputs | Confirmed side effects | Evidence | Current contradiction |
    | --- | --- | --- | --- | --- | --- |
    | `bootstrap` | `--root` | JSON с `created_directories` | Создает каталоги workspace и bootstrap-файлы runtime memory (`task-memory.json`, `project-memory.json`, `user-memory.json`, `workflow-runs.json`); backfill'ит `workflow_catalog`; не пишет run history; не трогает git | `src/application_agent/cli.py`, `src/application_agent/workspace.py`, `src/application_agent/memory/store.py`, `tests/test_memory_store.py`, `README.md` | `bootstrap` существует как CLI-команда и как элемент `project_memory.workflow_catalog`, но не возвращается командой `list-workflows`, потому что не зарегистрирован в workflow registry |
    | `ingest-vacancy` | `company`/`position` или данные, извлекаемые из `source_url`; `source_text`/`input_file`; channel/language/country/work-mode flags | JSON `WorkflowResult` + summary CLI | Создает `vacancies/<id>/{meta.yml,source.md,analysis.md,adoptions.md}`; добавляет строку в `response-monitoring.xlsx`; обновляет `task-memory.json`; пишет запись в `workflow-runs.json`; после возврата workflow CLI делает `git add`, `git commit`, `git push origin <current-branch>` | `src/application_agent/workflows/ingest_vacancy.py`, `src/application_agent/integrations/response_monitoring.py`, `src/application_agent/cli.py`, `tests/test_ingest_workflow.py`, `tests/test_cli.py`, `README.md` | `tooling/run-ingest-analyze.md` описывает ingest как локальный mutating run без Excel/git side effects; `agent_memory/workflows/ingest-vacancy.md` считает Excel future work; `tooling/git-workflow.md` закрепляет ручную публикацию через PowerShell scripts |
    | `analyze-vacancy` | `--vacancy-id` или inline ingest-поля (`company`, `position`, `source_*`) + optional `selected_resume` | JSON `WorkflowResult` | При наличии `vacancy_id` читает `meta.yml` и `source.md`, выбирает resume из `CV/`, обновляет `meta.yml`, `analysis.md`, `adoptions.md`, `task-memory.json`, `workflow-runs.json`; если `vacancy_id` отсутствует, сначала запускает in-process ingest и наследует его артефакты | `src/application_agent/workflows/analyze_vacancy.py`, `tests/test_analyze_workflow.py`, `README.md`, `tooling/run-ingest-analyze.md` | Root-spec ожидает дальнейшую эволюцию adoptions/output pipeline, но текущий контракт закреплен на vacancy-local `adoptions.md` и не описывает migration boundary |

  - Prioritized contradiction ledger:
    - `P0` CLI `ingest-vacancy` автопубликует изменения в git, хотя root runbook и `tooling/git-workflow.md` описывают публикацию как отдельный, подтверждаемый вручную шаг.
    - `P1` `agent_memory/workflows/ingest-vacancy.md` устарел: документ обещает только файловый scaffold и runtime memory, но код уже пишет в Excel и `workflow-runs.json`.
    - `P1` `tooling/run-ingest-analyze.md` недоописывает ingest side effects: из runbook нельзя понять, что `response-monitoring.xlsx` меняется и что CLI сейчас пытается коммитить/пушить.
    - `P1` Runtime memory не имеет reconciliation contract: `agent_memory/runtime/task-memory.json` ссылается на `20260421-dinamichno-razvivayuschayasya-sudohodnaya-kompaniya-direktor-po-tsifrovomu-razvitiyu-i-tehnologiyam-cto-02`, но `Test-Path` для соответствующей папки вакансии возвращает `False`.
    - `P2` `bootstrap` числится в `WORKFLOW_CATALOG`, но `list-workflows` показывает только `ingest-vacancy` и `analyze-vacancy`; сейчас смешаны CLI commands и registry-backed workflows.
    - `P2` `project-memory.json` и `WORKFLOW_CATALOG` перечисляют только `bootstrap`, `ingest-vacancy`, `analyze-vacancy`, тогда как root target-spec описывает более длинную очередь операций; граница между implemented contract и roadmap пока не закреплена.

  - Decisions requiring owner confirmation before contract is finalized:
    - Должен ли CLI `ingest-vacancy` вообще выполнять `git commit`/`git push`, или публикация должна быть вынесена в явный ручной/отдельный workflow?
    - Является ли `response-monitoring.xlsx` обязательным hard dependency для ingest, или нужен degradable mode без падения workflow?
    - При stale runtime entry нужно автоматически очищать ссылку, помечать ее как missing/archived или только предупреждать пользователя?
    - Нужно ли считать vacancy-local `adoptions.md` временным контрактом до отдельной миграции в корневой `adoptions/` pipeline?

### M2. Mutation And Publication Safety Policy

- Status: `in_progress`
- Goal:
  - принять и оформить явную политику того, что workflow может менять автоматически, а что требует отдельного подтверждения или ручного шага.
- Deliverables:
  - решение по auto-commit/auto-push в `ingest-vacancy`;
  - обновленные CLI/docs/tests под выбранную политику;
  - runbook с явным разделением local mutation и publication.
- Acceptance criteria:
  - поведение CLI и документация больше не противоречат друг другу;
  - пользовательские ожидания по подтверждению публикации отражены явно;
  - тесты подтверждают выбранный contract boundary.
- Validation commands:
  - `python -m unittest tests.test_cli tests.test_ingest_workflow tests.test_analyze_workflow`
  - `Get-Content -Raw ..\git-workflow.md`
  - `Get-Content -Raw ..\run-ingest-analyze.md`
- Notes / discoveries:
  - ручные PowerShell-скрипты публикации уже существуют, поэтому текущее автоповедение CLI выглядит архитектурно спорным.

### M3. Runtime Reconciliation And Missing-Artifact Behavior

- Status: `planned`
- Goal:
  - определить, как агент должен вести себя, когда память ссылается на удаленные или архивированные vacancy artifacts, и закрепить это в коде/контрактах.
- Deliverables:
  - политика работы со stale entries в `task-memory.json` и `workflow-runs.json`;
  - обновленные workflow contracts и validation scenarios;
  - при необходимости utility/guardrails для reconciliation.
- Acceptance criteria:
  - поведение при отсутствии vacancy folder формализовано;
  - CLI и workflow не подразумевают молча существование артефакта, которого уже нет;
  - есть воспроизводимый способ проверить корректность runtime state.
- Validation commands:
  - `Test-Path "C:\Users\avramko\OneDrive\Documents\Career\vacancies\20260421-dinamichno-razvivayuschayasya-sudohodnaya-kompaniya-direktor-po-tsifrovomu-razvitiyu-i-tehnologiyam-cto-02"`
  - `python run_agent.py --root ../.. show-memory`
  - `python -m unittest discover -s tests`
- Notes / discoveries:
  - это отдельный contract problem, а не просто грязные данные: runtime может переживать удаление старых вакансий.

### M4. Workflow Catalog Expansion Queue

- Status: `planned`
- Goal:
  - после стабилизации текущих контрактов разбить target operations из root-spec на реалистичную очередь внедрения.
- Deliverables:
  - ordered backlog для `prepare-screening`, `rebuild-master`, `rebuild-role-resume`, `build-linkedin`, `export-resume-pdf` и сопутствующих memory/adoptions integrations;
  - dependency map между новыми workflow и уже существующим кодом.
- Acceptance criteria:
  - каждая будущая операция имеет хотя бы минимальный input/output contract, external touchpoints и validation baseline;
  - очередь расширения не смешивает feature work с unresolved safety fixes.
- Validation commands:
  - `Get-Content -Raw C:\Users\avramko\OneDrive\Documents\Career\plans\resume-agent-spec.md`
  - `rg -n "prepare-screening|rebuild-master|rebuild-role-resume|build-linkedin|export-resume-pdf" C:\Users\avramko\OneDrive\Documents\Career\plans\resume-agent-spec.md`
  - `Get-Content -Raw C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\plans\2026-04-21-workflow-contract-alignment-and-safety.md`
- Notes / discoveries:
  - target operations уже описаны на уровне intent, но еще не приведены к implementation-ready контрактам.

## Decision log

- `2026-04-21 16:43` — Текущий workflow stack рассматривается как отдельный workstream, а не как часть общего artifact cleanup. — Основные риски связаны с side effects и контрактами поведения кода. — Это позволяет сначала стабилизировать безопасную основу, а уже потом расширять функциональность.
- `2026-04-21 16:43` — `unittest` принят как текущий validation baseline. — Он реально запускается в данном окружении, в отличие от `pytest`. — Все milestones плана должны использовать команды, воспроизводимые без дополнительной установки.
- `2026-04-21 16:43` — Исторический `ingest-refactor-plan.md` оставлен как reference о завершенном рефакторинге, но не как основной план текущего workstream. — Он не покрывает вопросы runtime safety, publication flow и contract drift. — Новый план берет более широкий operational scope.
- `2026-04-21 17:08` — Для M1 source of truth собран из кода и тестов, а root runbook/docs трактуются как expected-operator contract. — Иначе невозможно честно разделить фактическое поведение и drift в документации. — M2 должен выровнять именно operator-facing boundary, а не только внутренние описания.

## Progress log

- `2026-04-21 16:43` — По коду, тестам и runbook подтверждено текущее поведение `bootstrap`, `ingest-vacancy`, `analyze-vacancy`, включая Excel integration и git-side effects в CLI. — `python -m unittest discover -s tests` -> `36 tests, OK`. — Status: `planned`.
- `2026-04-21 16:43` — Зафиксированы ключевые contradictions: outdated workflow docs, auto-publish conflict, stale runtime state, расхождение в Excel-схеме и неполный workflow catalog относительно target-spec. — Требуется явное contract alignment до расширения функциональности. — Status: `planned`.
- `2026-04-21 17:08` — M1 дополнен contract matrix, contradiction ledger и списком owner-level решений по publication, Excel dependency и stale runtime handling. — Validation выявила дополнительный drift: `bootstrap` числится в catalog, но не в workflow registry/listing; `python run_agent.py --root ../.. list-workflows`, `python run_agent.py --root ../.. show-memory` и `python -m unittest discover -s tests` завершились успешно. — Status: `done`.

## Current state

- Current milestone: `M2`
- Current status: `in_progress`
- Next step: `Развести local mutation и git publication boundary в CLI/docs/tests, начиная с решения по auto-publish у ingest-vacancy.`
- Active blockers:
  - Нет решения по допустимости auto-commit/auto-push из CLI.
  - Нет согласованного ответа, как трактовать stale runtime entries.
  - Не согласован канонический Excel mapping contract.
- Open questions:
  - Должен ли `ingest-vacancy` уметь работать без `response-monitoring.xlsx`, если файла нет или он поврежден?
  - Нужно ли отделить локальный mutating run от публикации в Git на уровне отдельных CLI-команд?
  - Должен ли `analyze-vacancy` по-прежнему писать vacancy-local `adoptions.md`, если проект перейдет к корневому `adoptions/inbox/<vacancy_id>.md`?
  - Какой набор workflow нужно считать "минимально готовым" до начала feature expansion?

## Completion summary

Заполняется после завершения workstream-а по alignment и safety.
