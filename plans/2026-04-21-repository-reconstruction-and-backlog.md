# Repository Reconstruction And Backlog

- Title: `Repository reconstruction and backlog`
- Slug: `2026-04-21-repository-reconstruction-and-backlog`
- Owner: `Codex`
- Created: `2026-04-21`
- Last updated: `2026-04-21 20:35`
- Overall status: `in_progress`

## Objective

Зафиксировать актуальную, исполнимую последовательность восстановления репозитория и дальнейшей работы так, чтобы:

- текущий source of truth жил в актуальных plan files внутри `tooling/application-agent/plans/`;
- старые plan/spec artifacts были содержательно перенесены в новую структуру, а затем удалены;
- feature expansion не начиналась раньше, чем будет наведён порядок в репозитории и будет явно определено, что ещё не доведено в текущем workflow-стеке.

## Background and context

Корень `Career/` остаётся private data/orchestration слоем. Код инструмента живёт в `tooling/application-agent/` и уже реализует:

- `bootstrap`;
- `ingest-vacancy`;
- `analyze-vacancy`;
- runtime memory;
- Excel integration для `response-monitoring.xlsx`;
- parsing stack и Playwright fallback.

Подтверждённые факты:

- `python -m unittest discover -s tests` проходит;
- `pytest` в текущем окружении отсутствует;
- runtime memory содержит stale ссылки на отсутствующие vacancy folders;
- root-слой содержит незавершённые long-lived stores (`knowledge/`, `profile/`, `adoptions/`) и manual/historical artifacts (`Employers/`, `archive/`, `promts/`);
- superseded plan/spec artifacts (`plans/resume-agent-spec.md`, `plans/repository-topology.md`, `tooling/application-agent/plans/ingest-refactor-plan.md`) мигрированы в active plans и удалены.

Содержательно из старых артефактов уже мигрированы или подлежат миграции в новую структуру следующие намерения:

- public/private split: код и инженерные решения живут в `tooling/application-agent`, root хранит данные, шаблоны, результаты и orchestration artifacts;
- target workflow catalog: `prepare-screening`, `rebuild-master`, `rebuild-role-resume`, `build-linkedin`, `export-resume-pdf`;
- source-of-truth rules: `CV/MASTER.md` остаётся главным фактическим источником о кандидате, ролевые CV — производные, contact/profile overlays должны жить отдельно от resume text;
- output contracts и long-lived stores должны быть явно определены, а не оставаться скрытыми в historical docs и manual artifacts.

Главный источник путаницы на текущий момент:

- safety workstream уже завершён, но это не означает, что `bootstrap` / `ingest-vacancy` / `analyze-vacancy` считаются полностью доведёнными;
- root cleanup и migration старых плановых артефактов ещё не доведены до конца;
- planning remaining workflows нельзя считать следующим шагом до completion gate по текущему стеку.

## Scope

### In scope

- синхронизация master plan с фактическим состоянием workstreams;
- явная последовательность: repository cleanup -> current workflow completion gate -> planning remaining workflows;
- migration старых plan/spec artifacts в новые active plan files;
- удаление superseded plan artifacts после переноса содержимого;
- фиксация dependency gates между cleanup, current workflow completion и future feature planning.

### Out of scope

- реализация новых workflows в рамках этого master plan;
- изменение фактического содержимого `CV/`, `knowledge/`, `profile/`, `adoptions/`;
- генерация новых resume/PDF/LinkedIn outputs;
- неограниченная перепись runtime и root данных без отдельного workstream-плана.

## Assumptions

- `src/` и `tests/` в `tooling/application-agent` описывают текущее поведение точнее, чем superseded planning docs;
- старые plan/spec artifacts можно удалять после того, как их содержательные решения явно распределены по актуальным plan files;
- feature expansion допустима только после завершения cleanup и фиксации completion gate для текущего workflow-стека;
- `unittest` остаётся текущим воспроизводимым validation baseline.

## Risks and unknowns

