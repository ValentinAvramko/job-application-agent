# Repository Reconstruction And Backlog

- Title: `Repository reconstruction and backlog`
- Slug: `2026-04-21-repository-reconstruction-and-backlog`
- Owner: `Codex`
- Created: `2026-04-21`
- Last updated: `2026-04-23 09:17`
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

- Status: `done`
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

- Status: `in_progress`
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
- `2026-04-22 10:17` — В remediation plan закрыт M2 по resume path alignment: `analyze-vacancy`, adjacent `prepare-screening`, их tests и operator-facing runbook переведены с `CV/` на `resumes/`. — Это снимает path drift между кодом и фактическим root contract; в master M4 остаётся только явная реализация Excel prerequisite policy. — Следующий execution focus смещён на M3 remediation.
- `2026-04-22 10:23` — В remediation plan закрыт M3 по Excel prerequisite contract: `ingest-vacancy` теперь fail-fast валидирует `response-monitoring.xlsx`, а tests и operator-facing docs описывают workbook как обязательный prerequisite. — Это снимает последний содержательный blocker master M4; остаётся только финальная валидация и handback в completion gate/master sequencing. — Следующий execution focus смещён на M4 remediation validation.
- `2026-04-22 10:26` — Remediation plan завершён полностью: финальная validation подтвердила согласованность `list-workflows` и runtime memory, допустимость report-first stale history и зелёный full `unittest` baseline (`42 tests, OK`). — Master M4 можно считать закрытым; dependency gate перед M5 снят. — Следующий execution focus переносится на ordered planning remaining workflows.
- `2026-04-22 10:41` — M5 переведён в исполнение: после повторной сверки ordered backlog и существующих планов первым remaining workflow выбран `prepare-screening`. — У него уже есть реализованное ядро и test coverage, а остальные workflow по-прежнему упираются в незакрытые root/product contracts. — Следующий execution focus смещён на M2 плана `2026-04-21-prepare-screening-workflow.md`.
- `2026-04-22 10:58` — Первый execution milestone внутри M5 закрыт: `prepare-screening` встроен в runtime CLI/catalog surface и подтверждён targeted validation. — Это превращает plan из latent implementation branch в реально доступный workflow текущего стека. — Следующий execution focus смещён на M3 того же плана: full suite и real-scenario smoke run.
- `2026-04-22 11:08` — `prepare-screening` завершён как первый remaining workflow: full suite остаётся зелёным, а smoke run на реальной вакансии подтвердил создание `screening.md`, update `meta.yml` и runtime-memory trail без выхода за vacancy-local boundary. — Это закрывает первый execution branch внутри M5. — Следующий execution focus смещён на открытие dedicated plan для `rebuild-master`, где пока не определены permanent-signal/accepted-adoption contracts.
- `2026-04-22 11:18` — Для следующего workflow открыт dedicated plan `2026-04-22-rebuild-master-workflow.md`. — Базовая разведка показала, что `resumes/MASTER.md`, `adoptions/accepted/` и `knowledge/roles/` уже существуют, но canonical merge contract между ними не закреплён. — Следующий execution focus теперь сводится к одному owner-level решению по permanent-signal destination.
- `2026-04-22 11:42` — Owner-level sequencing уточнён: перед `rebuild-master` появился отдельный upstream process для review/acceptance signals (`inbox/` + `questions/` -> `accepted/` + `knowledge/roles`). — Это меняет не только contract, но и очередь remaining workflows внутри M5. — Для нового upstream process открыт dedicated plan `2026-04-22-adoptions-review-and-acceptance-workflow.md`.
- `2026-04-22 13:50` — Upstream review/acceptance plan уточнён до конкретной interaction shape: deterministic intake step отдельно готовит `inbox/` и `questions/`, а отдельная interactive Q&A session обновляет `accepted/MASTER.md` и при необходимости `knowledge/roles/`. — Это снимает двусмысленность текущего шага внутри M5. — Следующим execution focus становится уже code-facing decomposition этого upstream workflow.
- `2026-04-22 15:53` — Planning для upstream review/acceptance workflow завершён: создан dedicated execution plan `2026-04-22-implement-adoptions-review-and-acceptance-workflow.md`, а initial implementation shape закреплена как `runtime intake` + `agent-guided review support`. — Это превращает M5 шаг из planning branch в прямой execution backlog. — Следующий execution focus смещён на M1 нового execution plan.
- `2026-04-22 19:33` — Для следующего remaining workflow открыт dedicated plan `2026-04-22-build-linkedin-workflow.md`. — Baseline inventory подтвердил, что `build-linkedin` ещё не реализован, `profile/` пока почти пуст, а главный blocker сводится к first executable contract по LinkedIn artifacts и profile metadata overlay. — Execution focus внутри M5 теперь перенесён в M2 нового dedicated plan.
- `2026-04-23 08:57` — В dedicated plan `build-linkedin` закрыт M2 contract milestone: first executable version теперь фиксирует per-role pack `profile/linkedin/<target_role>.md`, обязательный `target_role`, `MASTER` как единственный factual source, role resume как positioning overlay и optional `profile/contact-regions.yml` только для profile surface. — Это снимает product blocker внутри M5 и переводит execution focus с contract discussion на M3 helper implementation. — Следующий execution step теперь уже кодовый, а не planning-only.
- `2026-04-23 09:17` — В dedicated plan `build-linkedin` закрыт M3 helper milestone: deterministic builder `application_agent.linkedin_builder` теперь собирает per-role LinkedIn pack, уважает precedence `MASTER -> role resume -> optional profile metadata`, держит private contacts только во filling guide и маркирует missing EN/profile-surface inputs через `CHECK` / `GAP`. — Это снимает implementation blocker по helper layer и переводит execution focus master M5 на M4 workflow wiring для `build-linkedin`. — Следующий execution step снова чётко сводится к runtime integration.

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
- `2026-04-22 10:17` — Второй remediation substep завершён: targeted search по workflow/tests/runbook больше не находит `CV` path references, а `python -m unittest tests.test_analyze_workflow tests.test_prepare_screening_workflow` проходит (`5 tests, OK`). — Resume path drift снят; активным blocker-ом внутри master M4 остаётся только explicit Excel prerequisite contract. — Status: `in_progress`.
- `2026-04-22 10:23` — Третий remediation substep завершён: `ingest-vacancy` больше не создаёт partial vacancy scaffold без workbook, а `python -m unittest tests.test_ingest_workflow tests.test_analyze_workflow tests.test_prepare_screening_workflow` проходит (`29 tests, OK`). — Все содержательные blocker-ы M4 сняты; master plan переходит к финальной remediation validation и handback. — Status: `in_progress`.
- `2026-04-22 10:26` — Master M4 закрыт: `python run_agent.py --root ../.. list-workflows`, `python run_agent.py --root ../.. show-memory` и `python -m unittest discover -s tests` подтверждают, что current stack больше не имеет скрытых contract blocker-ов для feature planning. — Следующий этап master sequencing смещён на M5 ordered planning for remaining workflows. — Status: `done`.
- `2026-04-22 10:41` — M5 revalidation завершена: evidence из safety/root plans и текущего кода подтверждает, что `prepare-screening` остаётся первым исполнимым кандидатом, потому что уже имеет runtime core, тогда как `rebuild-master`, `rebuild-role-resume`, `build-linkedin` и `export-resume-pdf` всё ещё зависят от отдельных downstream contracts. — Кодовая реализация M5 начинается с CLI/catalog/operator integration для `prepare-screening`. — Status: `in_progress`.
- `2026-04-22 10:58` — CLI/catalog/operator integration для `prepare-screening` завершена: targeted tests и `list-workflows` подтверждают, что workflow теперь зарегистрирован и доступен через public entrypoint. — Master M5 остаётся активным, потому что для полного handoff этого первого remaining workflow ещё нужен M3 smoke-check на реальном vacancy scenario. — Status: `in_progress`.
- `2026-04-22 11:08` — Первый remaining workflow закрыт end-to-end: `prepare-screening` теперь реализован, провалидирован и опробован на реальной вакансии. — Master M5 продолжается уже не вокруг этого workflow, а вокруг следующего dependency-gated этапа `rebuild-master`. — Status: `in_progress`.
- `2026-04-22 11:18` — M5 продолжен через dedicated plan для `rebuild-master`: baseline contract inventory собран, а активный blocker сведён к product decision по permanent signals и accepted adoptions. — Это отделяет реальную нехватку решения от технической неопределённости и не даёт prematurely стартовать risky resume-editing workflow. — Status: `in_progress`.
- `2026-04-22 11:42` — M5 перепоследован после owner clarification: ближайшим planning/execution step теперь является отдельный review/acceptance workflow, а `rebuild-master` переведён в downstream-зависимость от него. — Это повышает качество sequencing: сначала approval/normalization, потом master mutation, потом role rebuild. — Status: `in_progress`.
- `2026-04-22 13:50` — В dedicated plan review/acceptance закрыт M2: interaction shape и file contract теперь закреплены без product ambiguity, включая shared ledger `adoptions/questions/open.md`, separate intake stage и отсутствие role-specific accepted artifacts. — Remaining work внутри M5 теперь сводится не к выбору модели, а к implementation-ready decomposition. — Status: `in_progress`.
- `2026-04-22 15:53` — Dedicated planning plan review/acceptance завершён полностью: создан execution plan с отдельными milestones для intake workflow, review helper layer, agent-guided review support и rebuild-master handoff. — Ordered workflow backlog внутри M5 снова стал исполнимым без дополнительных product решений. — Status: `in_progress`.
- `2026-04-22 18:49` — Upstream review/acceptance execution и downstream `rebuild-master` завершены end-to-end: `README.md` и dedicated plan фиксируют final contract, а full validation baseline подтверждён (`python -m unittest discover -s tests` -> `OK (57 tests)`, `list-workflows`, `show-memory`). — Sequencing ambiguity для `MASTER` снята; следующий remaining-workflow step внутри M5 теперь сводится к открытию dedicated plan для `rebuild-role-resume`. — Status: `in_progress`.
- `2026-04-22 19:33` — Dedicated plan для `build-linkedin` открыт и доведён до baseline M1: подтверждено отсутствие workflow-кода, пустой почти `profile/` layer и наличие only-historical prompt map в `promts/promt-create-linkedin-profile.md`. — M5 остаётся активным, но его текущий blocker теперь narrowed до одного contract-decision milestone внутри нового плана. — Status: `in_progress`.
- `2026-04-22 20:05` — `rebuild-role-resume` завершён end-to-end: helper module, workflow wiring, runtime report, docs sync и full validation baseline подтверждены (`python -m unittest discover -s tests` -> `OK (62 tests)`, `list-workflows`, `show-memory`). — Sequencing для resume family теперь доведён от `accepted` до `MASTER` и выбранного role resume; следующий remaining-workflow step смещается на `build-linkedin`. — Status: `in_progress`.
- `2026-04-23 08:57` — Contract ambiguity для `build-linkedin` снята: dedicated plan M2 закрепил one-pack output `profile/linkedin/<target_role>.md`, обязательный `target_role`, deterministic precedence между `MASTER`, role resume и optional profile metadata, а также privacy-safe contact policy. — Validation опиралась на повторное чтение dedicated plan, `profile/README.md` и historical LinkedIn prompt map. — Status: `in_progress`.
- `2026-04-23 09:17` — Helper layer для `build-linkedin` реализован и провалидирован: `application_agent.linkedin_builder` рендерит deterministic artifact `profile/linkedin/<target_role>.md`, использует front matter `MASTER.md` как fallback profile surface, уважает optional metadata override и не выводит private contacts в public-ready blocks. — Validation: `python -m unittest tests.test_build_linkedin_helpers` -> `OK`. — Status: `in_progress`.

## Current state

- Current milestone: `M5`
- Current status: `in_progress`
- Next step: `Перейти в dedicated plan `2026-04-22-build-linkedin-workflow.md` и реализовать M4 workflow wiring: обернуть `application_agent.linkedin_builder` в executable `build-linkedin`, подключить registry/cli/config/runtime report и покрыть workflow/CLI tests.`
- Active blockers:
  - none
- Open questions:
  - none

## Completion summary

Заполняется после завершения M1-M5.

