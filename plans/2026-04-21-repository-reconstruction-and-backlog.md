# Repository Reconstruction And Backlog

- Title: `Repository reconstruction and backlog`
- Slug: `2026-04-21-repository-reconstruction-and-backlog`
- Owner: `Codex`
- Created: `2026-04-21`
- Last updated: `2026-04-21 16:43`
- Overall status: `in_progress`

## Objective

Зафиксировать текущее, подтвержденное состояние private/public workspace так, чтобы следующую работу по инструменту можно было продолжать без повторной разведки: с понятной картиной реализованных возможностей, незакрытых направлений, противоречий между кодом и документацией, а также с разбивкой дальнейшей работы на самостоятельные workstreams.

## Background and context

Корень `Career/` является private data/orchestration-слоем и содержит реальные резюме, вакансии, шаблоны, экспортные артефакты, историю ручной работы и служебные материалы. Код инструмента живет в submodule `tooling/application-agent/`, где уже реализованы CLI, файловая память, `ingest-vacancy`, `analyze-vacancy`, Excel-интеграция для `response-monitoring.xlsx`, парсинг HH/generic pages и Playwright fallback.

Разведка показала, что репозиторий опирается сразу на несколько слоев источников:

- исторические design-документы в корневом `plans/` (`resume-agent-spec.md`, `repository-topology.md`);
- legacy prompt corpus в `promts/` и больших Markdown-артефактах (`responses.md`, `adoptions_00.md`);
- текущую рабочую документацию в `tooling/` и `tooling/application-agent/README.md`;
- фактическую реализацию и тесты в `tooling/application-agent/src` и `tests`;
- реальные runtime- и vacancy-артефакты в корне.

Подтвержденные факты по текущему состоянию:

- код инструмента реализует только `bootstrap`, `ingest-vacancy`, `analyze-vacancy`;
- `python -m unittest discover -s tests` в `tooling/application-agent` проходит: `36 tests, OK`;
- `pytest` в текущем окружении отсутствует;
- корневые каталоги `knowledge/`, `adoptions/`, `profile/` в основном содержат только README/шаблоны, а не наполненные рабочие данные;
- `agent_memory/runtime/task-memory.json` и `workflow-runs.json` ссылаются на вакансии, которых уже нет в `vacancies/`, то есть runtime-состояние не синхронизировано с файловым слоем;
- в `tooling/application-agent/plans/` уже есть исторический `ingest-refactor-plan.md`, но он фиксирует только завершенный рефакторинг ingest и не покрывает общую картину проекта.

Ключевые противоречия, найденные во время обследования:

- `plans/resume-agent-spec.md` описывает 7 целевых операций и путь `tooling/public-agent/`, а текущий код реализует 2 workflow и фактически живет в `tooling/application-agent/`;
- `agent_memory/workflows/ingest-vacancy.md` говорит, что Excel-интеграция остается следующим шагом, хотя она уже реализована и покрыта тестами;
- `plans/resume-agent-spec.md` описывает Excel-схему A-J без `vacancy_id` в отдельной колонке, а `templates/excel/response-monitoring-mapping.md` и код используют A-K с `vacancy_id` в колонке A;
- CLI `ingest-vacancy` автоматически делает `git add/commit/push`, что конфликтует с design-правилом про публикацию только после подтверждения пользователя и с ручным flow из `tooling/git-workflow.md`.

## Scope

### In scope

- зафиксировать подтвержденную картину проекта и текущего технического состояния;
- разложить найденные направления работы на небольшие проверяемые milestones;
- выделить крупные workstreams и оформить для них отдельные планы в `tooling/application-agent/plans/`;
- зафиксировать assumptions, blockers, unknowns и открытые противоречия;
- определить один конкретный рекомендуемый `Next step` для следующей сессии.

### Out of scope

- реализация новых workflow или изменение текущей логики инструмента;
- наполнение `knowledge/`, `profile/`, `adoptions/` реальными пользовательскими данными;
- переписывание исторических root-документов вне случаев, когда это потребуется отдельным milestone;
- генерация новых PDF/LinkedIn/резюме-артефактов.

## Assumptions

- design-документы в корневом `plans/` отражают намерение и целевую модель, но не являются источником истины для текущей реализации;
- текущие `src/` и `tests/` в `tooling/application-agent` являются источником истины для уже поставленного поведения;
- исторические vacancy/output-артефакты могли быть удалены или архивированы, поэтому workflow log нельзя считать самодостаточно актуальным без сверки с файловой системой;
- следующая сессия должна стартовать из этих планов, а не из повторной полной разведки репозитория.

## Risks and unknowns

