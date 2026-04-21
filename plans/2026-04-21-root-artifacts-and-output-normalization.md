# Root Artifacts And Output Normalization

- Title: `Root artifacts and output normalization`
- Slug: `2026-04-21-root-artifacts-and-output-normalization`
- Owner: `Codex`
- Created: `2026-04-21`
- Last updated: `2026-04-21 20:35`
- Overall status: `in_progress`

## Objective

Превратить root workspace из смеси active, partial, historical и manual-only артефактов в понятный data/template/output layer с явными source-of-truth правилами и одновременно:

- перенести содержательные решения из superseded root planning artifacts в актуальные plan files;
- убрать конкурирующие источники истины по структуре workspace и workflow roadmap;
- подготовить удаление старых root plan/spec files после миграции.

## Background and context

Разведка root показала несколько слоёв артефактов:

- активные источники фактов и рабочих материалов: `CV/`, `vacancies/`, `response-monitoring.xlsx`, `agent_memory/`;
- partially initialized long-lived stores: `knowledge/`, `profile/`, `adoptions/`;
- reusable templates: `templates/`;
- legacy prompt/doc corpus: `promts/`, `responses.md`, `adoptions_00.md`;
- manual output traces и employer-specific artifacts: `Employers/`, `archive/`;
- superseded planning artifacts в удалённом root `plans/`.

Подтверждённые факты:

- `CV/MASTER.md` и ролевые CV остаются основным resume-слоем о кандидате;
- `profile/contact-regions.yml` ожидается целевой моделью, но сейчас отсутствует;
- `knowledge/roles` и `adoptions/accepted|inbox` почти пусты и не участвуют в runtime;
- `vacancies/` содержит реальные workflow artifacts и сегодня является главным рабочим output layer;
- `Employers/TaxDome/render_resume_pdf.py` и файлы в `archive/` фиксируют manual-only export traces;
- содержимое старых root docs `plans/resume-agent-spec.md` и `plans/repository-topology.md` уже перенесено в active plans; сами root files удалены и больше не должны существовать как отдельные источники истины.

Мигрируемые решения из superseded root docs:

- public/private split: код и implementation plans живут в `tooling/application-agent`, root хранит данные, шаблоны и outputs;
- target workflow catalog: после текущего стека предполагаются `prepare-screening`, `rebuild-master`, `rebuild-role-resume`, `build-linkedin`, `export-resume-pdf`;
- source-of-truth rules: `CV/MASTER.md` — главный facts source, role resumes — производные, contact/profile overlays должны жить отдельно от resume text;
- целевая root topology: `CV/`, `vacancies/`, `knowledge/`, `adoptions/`, `profile/`, `agent_memory/`, `templates/`, `Employers/`, `archive/`.

## Scope

### In scope

- source-of-truth map для значимых root directories и file families;
- нормализация ролей каталогов `CV/`, `profile/`, `knowledge/`, `adoptions/`, `vacancies/`, `templates/`, `Employers/`, `archive/`, `promts/`;
- определение target path для output pipeline: resume text artifacts, LinkedIn outputs, screening prep, PDF export и employer-specific artifacts;
- migration superseded root planning artifacts в актуальные plan files;
- удаление старых root plan/spec files после переноса содержательных решений.

### Out of scope

- изменение core-кода workflow без отдельного workstream-плана;
- генерация новых PDF/DOCX/LinkedIn материалов;
- редактирование фактического содержимого resume/profile data;
- удаление исторических output artifacts без явной retention policy.

## Assumptions

- `CV/MASTER.md` остаётся главным facts source для candidate profile;
- role CV представляют производные ролевые представления, а не независимые источники истины;
- missing/empty files в `knowledge/`, `profile/`, `adoptions/` означают незавершённый data layer, а не intentional final state;
- superseded root planning artifacts можно удалять после того, как их целевые решения явно встроены в active plans.

## Risks and unknowns

- часть naming/schema conventions уже расходится между templates, кодом и manual artifacts;
- неясно, какой процент legacy prompt/doc corpus должен стать tests/specs, а какой можно оставить historical-only;
- при migration старых planning artifacts легко потерять полезный target intent по topology и workflow roadmap;
- неясно, где в итоге должен жить окончательный export pipeline: в public agent, private root или в hybrid scheme.

