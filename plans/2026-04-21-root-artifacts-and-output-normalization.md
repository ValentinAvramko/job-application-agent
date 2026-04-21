# Root Artifacts And Output Normalization

- Title: `Root artifacts and output normalization`
- Slug: `2026-04-21-root-artifacts-and-output-normalization`
- Owner: `Codex`
- Created: `2026-04-21`
- Last updated: `2026-04-21 19:51`
- Overall status: `in_progress`

## Objective

Превратить root workspace из смеси active, partial, historical и manual-only артефактов в понятный data/template/output layer с явными source-of-truth правилами и одновременно:

- перенести содержательные решения из superseded root planning artifacts в актуальные plan files;
- убрать конкурирующие источники истины по структуре workspace и workflow roadmap;
- подготовить удаление старых root plan/spec files после миграции.

## Background and context

Разведка root показала несколько слоев артефактов:

- активные источники фактов и рабочих материалов: `CV/`, `vacancies/`, `response-monitoring.xlsx`;
- partially initialized long-lived stores: `knowledge/`, `profile/`, `adoptions/`;
- reusable templates: `templates/`;
- legacy prompt/doc corpus: `promts/`, `responses.md`, `adoptions_00.md`;
- manual output traces и employer-specific artifacts: `Employers/`, `archive/`;
- superseded planning artifacts в root `plans/`.

Подтвержденные факты:

- `CV/MASTER.md` и ролевые CV остаются основным фактологическим слоем о кандидате;
- `profile/contact-regions.yml` ожидается целевой моделью, но сейчас отсутствует;
- `knowledge/roles/` и `adoptions/accepted|inbox` в основном пусты;
- `vacancies/` содержит актуальные и исторически неполные vacancy-local artifacts;
- `Employers/TaxDome/render_resume_pdf.py` и файлы в `archive/` фиксируют manual-only export traces;
- содержимое старых root docs `plans/resume-agent-spec.md` и `plans/repository-topology.md` перенесено в активные plans; сами файлы больше не должны существовать как отдельные источники истины.

Мигрируемые решения из superseded root docs:

- public/private split: код и implementation plans живут в `tooling/application-agent`, root хранит данные, шаблоны и outputs;
- target workflow catalog: после текущего стека предполагаются `prepare-screening`, `rebuild-master`, `rebuild-role-resume`, `build-linkedin`, `export-resume-pdf`;
- source-of-truth rules: `CV/MASTER.md` главный facts source, role resumes производны, contact/profile overlays вынесены из resume text;
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

- `CV/MASTER.md` остается главным facts source для candidate profile;
- role CV представляют производные ролевые представления, а не независимые источники истины;
- missing/empty files в `knowledge/`, `profile/`, `adoptions/` означают незавершенный data layer, а не intentional minimal final state;
- superseded root planning artifacts можно удалить после того, как их целевые решения будут явно встроены в активные plans.

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
- `C:\Users\avramko\OneDrive\Documents\Career\plans\` — чтение / миграция / удаление — superseded root planning artifacts.

## Milestones

### M1. Root Artifact Inventory And Migration Map

- Status: `in_progress`
- Goal:
  - собрать inventory matrix, где для каждого root-слоя указаны назначение, producer, consumer, status и проблемы;
  - составить migration map для superseded root planning artifacts.
- Deliverables:
  - inventory matrix по `CV/`, `profile/`, `knowledge/`, `adoptions/`, `vacancies/`, `templates/`, `promts/`, `Employers/`, `archive/`, `plans/`;
  - классификация артефактов: canonical / generated / template / historical / manual-only / stale;
  - mapping `old artifact -> new active plan/doc destination`.
- Acceptance criteria:
  - для каждого крупного каталога понятна его роль и связь с submodule;
  - отдельно отмечены пустые, отсутствующие, дублирующиеся и legacy-only области;
  - для `plans/resume-agent-spec.md` и `plans/repository-topology.md` определено, куда именно мигрирует их содержимое.
- Validation commands:
  - `Get-ChildItem CV,templates,profile,knowledge,adoptions,Employers,archive -Recurse -File`
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\plans -File`
  - `Test-Path "C:\Users\avramko\OneDrive\Documents\Career\profile\contact-regions.yml"`
  - `Get-ChildItem vacancies -Directory`
- Notes / discoveries:
  - `profile/contact-regions.yml` отсутствует.
  - `knowledge/roles` и `adoptions/accepted|inbox` пока не выполняют заявленную роль постоянной базы.

### M2. Canonical Root Contract Decisions

- Status: `planned`
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
  - migrated target intent должен жить в active plans, а не в отдельном superseded root plan corpus.

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
  - обновленные active plans, в которые встроены topology, workflow roadmap и source-of-truth rules из старых root docs.
- Acceptance criteria:
  - для `promts/*.md`, `responses.md`, `adoptions_00.md` определен дальнейший статус;
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

## Progress log

- `2026-04-21 16:43` — Подтверждено, что `CV/` насыщен версиями, а `profile/`, `knowledge/`, `adoptions/` остаются в основном скелетными. — Проверка файловой структуры выявила отсутствие `profile/contact-regions.yml` и пустые long-lived stores. — Status: `planned`.
- `2026-04-21 16:43` — Найдены manual output traces в `Employers/` и `archive/`, а также крупный legacy prompt corpus в `promts/`, `responses.md`, `adoptions_00.md`. — Это указывает на незавершенную миграцию от prompt-first/manual workflows к tool-driven pipeline. — Status: `planned`.
- `2026-04-21 19:51` — План переприоритизирован в следующий активный этап master plan и расширен migration/removal задачей для superseded root planning artifacts. — Следующий фокус: inventory + migration map, а не feature work. — Status: `in_progress`.
- `2026-04-21 19:51` — Содержательные решения superseded root planning artifacts перенесены в активные plans, а сами root files удалены. — Дальнейший focus смещается с migration/removal на оставшиеся root contracts и producer/consumer inventory. — Status: `in_progress`.

## Current state

- Current milestone: `M1`
- Current status: `in_progress`
- Next step: `Собрать inventory root-слоев без удаленных superseded plan files и зафиксировать producer/consumer map для CV, profile, knowledge, adoptions, vacancies, templates, Employers, archive и legacy corpus.`
- Active blockers:
  - Не определено, какой root-слой считается каноническим для контактов, постоянных сигналов и adoptions.
  - Не определен target home для PDF/LinkedIn/export pipeline.
  - Еще не закреплены canonical root contracts после удаления superseded plan files.
- Open questions:
  - Нужно ли сохранять vacancy-local `adoptions.md` после введения корневого inbox workflow?
  - Должно ли `CV/MASTER.md` оставаться единственным facts source, если часть нормализации будет переноситься в `knowledge/` и memory stores?
  - Какие части old root docs должны попасть в master plan, а какие в root normalization plan или future workflow plans?

## Completion summary

Заполняется после завершения workstream-а по нормализации root artifacts, migration prompt/doc corpus и удалению superseded root planning artifacts.