- часть важных root contracts пока существует только неявно или фрагментарно;
- в old plan artifacts могли оставаться assumptions, которые не всплывут без аккуратной migration map;
- без отдельного completion gate снова смешаются safety findings, repository cleanup и planning новых workflow;
- если удалить старые plan artifacts без переноса их содержательных решений, можно потерять target intent по структуре workspace и очередности feature wave.

## External touchpoints

- `C:\Users\avramko\OneDrive\Documents\Career\vacancies\` — чтение / проверка — фактические vacancy artifacts и рассинхронизация с runtime;
- `C:\Users\avramko\OneDrive\Documents\Career\agent_memory\` — чтение / проверка — workflow contracts и runtime state;
- `C:\Users\avramko\OneDrive\Documents\Career\response-monitoring.xlsx` — чтение / проверка — фактический Excel contract;
- `C:\Users\avramko\OneDrive\Documents\Career\CV\` — чтение / проверка — source-of-truth для resume branch;
- `C:\Users\avramko\OneDrive\Documents\Career\plans\` — historical touchpoint; superseded root planning artifacts уже мигрированы и удалены;
- `C:\Users\avramko\OneDrive\Documents\Career\tooling\run-ingest-analyze.md` и `tooling\git-workflow.md` — чтение / проверка — operator-facing contract.

## Milestones

### M1. Repository Evidence Baseline

- Status: `done`
- Goal:
  - зафиксировать подтверждённую карту репозитория, текущих подсистем и основных противоречий;
  - определить самостоятельные workstreams и опорный master plan для продолжения.
- Deliverables:
  - этот master plan;
  - список подтверждённых фактов, contradictions, assumptions, blockers и open questions;
  - разбиение дальнейшей работы на отдельные планы.
- Acceptance criteria:
  - master plan описывает текущую картину проекта без опоры на устные пояснения;
  - перечислены ключевые подсистемы, external touchpoints и подтверждённые несоответствия;
  - определён один конкретный `Next step` для следующей сессии.
- Validation commands:
  - `Get-ChildItem vacancies -Directory`
  - `Test-Path "C:\Users\avramko\OneDrive\Documents\Career\vacancies\20260421-dinamichno-razvivayuschayasya-sudohodnaya-kompaniya-direktor-po-tsifrovomu-razvitiyu-i-tehnologiyam-cto-02"`
  - `python -m unittest discover -s tests`
- Notes / discoveries:
  - `unittest` проходит, `pytest` отсутствует.
  - runtime memory ссылается на несуществующие vacancy folders.
  - design intent, code и root artifacts заметно разошлись.

### M2. Workflow Contracts And Safety Alignment

- Status: `done`
- Goal:
  - привести текущие workflow, memory contracts и mutation/publication behavior к единой, проверяемой модели;
  - убрать скрытые side effects и зафиксировать safety boundary.
- Deliverables:
  - workstream plan: `2026-04-21-workflow-contract-alignment-and-safety.md`;
  - contract matrix current vs intended behavior;
  - backlog по core-логике и safety.
- Acceptance criteria:
  - для `bootstrap`, `ingest-vacancy`, `analyze-vacancy`, runtime memory, Excel и git-публикации есть единое описание current state;
  - зафиксированы решения по auto-publish, stale runtime и validation baseline.
- Validation commands:
  - `python run_agent.py --root ../.. list-workflows`
  - `python run_agent.py --root ../.. show-memory`
  - `python -m unittest discover -s tests`
- Notes / discoveries:
  - workstream завершён отдельным планом и больше не должен трактоваться как автоматический trigger для немедленного старта нового workflow.

### M3. Repository Cleanup, Root Normalization, And Plan Artifact Migration

- Status: `in_progress`
- Goal:
  - навести порядок в root data/template/output layer;
  - перенести содержимое superseded planning artifacts в актуальные plan files;
  - удалить старые plan/spec files после миграции.
- Deliverables:
  - workstream plan: `2026-04-21-root-artifacts-and-output-normalization.md`;
  - source-of-truth map для root-слоёв и historical artifacts;
  - migration map для `plans/resume-agent-spec.md`, `plans/repository-topology.md`, `tooling/application-agent/plans/ingest-refactor-plan.md`;
  - удаление superseded planning artifacts после переноса содержательных решений.
- Acceptance criteria:
  - для ключевых root-каталогов и output families определены producer, consumer, status и canonical role;
  - содержимое старых plan/spec artifacts распределено по актуальным plans;
  - superseded plan/spec files удалены из репозитория без потери значимого target intent.
- Validation commands:
  - `Get-Content -Raw plans\2026-04-21-root-artifacts-and-output-normalization.md`
  - `Test-Path "C:\Users\avramko\OneDrive\Documents\Career\plans\resume-agent-spec.md"`
  - `Test-Path "C:\Users\avramko\OneDrive\Documents\Career\plans\repository-topology.md"`
  - `Test-Path "C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\plans\ingest-refactor-plan.md"`
- Notes / discoveries:
  - cleanup включает не только root data/output layer, но и migration/removal старых planning artifacts;
  - M1 workstream-шаг по inventory/migration map закрыт; следующий фокус M3 — canonical root contracts и output-placement decisions.

### M4. Current Workflow Completion Gate

- Status: `planned`
- Goal:
  - после M3 явно определить, что именно ещё не доведено в `bootstrap`, `ingest-vacancy`, `analyze-vacancy`;
  - отделить незавершённости текущего стека от planning remaining workflows.
- Deliverables:
  - completion gate для текущего workflow-стека;
  - отдельный plan/checklist по незакрытым задачам current workflow stack;
  - обновлённый `Current state` в master plan.
- Acceptance criteria:
  - однозначно зафиксировано, что считается "доделанным" для текущего workflow-стека;
  - у remaining workflows есть явный dependency gate;
  - `prepare-screening` больше не выглядит следующим шагом до завершения M4.
- Validation commands:
  - `Get-Content -Raw plans\2026-04-21-repository-reconstruction-and-backlog.md`
  - `Get-Content -Raw plans\2026-04-21-workflow-contract-alignment-and-safety.md`
  - `python run_agent.py --root ../.. list-workflows`
- Notes / discoveries:
  - safety-план закрыл boundary и guardrails, но не дал ответа на вопрос, что считать минимально завершённым состоянием current workflow stack.

### M5. Ordered Planning For Remaining Workflows

- Status: `planned`
- Goal:
  - только после M3 и M4 спланировать remaining workflows: `prepare-screening`, `rebuild-master`, `rebuild-role-resume`, `build-linkedin`, `export-resume-pdf`.
- Deliverables:
  - ordered planning backlog для remaining workflows;
  - feature plans, которые допустимо открывать после completion gate;
  - обновлённая последовательность реализации без опоры на superseded docs.
- Acceptance criteria:
  - planning remaining workflows начинается только после repository cleanup и current workflow completion gate;
  - `prepare-screening` и остальные future workflows не стартуют раньше времени;
  - queue remaining workflows опирается на актуальные plans, а не на удалённые артефакты.
- Validation commands:
  - `Get-Content -Raw plans\2026-04-21-repository-reconstruction-and-backlog.md`
  - `Get-Content -Raw plans\2026-04-21-root-artifacts-and-output-normalization.md`
  - `Get-Content -Raw plans\2026-04-21-prepare-screening-workflow.md`
- Notes / discoveries:
  - без M3 и M4 feature wave снова смешает roadmap, cleanup и текущие незавершённости.

## Decision log

- `2026-04-21 16:43` — Главный план ведётся в `tooling/application-agent/plans/`, потому что основная логика изменений относится к submodule-коду и его контрактам. — Это соответствует `AGENTS.md` в корне и в submodule. — Все root artifacts рассматриваются как external touchpoints.
- `2026-04-21 16:43` — Работа разбита на самостоятельные workstreams по safety и root normalization. — Это уменьшает риск смешать cleanup, contract alignment и future features. — Master plan фиксирует их зависимость и порядок.
- `2026-04-21 19:51` — Следующим активным этапом выбран repository cleanup через `2026-04-21-root-artifacts-and-output-normalization.md`. — Причина: сначала нужно навести порядок в репозитории и мигрировать superseded plan artifacts. — `prepare-screening` больше не считается следующим execution step.
- `2026-04-21 19:51` — Старые плановые артефакты (`plans/resume-agent-spec.md`, `plans/repository-topology.md`, `tooling/application-agent/plans/ingest-refactor-plan.md`) должны быть не просто помечены, а содержательно перенесены в новые active plans и затем удалены. — Это убирает конкурирующие источники истины. — Migration/removal включены в M3.
- `2026-04-21 19:51` — Planning remaining workflows отложен за completion gate по текущему workflow-стеку. — Safety findings недостаточно, чтобы считать `ingest-vacancy` и `analyze-vacancy` полностью доведёнными. — До завершения M4 feature expansion не является следующим шагом.
- `2026-04-21 20:35` — M1 в workstream-плане root normalization завершён: добавлены inventory matrix и migration map, зафиксировано, какие root artifacts реально участвуют в runtime сегодня. — Это сместило активный шаг M3 с инвентаризации на canonical root contract decisions. — Master plan синхронизирован с новым состоянием workstream-а.

## Progress log

- `2026-04-21 16:43` — Проведена первичная разведка корня, `tooling/`, submodule-кода, тестов, шаблонов, runtime-памяти, vacancy-артефактов, legacy prompt-материалов и manual output traces. — `python -m unittest discover -s tests` -> `36 tests, OK`; `pytest` отсутствует; runtime memory указывает на несуществующие vacancy folders. — Status: `in_progress`.
- `2026-04-21 16:43` — Создан master plan и выделены самостоятельные workstreams для дальнейшей работы без повторного обследования. — Валидация опирается на файловую структуру, `unittest` и документированные команды CLI. — Status: `in_progress`.
- `2026-04-21 19:51` — Master plan пересобран после повторного review всех plans и superseded artifacts. — Последовательность зафиксирована как `M3 cleanup -> M4 completion gate -> M5 planning remaining workflows`. — Status: `in_progress`.
- `2026-04-21 19:51` — Superseded plan/spec artifacts мигрированы в active plans и удалены из репозитория. — Валидация migration/removal теперь опирается на `Test-Path = False` для старых файлов и на содержимое новых plan files. — Status: `in_progress`.
- `2026-04-21 20:35` — M1 в workstream-плане root normalization завершён: добавлены inventory matrix и migration map, подтверждено, что runtime реально живёт на `CV/`, `vacancies/`, `agent_memory/` и Excel, а `profile/`, `knowledge/`, `adoptions/` пока остаются целевыми stores. — M1 validation passed with `root/plans = False`, `profile/contact-regions.yml = False` and 3 current vacancy directories; активный шаг M3 смещён на canonical root contracts. — Status: `in_progress`.

## Current state

- Current milestone: `M3`
- Current status: `in_progress`
- Next step: `Продолжить M3 через M2 плана 2026-04-21-root-artifacts-and-output-normalization.md: определить canonical root contracts для CV, profile, knowledge, adoptions, vacancies, Excel и legacy corpus, а также снять конфликт vacancy-local и root-level adoptions.`
- Active blockers:
  - Не определён canonical root contract для `profile/`, `knowledge/`, `adoptions/`, output pipeline и legacy prompt corpus.
  - Не зафиксирован отдельный completion gate по текущему workflow-стеку после safety workstream.
- Open questions:
  - Какой набор `bootstrap` / `ingest-vacancy` / `analyze-vacancy` нужно считать минимально завершённым до M5?
  - Нужно ли после M3 открывать отдельный plan по completion gate текущих workflow или достаточно checklist внутри master plan?
  - Должен ли `vacancies/<id>/adoptions.md` оставаться текущим generated artifact после появления root-level adoptions contract?

## Completion summary

Заполняется после завершения M1-M5. На текущем этапе master plan находится в фазе repository cleanup и migration/removal superseded planning artifacts.