## External touchpoints

- `C:\Users\avramko\OneDrive\Documents\Career\CV\` — чтение / проверка — master и role resumes, версии и facts source;
- `C:\Users\avramko\OneDrive\Documents\Career\profile\` — чтение / возможное обновление / проверка — contact regions и metadata;
- `C:\Users\avramko\OneDrive\Documents\Career\knowledge\` — чтение / возможное обновление / проверка — role/company signals;
- `C:\Users\avramko\OneDrive\Documents\Career\adoptions\` — чтение / возможное обновление / проверка — inbox, accepted, questions;
- `C:\Users\avramko\OneDrive\Documents\Career\vacancies\` — чтение / проверка — vacancy-local artifacts;
- `C:\Users\avramko\OneDrive\Documents\Career\templates\` — чтение / возможное обновление / проверка — reusable templates и schema hints;
- `C:\Users\avramko\OneDrive\Documents\Career\promts\`, `responses.md`, `adoptions_00.md` — чтение / проверка — legacy business logic corpus;
- `C:\Users\avramko\OneDrive\Documents\Career\Employers\` и `archive\` — чтение / проверка — manual export traces;
- `C:\Users\avramko\OneDrive\Documents\Career\plans\` — чтение / migration / removal — superseded root planning artifacts; каталог уже отсутствует и не должен возвращаться.

## M1 Inventory Matrix

| Root artifact | Representative contents | Producer | Consumer | Classification | Current status / issue |
| --- | --- | --- | --- | --- | --- |
| `CV/` | `MASTER.md`, `CIO.md`, `CTO.md`, `HoE.md`, `HoD.md`, `EM.md`, `versions/`, `OPTIONAL_RULES.yml` | Manual profile maintenance and historical exports | `analyze-vacancy`, `prepare-screening`, manual resume editing | `MASTER.md` is canonical; role resumes are derived; `versions/` is historical; `OPTIONAL_RULES.yml` is legacy/manual-only for now | Active and heavily used, but current code does not consume `OPTIONAL_RULES.yml`; active and historical resume artifacts live side by side |
| `profile/` | `README.md`, missing `contact-regions.yml`, template in `templates/profile/` | `bootstrap` creates the directory; expected human-maintained metadata later | Planned contact/profile-aware workflows only | Intended canonical metadata store | Structurally declared but functionally missing: the target file does not exist and no current workflow reads it |
| `knowledge/` | `README.md`, `roles/README.md`, empty `company_signals/` | `bootstrap` creates the store; future normalization/adoption workflow should populate it | Future resume rebuild and signal accumulation workflows | Intended canonical long-lived signal store | Mostly skeletal; no current runtime writer or reader |
| `adoptions/` | `README.md`, empty `inbox/`, empty `accepted/`, `questions/open.md` | `bootstrap` creates the store; future review workflow should write to it | Future resume rebuild/adoption workflows | Intended canonical review store | Conflicts with the current reality: live workflow writes `vacancies/<id>/adoptions.md`, while root inbox/accepted remain unused |
| `vacancies/` | per-vacancy `meta.yml`, `source.md`, `analysis.md`, `adoptions.md` | `ingest-vacancy`, `analyze-vacancy`, `prepare-screening` | Runtime memory, operator review, future downstream workflows | Active generated workspace per vacancy | This is the real active artifact family today; it mixes local record, analysis output and vacancy-local adoptions |
| `response-monitoring.xlsx` | ingest ledger workbook, schema map in `templates/excel/response-monitoring-mapping.md` | `ingest-vacancy` integration plus manual spreadsheet edits | Operator tracking and reconciliation | Active canonical tracking ledger | Real business contract exists, but part of the schema still lives in spreadsheet/template documentation instead of a dedicated root contract file |
| `templates/` | profile, knowledge, adoptions, interview and Excel templates | Manual design/spec work | Humans and plan documents; current runtime does not read these files directly | Template/spec layer | Useful reference corpus, but not wired into bootstrap or workflow rendering, so drift risk is high |
| `agent_memory/` | runtime memory, schemas, workflow contracts | `bootstrap`, memory store, workflow execution | CLI workflows and operator diagnostics | Active private runtime/state layer | Canonical for runtime state, but may keep stale vacancy references until explicit reconciliation |
| `promts/` + `responses.md` + `adoptions_00.md` | legacy prompts and large historical corpora | Legacy manual/prompt-first workflow | Human reference only for now | Legacy / stale but potentially mineable corpus | Still valuable as raw input, but now competes with active plans if treated as current spec |
| `Employers/` | employer-specific resumes, notes, `TaxDome/render_resume_pdf.py`, preview PNGs | Manual one-off tailoring/export work | Human/operator only | Manual-only / historical examples | Contains unsupported manual pipeline fragments outside current tool contract |
| `archive/` | historical PDF/DOCX exports | Manual export flow | Human archive only | Historical output store | No explicit retention/status convention yet |
| historical root `plans/` | removed root `plans/` directory and superseded spec files | Legacy planning process | None after migration | Stale / removed | Content was migrated; the directory is absent by design and must not reappear as a source of truth |

## M1 Migration Map For Superseded Planning Artifacts

| Old artifact | Current status | Active destination after migration | Notes |
| --- | --- | --- | --- |
| `C:\Users\avramko\OneDrive\Documents\Career\plans\resume-agent-spec.md` | removed | `plans/2026-04-21-repository-reconstruction-and-backlog.md`, `plans/2026-04-21-root-artifacts-and-output-normalization.md` | Public/private split, workflow catalog, source-of-truth rules and cleanup ordering were redistributed into active plans |
| `C:\Users\avramko\OneDrive\Documents\Career\plans\repository-topology.md` | removed | `AGENTS.MD`, `plans/2026-04-21-repository-reconstruction-and-backlog.md`, `plans/2026-04-21-root-artifacts-and-output-normalization.md` | Root topology and routing rules now live in root instructions plus active submodule plans |
| `C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\plans\ingest-refactor-plan.md` | removed | `plans/2026-04-21-workflow-contract-alignment-and-safety.md`, `README.md` | Workflow/safety decisions were retained in the dedicated safety plan and in the repository README architecture notes |

## Milestones

### M1. Root Artifact Inventory And Migration Map

- Status: `done`
- Goal:
  - собрать inventory matrix, где для каждого root-слоя указаны назначение, producer, consumer, status и проблемы;
  - составить migration map для superseded root planning artifacts.
- Deliverables:
  - inventory matrix по `CV/`, `profile/`, `knowledge/`, `adoptions/`, `vacancies/`, `templates/`, `promts/`, `Employers/`, `archive/`, historical root `plans/`, `response-monitoring.xlsx`, `agent_memory/`;
  - классификация артефактов: canonical / generated / template / historical / manual-only / stale;
  - mapping `old artifact -> new active plan/doc destination`.
- Acceptance criteria:
  - для каждого крупного каталога понятна его роль и связь с submodule;
  - отдельно отмечены пустые, отсутствующие, дублирующиеся и legacy-only области;
  - для `plans/resume-agent-spec.md` и `plans/repository-topology.md` определено, куда именно мигрирует их содержимое.
- Validation commands:
  - `Get-ChildItem CV,templates,profile,knowledge,adoptions,Employers,archive -Recurse -File`
  - `Test-Path "C:\Users\avramko\OneDrive\Documents\Career\plans"`
  - `Test-Path "C:\Users\avramko\OneDrive\Documents\Career\profile\contact-regions.yml"`
  - `Get-ChildItem vacancies -Directory`
- Notes / discoveries:
  - `profile/contact-regions.yml` отсутствует.
  - `knowledge/roles` и `adoptions/accepted|inbox` пока не выполняют заявленную роль постоянной базы.
  - Current code активно читает/пишет только `CV/`, `vacancies/`, `agent_memory/` и `response-monitoring.xlsx`; `profile/`, `knowledge/`, `adoptions/` остаются target stores, а не active workflow stores.
  - Vacancy-local `vacancies/<id>/adoptions.md` — единственное adoptions family, которое сейчас генерирует инструмент.
  - Historical root `plans/` уже удалён; дальнейшая работа должна решать контракты без восстановления root plan/spec corpus.

### M2. Canonical Root Contract Decisions

- Status: `in_progress`
- Goal:
  - определить, какие root-артефакты являются источником истины, какие производными, а какие историческими;
  - встроить migrated target intent из старых root docs в новую структуру планов.
- Deliverables:
  - canonical contract map для `CV`, `profile`, `knowledge`, `adoptions`, `vacancies`, Excel и templates;
  - решения по naming, location и schema drift;
  - явное распределение migrated intent из старых root docs по актуальным plan files.
- Acceptance criteria:
  - для каждого долгоживущего root store есть owner, expected shape и update path;
  - противоречия вида `vacancy-local adoptions.md` vs `adoptions/inbox/<vacancy_id>.md`, `promts/` vs skill-first docs, missing `contact-regions.yml` либо сняты, либо явно задокументированы;
  - target topology и source-of-truth rules из старых root docs больше не требуют отдельных файлов-источников.
- Validation commands:
  - `Get-Content -Raw C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\plans\2026-04-21-repository-reconstruction-and-backlog.md`
  - `Get-Content -Raw C:\Users\avramko\OneDrive\Documents\Career\templates\excel\response-monitoring-mapping.md`
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\adoptions -Recurse -File`
- Notes / discoveries:
  - migrated target intent должен жить в active plans, а не в отдельном superseded root plan corpus;
  - M1 показал, что root contract decisions надо принимать относительно реального runtime graph, а не относительно только README/шаблонов.

