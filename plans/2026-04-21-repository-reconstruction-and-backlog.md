# Repository Reconstruction And Backlog

- Title: `Repository reconstruction and backlog`
- Slug: `2026-04-21-repository-reconstruction-and-backlog`
- Owner: `Codex`
- Created: `2026-04-21`
- Last updated: `2026-04-22 10:14`
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
- root-слой содержит незавершённые long-lived stores (`knowledge/`, `profile/`, `adoptions/`) и manual/historical artifacts (`employers/`, `archive/`, `promts/`);
- superseded plan/spec artifacts (`plans/resume-agent-spec.md`, `plans/repository-topology.md`, `tooling/application-agent/plans/ingest-refactor-plan.md`) мигрированы в active plans и удалены.

Содержательно из старых артефактов уже мигрированы или подлежат миграции в новую структуру следующие намерения:

- public/private split: код и инженерные решения живут в `tooling/application-agent`, root хранит данные, шаблоны, результаты и orchestration artifacts;
- target workflow catalog: `prepare-screening`, `rebuild-master`, `rebuild-role-resume`, `build-linkedin`, `export-resume-pdf`;
- source-of-truth rules: `resumes/MASTER.md` остаётся главным фактическим источником о кандидате, ролевые resumes — производные, contact/profile overlays должны жить отдельно от resume text;
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
- изменение фактического содержимого `resumes/`, `knowledge/`, `profile/`, `adoptions/`;
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
- `C:\Users\avramko\OneDrive\Documents\Career\resumes\` — чтение / проверка — source-of-truth для resume branch;
- `C:\Users\avramko\OneDrive\Documents\Career\plans\` — historical touchpoint; superseded root planning artifacts уже мигрированы и удалены;
- `C:\Users\avramko\OneDrive\Documents\Career\tooling\run-ingest-analyze.md` и `tooling\git-workflow.md` — чтение / проверка — operator-facing contract.

## Milestones

### M1. Repository Evidence Baseline

- Status: `done`
- Goal:
  - зафиксировать подтвержденную карту репозитория, текущих подсистем и основных противоречий;
  - определить самостоятельные workstreams и опорный master plan для продолжения.
- Deliverables:
  - этот master plan;
  - список подтвержденных фактов, contradictions, assumptions, blockers и open questions;
  - разбиение дальнейшей работы на отдельные планы.
- Acceptance criteria:
  - master plan описывает текущую картину проекта без опоры на устные пояснения;
  - перечислены ключевые подсистемы, external touchpoints и подтвержденные несоответствия;
  - определен один конкретный `Next step` для следующей сессии.
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
  - workstream завершен отдельным планом и больше не должен трактоваться как автоматический trigger для немедленного старта нового workflow.

### M3. Repository Cleanup, Root Normalization, And Plan Artifact Migration

- Status: `done`
- Goal:
  - навести порядок в root data/template/output layer;
  - перенести содержимое superseded planning artifacts в актуальные plan files;
  - удалить старые plan/spec files после миграции.
- Deliverables:
  - workstream plan: `2026-04-21-root-artifacts-and-output-normalization.md`;
  - source-of-truth map для root-слоев и historical artifacts;
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
  - M1 workstream-шаг по inventory/migration map закрыт; M2 canonical root contracts тоже закрыт; M3 output-placement decisions тоже закрыты;
  - финальный cleanup substep по legacy prompt/doc distillation тоже закрыт, поэтому master M3 завершён полностью.

### M4. Current Workflow Completion Gate

- Status: `in_progress`
- Goal:
  - после M3 явно определить, что именно еще не доведено в `bootstrap`, `ingest-vacancy`, `analyze-vacancy`;
  - отделить незавершенности текущего стека от planning remaining workflows.
- Deliverables:
  - completion gate для текущего workflow-стека;
  - отдельный plan/checklist по незакрытым задачам current workflow stack (`2026-04-22-current-workflow-completion-gate.md`);
  - обновленный `Current state` в master plan.
- Acceptance criteria:
  - однозначно зафиксировано, что считается "доделанным" для текущего workflow-стека;
  - у remaining workflows есть явный dependency gate;
  - `prepare-screening` больше не выглядит следующим шагом до завершения M4.
- Validation commands:
  - `Get-Content -Raw plans\2026-04-21-repository-reconstruction-and-backlog.md`
  - `Get-Content -Raw plans\2026-04-21-workflow-contract-alignment-and-safety.md`
  - `python run_agent.py --root ../.. list-workflows`
- Notes / discoveries:
  - safety-план закрыл boundary и guardrails, но не дал ответа на вопрос, что считать минимально завершенным состоянием current workflow stack.
  - dedicated plan `2026-04-22-current-workflow-completion-gate.md` открыт как рабочий артефакт для этого milestone.
  - gate decisions уже приняты; текущий follow-up внутри master M4 — исполнить remediation plan `2026-04-22-current-stack-contract-remediation.md` и снять найденные blocker-ы.

### M5. Ordered Planning For Remaining Workflows

- Status: `planned`
- Goal:
  - только после M3 и M4 спланировать remaining workflows: `prepare-screening`, `rebuild-master`, `rebuild-role-resume`, `build-linkedin`, `export-resume-pdf`.
- Deliverables:
  - ordered planning backlog для remaining workflows;
  - feature plans, которые допустимо открывать после completion gate;
  - обновленная последовательность реализации без опоры на superseded docs.
- Acceptance criteria:
  - planning remaining workflows начинается только после repository cleanup и current workflow completion gate;
  - `prepare-screening` и остальные future workflows не стартуют раньше времени;
  - queue remaining workflows опирается на актуальные plans, а не на удаленные артефакты.
- Validation commands:
  - `Get-Content -Raw plans\2026-04-21-repository-reconstruction-and-backlog.md`
  - `Get-Content -Raw plans\2026-04-21-root-artifacts-and-output-normalization.md`
  - `Get-Content -Raw plans\2026-04-21-prepare-screening-workflow.md`
- Notes / discoveries:
  - без M3 и M4 feature wave снова смешает roadmap, cleanup и текущие незавершенности.

## Decision log

- `2026-04-21 16:43` — Главный план ведется в `tooling/application-agent/plans/`, потому что основная логика изменений относится к submodule-коду и его контрактам. — Это соответствует `AGENTS.md` в корне и в submodule. — Все root artifacts рассматриваются как external touchpoints.
- `2026-04-21 16:43` — Работа разбита на самостоятельные workstreams по safety и root normalization. — Это уменьшает риск смешать cleanup, contract alignment и future features. — Master plan фиксирует их зависимость и порядок.
- `2026-04-21 19:51` — Следующим активным этапом выбран repository cleanup через `2026-04-21-root-artifacts-and-output-normalization.md`. — Причина: сначала нужно навести порядок в репозитории и мигрировать superseded plan artifacts. — `prepare-screening` больше не считается следующим execution step.
- `2026-04-21 19:51` — Старые плановые артефакты (`plans/resume-agent-spec.md`, `plans/repository-topology.md`, `tooling/application-agent/plans/ingest-refactor-plan.md`) должны быть не просто помечены, а содержательно перенесены в новые active plans и затем удалены. — Это убирает конкурирующие источники истины. — Migration/removal включены в M3.
- `2026-04-21 19:51` — Planning remaining workflows отложен за completion gate по текущему workflow-стеку. — Safety findings недостаточно, чтобы считать `ingest-vacancy` и `analyze-vacancy` полностью доведенными. — До завершения M4 feature expansion не является следующим шагом.
- `2026-04-21 20:35` — M1 в workstream-плане root normalization завершен: добавлены inventory matrix и migration map, зафиксировано, какие root artifacts реально участвуют в runtime сегодня. — Это сместило активный шаг M3 с инвентаризации на canonical root contract decisions. — Master plan синхронизирован с новым состоянием workstream-а.
- `2026-04-21 21:02` — M2 в workstream-плане root normalization завершен: canonical contracts закреплены для `resumes`, `profile`, `knowledge`, `adoptions`, `vacancies`, Excel, templates и legacy corpus. — Это снимает часть source-of-truth конфликтов и переводит активный шаг M3 на output placement clarification. — Master plan обновлен без изменения общей очередности `M3 -> M4 -> M5`.
- `2026-04-21 20:33` — M3 output-placement decisions в root-normalization workstream закрыты: `vacancies/<id>/` зафиксирован как working output layer для vacancy-scoped generation, `profile/` — как home для durable profile derivatives, а `archive/`, `resumes/versions/` и `employers/` — как manual-only historical/reference layers вне runtime и agent workflows. — Это снимает blocker по output home/lifecycle policy и оставляет в M3 только legacy corpus distillation. — Master sequencing `M3 -> M4 -> M5` сохраняется.
- `2026-04-22 09:10` — Legacy prompt/doc corpus дистиллирован в root-normalization workstream plan: `promts/*.md` разнесены по будущим workflow-направлениям, `responses.md` закреплён как historical vacancy corpus, а `adoptions_00.md` — как historical adoption corpus/examples bank. — Это закрывает последний cleanup substep master M3 и позволяет перейти к explicit current workflow completion gate. — Active milestone смещён на M4.
- `2026-04-22 09:10` — Для master M4 открыт отдельный plan `2026-04-22-current-workflow-completion-gate.md`. — Completion gate требует собственного contradiction ledger и явного решения по blocker-ам текущего стека. — Следующий execution focus переносится в этот новый plan.
- `2026-04-22 09:17` — В completion-gate plan собран contradiction ledger и draft completion matrix. — Это завершило baseline-сборку и проявило три главных gate-topic: `bootstrap` catalog boundary, `CV/` vs `resumes/` drift и Excel dependency policy. — Master M4 теперь находится в стадии решений, а не разведки.
- `2026-04-22 10:03` — Completion gate доведён до явных решений: `bootstrap` признан setup-only command, `resumes/` — единственным valid resume root, а `response-monitoring.xlsx` — hard prerequisite для текущего ingest path. — Эти решения упакованы в отдельный remediation plan `2026-04-22-current-stack-contract-remediation.md`. — Master M4 остаётся активным до снятия blocker-ов через этот remediation plan.
- `2026-04-22 10:14` — В remediation plan закрыт M1 по `bootstrap` catalog boundary: `WORKFLOW_CATALOG` и runtime memory синхронизированы под setup-only semantics, а `README.md` больше не описывает `bootstrap` как runtime workflow. — Это снимает первый blocker внутри master M4 и переводит execution focus на path remediation `CV/` -> `resumes/`. — Master plan остаётся в M4 до закрытия remaining blocker-ов.

## Progress log

- `2026-04-21 16:43` — Проведена первичная разведка корня, `tooling/`, submodule-кода, тестов, шаблонов, runtime-памяти, vacancy-артефактов, legacy prompt-материалов и manual output traces. — `python -m unittest discover -s tests` -> `36 tests, OK`; `pytest` отсутствует; runtime memory указывает на несуществующие vacancy folders. — Status: `in_progress`.
- `2026-04-21 16:43` — Создан master plan и выделены самостоятельные workstreams для дальнейшей работы без повторного обследования. — Валидация опирается на файловую структуру, `unittest` и документированные команды CLI. — Status: `in_progress`.
- `2026-04-21 19:51` — Master plan пересобран после повторного review всех plans и superseded artifacts. — Последовательность зафиксирована как `M3 cleanup -> M4 completion gate -> M5 planning remaining workflows`. — Status: `in_progress`.
- `2026-04-21 19:51` — Superseded plan/spec artifacts мигрированы в active plans и удалены из репозитория. — Валидация migration/removal теперь опирается на `Test-Path = False` для старых файлов и на содержимое новых plan files. — Status: `in_progress`.
- `2026-04-21 20:35` — M1 в workstream-плане root normalization завершен: добавлены inventory matrix и migration map, подтверждено, что runtime реально живет на `resumes/`, `vacancies/`, `agent_memory/` и Excel, а `profile/`, `knowledge/`, `adoptions/` пока остаются целевыми stores. — M1 validation passed with `root/plans = False`, `profile/contact-regions.yml = False` and 3 current vacancy directories; активный шаг M3 смещен на canonical root contracts. — Status: `in_progress`.
- `2026-04-21 21:02` — M2 в workstream-плане root normalization завершен: canonical contract map зафиксировал разделение между durable root stores, generated vacancy-local artifacts и historical/reference layers. — Ключевой результат: root `adoptions/` признан long-lived review layer, а `vacancies/<id>/adoptions.md` — staging artifact текущего runtime. — Status: `in_progress`.
- `2026-04-21 20:33` — M3 output-placement substep в root-normalization workstream закрыт: validation confirmed the current contents of `employers/`, `archive/` и `resumes/versions/`, after which placement and lifecycle rules were fixed in the workstream plan. — Следующий cleanup focus внутри master M3 переместился на legacy prompt/doc distillation (`promts/`, `responses.md`, `adoptions_00.md`). — Status: `in_progress`.
- `2026-04-22 09:10` — Master M3 закрыт: root-normalization workstream завершён полностью после фиксации distillation map по `promts/*.md`, `responses.md` и `adoptions_00.md`, а также подтверждения, что старые root plan/spec artifacts по-прежнему отсутствуют. — Cleanup больше не является активным этапом; следующий шаг смещён на explicit completion gate текущего workflow-стека. — Status: `done`.
- `2026-04-22 09:10` — Master M4 стартовал: создан отдельный plan `2026-04-22-current-workflow-completion-gate.md` и зафиксирован initial baseline по CLI, runtime memory и tests. — `list-workflows` показывает только `ingest-vacancy` и `analyze-vacancy`, тогда как `show-memory` и `WORKFLOW_CATALOG` всё ещё включают `bootstrap`; `unittest` остаётся зелёным (`39 tests, OK`). — Status: `in_progress`.
- `2026-04-22 09:17` — M4 продолжен внутри dedicated plan: baseline доведён до contradiction ledger и candidate completion criteria. — Дополнительная проверка показала реальный runtime blocker по path contract (`resumes/` существует, `CV/` отсутствует, но код всё ещё читает `CV/`) и незакрытый policy question по `response-monitoring.xlsx`. — Status: `in_progress`.
- `2026-04-22 10:03` — Stage решений завершён: completion-gate plan закрыт как planning artifact, а следующий execution step перенесён в `2026-04-22-current-stack-contract-remediation.md`. — Это отделяет определение blocker-ов от их исправления и делает master M4 исполнимым. — Status: `in_progress`.
- `2026-04-22 10:14` — Первый remediation substep завершён: `python run_agent.py --root ../.. list-workflows` теперь согласован с `project_memory.workflow_catalog`, а `python -m unittest tests.test_memory_store tests.test_cli` проходит (`5 tests, OK`). — Bootstrap catalog drift снят; remaining focus внутри M4 смещён на `CV/` -> `resumes/` и explicit Excel prerequisite. — Status: `in_progress`.

## Current state

- Current milestone: `M4`
- Current status: `in_progress`
- Next step: `Продолжить plan `2026-04-22-current-stack-contract-remediation.md` с M2 path remediation (`CV/` -> `resumes/`) в active и adjacent workflow surface.`
- Active blockers:
  - Current stack всё ещё имеет runtime/path drift между кодом и реальным root contract (`CV/` vs `resumes/`).
  - Excel prerequisite policy ещё не реализована как явный operator-visible contract.
- Open questions:
  - Какой набор `bootstrap` / `ingest-vacancy` / `analyze-vacancy` нужно считать минимально завершенным до M5?
  - Нужно ли path remediation ограничивать current stack, или сразу включать adjacent `prepare-screening` contract?

## Completion summary

Заполняется после завершения M1-M5. На текущем этапе cleanup и migration/removal superseded planning artifacts завершены; активная фаза смещена на M4 current workflow completion gate.