- скрытые git-side effects в `ingest-vacancy` могут приводить к несанкционированной публикации private-артефактов;
- runtime-память не синхронизирована с `vacancies/`, из-за чего CLI и дальнейшие workflow могут опираться на несуществующие сущности;
- часть root-контрактов пока только задумана: `profile/contact-regions.yml` отсутствует, `knowledge/roles/*.md` не заполнены, `adoptions/inbox` и `accepted` пусты;
- manual export pipeline существует вне инструмента (`Employers/TaxDome/render_resume_pdf.py`, PDF/DOCX в `archive/`), что усложняет выбор канонического output path;
- неизвестно, должен ли canonical Excel-контракт остаться A-K или быть возвращен к A-J;
- не определено, сохранять ли auto-commit/auto-push как feature или убрать как опасное побочное действие;
- не определено, какие legacy prompt-артефакты нужно конвертировать в тесты/спеки, а какие оставить как исторический reference.

## External touchpoints

- `C:\Users\avramko\OneDrive\Documents\Career\vacancies\` — чтение / проверка — подтверждение фактических vacancy-артефактов и рассинхронизации с runtime.
- `C:\Users\avramko\OneDrive\Documents\Career\agent_memory\` — чтение / проверка — фиксация workflow-контрактов и состояния памяти.
- `C:\Users\avramko\OneDrive\Documents\Career\response-monitoring.xlsx` — чтение / проверка — определение фактического Excel-контракта.
- `C:\Users\avramko\OneDrive\Documents\Career\CV\` — чтение / проверка — карта источников правды для резюме и output pipeline.
- `C:\Users\avramko\OneDrive\Documents\Career\templates\` — чтение / проверка — выявление template contracts и пробелов интеграции.
- `C:\Users\avramko\OneDrive\Documents\Career\promts\` — чтение / проверка — extraction legacy business rules и target operations.
- `C:\Users\avramko\OneDrive\Documents\Career\Employers\` и `C:\Users\avramko\OneDrive\Documents\Career\archive\` — чтение / проверка — восстановление manual output pipeline.
- `C:\Users\avramko\OneDrive\Documents\Career\tooling\git\` — чтение / проверка — сверка intended git flow с текущими side effects CLI.

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
  - мастер-план описывает текущую картину проекта без опоры на устные пояснения;
  - перечислены ключевые подсистемы, external touchpoints и подтвержденные несоответствия;
  - определен один конкретный `Next step` для следующей сессии.
- Validation commands:
  - `Get-ChildItem vacancies -Directory`
  - `Test-Path "C:\Users\avramko\OneDrive\Documents\Career\vacancies\20260421-dinamichno-razvivayuschayasya-sudohodnaya-kompaniya-direktor-po-tsifrovomu-razvitiyu-i-tehnologiyam-cto-02"`
  - `python -m unittest discover -s tests`
- Notes / discoveries:
  - `unittest` проходит, `pytest` отсутствует.
  - runtime-память ссылается на несуществующие vacancy folders.
  - дизайн и код расходятся по числу workflow, Excel-схеме и git side effects.

### M2. Workflow Contracts And Safety Alignment

- Status: `planned`
- Goal:
  - привести текущие workflow, memory contracts и mutation/publication behavior к единой, проверяемой модели;
  - убрать или явно ратифицировать скрытые side effects.
- Deliverables:
  - workstream plan: `2026-04-21-workflow-contract-alignment-and-safety.md`;
  - contract matrix current vs intended behavior;
  - приоритизированный backlog по core-логике и safety.
- Acceptance criteria:
  - для `bootstrap`, `ingest-vacancy`, `analyze-vacancy`, runtime memory, Excel и git-публикации есть единое описание current state и target state;
  - зафиксированы решения по auto-commit/auto-push, stale runtime и canonical validation path.
- Validation commands:
  - `python run_agent.py --root ../.. list-workflows`
  - `python run_agent.py --root ../.. show-memory`
  - `python -m unittest discover -s tests`
- Notes / discoveries:
  - текущее поведение уже достаточно богато, чтобы сначала стабилизировать контракт, а потом расширять каталог workflow.

### M3. Root Artifact And Output Pipeline Normalization

- Status: `planned`
- Goal:
  - нормализовать root data/template/output layer и определить, какие артефакты являются входами, шаблонами, кэшем, архивом или manual-only обходным путем.
- Deliverables:
  - workstream plan: `2026-04-21-root-artifacts-and-output-normalization.md`;
  - source-of-truth map для `CV/`, `profile/`, `knowledge/`, `adoptions/`, `templates/`, `Employers/`, `archive/`, `promts/`;
  - backlog по migration path для output pipeline.
- Acceptance criteria:
  - для каждого значимого root-каталога определены producer, consumer и статус;
  - зафиксированы gaps вроде отсутствующего `profile/contact-regions.yml`, пустых knowledge/adoptions stores и manual PDF generation.
- Validation commands:
  - `Get-ChildItem CV,templates,profile,knowledge,adoptions,Employers,archive -Recurse -File`
  - `Test-Path "C:\Users\avramko\OneDrive\Documents\Career\profile\contact-regions.yml"`
  - `Get-ChildItem promts -File`
- Notes / discoveries:
  - legacy prompt corpus и manual employer-specific outputs содержат много бизнес-логики, но пока не встроены в инструмент как явные контракты.

### M4. Ordered Implementation Queue

- Status: `planned`
- Goal:
  - после прояснения контрактов собрать короткую, исполнимую очередь следующих инженерных изменений без повторной разведки.
- Deliverables:
  - упорядоченный implementation backlog на основе M2 и M3;
  - обновленный `Current state` в master plan;
  - список blockers и решений, требующих подтверждения пользователя.
- Acceptance criteria:
  - порядок дальнейшей реализации понятен и опирается на зафиксированные зависимости;
  - backlog не смешивает safety fixes, contract alignment и feature expansion без необходимости.
- Validation commands:
  - `Get-Content -Raw plans\2026-04-21-repository-reconstruction-and-backlog.md`
  - `Get-Content -Raw plans\2026-04-21-workflow-contract-alignment-and-safety.md`
  - `Get-Content -Raw plans\2026-04-21-root-artifacts-and-output-normalization.md`
- Notes / discoveries:
  - этот milestone нельзя качественно закрыть, пока не будут пройдены M2 и M3.

## Decision log

- `2026-04-21 16:43` — Главный план ведется в `tooling/application-agent/plans/`, потому что основная логика изменений и все инженерные решения относятся к submodule-коду и его контрактам. — Это соответствует `AGENTS.md` в корне и в submodule. — Все корневые артефакты дальше рассматриваются как external touchpoints.
- `2026-04-21 16:43` — Работа разбита на два самостоятельных workstreams: `workflow-contract-alignment-and-safety` и `root-artifacts-and-output-normalization`. — Найденные проблемы естественно группируются в эти два потока без искусственного дробления. — Следующие инженерные сессии можно вести независимо по одному из потоков.
- `2026-04-21 16:43` — Исторические design docs и prompt corpus признаны input-материалом для реконструкции, но не источником истины о текущем поведении. — Реализация и тесты уже ушли дальше части старых документов и одновременно расходятся с ними. — В планах нужно явно разделять current state и target intent.

## Progress log

- `2026-04-21 16:43` — Проведена первичная разведка корня, `tooling/`, submodule-кода, тестов, шаблонов, runtime-памяти, vacancy-артефактов, legacy prompt-материалов и manual output traces. — `python -m unittest discover -s tests` -> `36 tests, OK`; `pytest` отсутствует; runtime memory указывает на несуществующие vacancy folders. — Status: `in_progress`.
- `2026-04-21 16:43` — Создан master plan и выделены самостоятельные workstreams для дальнейшей работы без повторного обследования. — Валидация опирается на файловую структуру, `unittest` и документированные команды CLI. — Status: `in_progress`.

## Current state

- Current milestone: `M2`
- Current status: `planned`
- Next step: `Составить contract matrix current-vs-target для bootstrap/ingest/analyze, runtime memory, Excel и git side effects на основе плана 2026-04-21-workflow-contract-alignment-and-safety.md.`
- Active blockers:
  - Не принято решение, допустим ли auto-commit/auto-push в `ingest-vacancy`.
  - Не определен канонический Excel-контракт: A-J из старой спецификации или A-K из текущего кода и mapping doc.
  - Не определено правило синхронизации runtime memory с удаленными/архивированными vacancy-артефактами.
- Open questions:
  - Считать ли `plans/resume-agent-spec.md` исторической целевой моделью или базой для обязательного contract alignment?
  - Нужно ли сохранять vacancy-local `adoptions.md` как самостоятельный артефакт после перехода к `adoptions/inbox/<vacancy_id>.md`?
  - Какие legacy prompt-документы должны быть переведены в код/тесты, а какие можно оставить reference-only?
  - Должен ли output pipeline для PDF/LinkedIn жить внутри public agent или оставаться partially manual в корне?

## Completion summary

Заполняется после завершения master-плана. Пока задача находится в фазе реконструкции репозитория и нормализации backlog.