### M3. Output Pipeline Migration Path

- Status: `planned`
- Goal:
  - определить, как manual employer-specific и historical outputs переводятся в поддерживаемый pipeline для resume export, LinkedIn, screening prep и related artifacts.
- Deliverables:
  - migration path для ручных PDF/DOCX/export scripts;
  - target placement rules для будущих output artifacts;
  - решение, какие employer-specific traces сохраняются как examples/tests/reference.
- Acceptance criteria:
  - manual renderer и архивные outputs не остаются без статуса;
  - для каждого важного output family понятно, где он должен жить и чем генерироваться;
  - определены границы между reusable pipeline и one-off artifacts.
- Validation commands:
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\Employers -Recurse -File`
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\archive -File`
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\CV\versions -File`
- Notes / discoveries:
  - `Employers/TaxDome/render_resume_pdf.py` — явный пример manual-only export path.

### M4. Legacy Prompt And Superseded Plan Distillation

- Status: `planned`
- Goal:
  - превратить накопленные prompt/doc/plan materials в управляемый knowledge/spec layer;
  - удалить superseded plan artifacts после переноса их содержательных решений.
- Deliverables:
  - список prompt/doc artifacts, которые надо перенести в планы, tests, templates или workflow specs;
  - список artifacts, которые можно оставить historical-only;
  - deletion list для superseded root planning artifacts после migration;
  - обновлённые active plans, в которые встроены topology, workflow roadmap и source-of-truth rules из старых root docs.
- Acceptance criteria:
  - для `promts/*.md`, `responses.md`, `adoptions_00.md` определён дальнейший статус;
  - содержимое `plans/resume-agent-spec.md` и `plans/repository-topology.md` мигрировано в актуальные plan files;
  - superseded root planning artifacts удалены из репозитория.
- Validation commands:
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\promts -File`
  - `Test-Path "C:\Users\avramko\OneDrive\Documents\Career\plans\resume-agent-spec.md"`
  - `Test-Path "C:\Users\avramko\OneDrive\Documents\Career\plans\repository-topology.md"`
- Notes / discoveries:
  - задача этого milestone не в архивной пометке, а в полном переносе содержания и последующем удалении superseded files.

## Decision log

- `2026-04-21 16:43` — Root data/template/output layer выделен в отдельный workstream. — Найденные проблемы относятся к source-of-truth и artifact ownership, а не только к логике workflow. — Это уменьшает риск смешать cleanup и feature implementation.
- `2026-04-21 16:43` — Legacy prompt corpus рассматривается как valuable input, но не как финальная форма хранения бизнес-правил. — Он уже пересекается со спецификациями и частично дублирует их. — Нужна управляемая distillation.
- `2026-04-21 19:51` — Superseded root plan/spec artifacts должны быть не просто помечены, а полностью мигрированы в актуальные plans и затем удалены. — Это убирает параллельные источники истины в root `plans/`. — Migration/removal встроены в milestones M1-M4.
- `2026-04-21 20:35` — `vacancies/<id>/adoptions.md` зафиксирован как текущий generated vacancy-local artifact, а не как long-lived canonical adoptions store. — Root `adoptions/` существует как целевая структура, но ещё не подключён к runtime. — M2 должен решить, остаётся ли vacancy-local слой, мигрируется ли он в inbox или живут оба слоя с разными ролями.
- `2026-04-21 20:35` — Текущий runtime root-контракт фактически опирается на `CV/`, `vacancies/`, `agent_memory/` и `response-monitoring.xlsx`; `templates/` и legacy prompt corpus пока не являются runtime inputs. — Это подтверждено поиском по коду и фактической файловой структурой. — Дальнейшие решения нужно принимать относительно реального producer/consumer graph.

## Progress log

- `2026-04-21 16:43` — Подтверждено, что `CV/` насыщен версиями, а `profile/`, `knowledge/`, `adoptions/` остаются в основном скелетными. — Проверка файловой структуры выявила отсутствие `profile/contact-regions.yml` и пустые long-lived stores. — Status: `planned`.
- `2026-04-21 16:43` — Найдены manual output traces в `Employers/` и `archive/`, а также крупный legacy prompt corpus в `promts/`, `responses.md`, `adoptions_00.md`. — Это указывает на незавершённую миграцию от prompt-first/manual workflows к tool-driven pipeline. — Status: `planned`.
- `2026-04-21 19:51` — План переприоритизирован в следующий активный этап master plan и расширен migration/removal задачей для superseded root planning artifacts. — Следующий фокус: inventory + migration map, а не feature work. — Status: `in_progress`.
- `2026-04-21 19:51` — Содержательные решения superseded root planning artifacts перенесены в active plans, а сами root files удалены. — Дальнейший focus смещается с migration/removal на оставшиеся root contracts и producer/consumer inventory. — Status: `in_progress`.
- `2026-04-21 20:35` — В план добавлены M1 inventory matrix и migration map по реальным root artifacts, включая `response-monitoring.xlsx`, `agent_memory/`, legacy corpus и уже удалённый root `plans/`. — Проверка кода показала, что runtime сегодня реально работает через `CV/`, `vacancies/`, `agent_memory/` и Excel, а `profile/`, `knowledge/`, `adoptions/` пока остаются целевыми stores; validation confirmed `Test-Path root/plans = False`, `Test-Path profile/contact-regions.yml = False`, `vacancies/` currently contains 3 directories. — Status: `done`.

## Current state

- Current milestone: `M2`
- Current status: `in_progress`
- Next step: `Зафиксировать canonical contract для CV, profile, knowledge, adoptions, vacancies, response-monitoring.xlsx и legacy corpus, а также разрешить конфликт между vacancy-local adoptions.md, root inbox-подходом и отсутствующим contact-regions.yml.`
- Active blockers:
  - Не определён canonical root-layer для контактов, долгоживущих сигналов и adoptions после инвентаризации фактических producer/consumer связей.
  - Не решено, должен ли `vacancies/<id>/adoptions.md` остаться generated sidecar-artifact либо мигрировать в `adoptions/inbox/<vacancy_id>.md`.
  - Не определён target home для PDF/LinkedIn/export pipeline и employer-specific traces.
- Open questions:
  - Должен ли `CV/MASTER.md` оставаться единственным facts source, если часть нормализации переедет в `knowledge/` и `profile/`?
  - Являются ли шаблоны в `templates/` runtime-contract inputs или это только human-facing reference/spec layer?
  - Какой статус должны получить `promts/`, `responses.md` и `adoptions_00.md`: future test/spec source, historical-only corpus или промежуточный reference layer?

## Completion summary

Заполняется после завершения workstream-а по нормализации root artifacts, migration prompt/doc corpus и удалению superseded root planning artifacts.
