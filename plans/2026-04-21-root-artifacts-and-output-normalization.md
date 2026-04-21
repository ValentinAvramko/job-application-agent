# Root Artifacts And Output Normalization

- Title: `Root artifacts and output normalization`
- Slug: `2026-04-21-root-artifacts-and-output-normalization`
- Owner: `Codex`
- Created: `2026-04-21`
- Last updated: `2026-04-21 16:43`
- Overall status: `planned`

## Objective

Превратить корневой private workspace из набора частично оформленных и частично исторических артефактов в понятный data/template/output layer с явными source-of-truth правилами, так чтобы инструмент мог надежно опираться на `CV/`, `profile/`, `knowledge/`, `adoptions/`, `vacancies/`, `templates/`, `Employers/`, `archive/` и legacy prompt corpus без скрытых допущений и ручных обходных путей.

## Background and context

Разведка корня показала несколько разных типов артефактов:

- активные источники фактов и рабочих материалов: `CV/`, `vacancies/`, `response-monitoring.xlsx`;
- заготовленные, но слабо наполненные хранилища: `knowledge/`, `profile/`, `adoptions/`;
- template layer: `templates/`;
- legacy prompt/spec layer: `promts/`, `responses.md`, `adoptions_00.md`, корневой `plans/`;
- manual output traces и employer-specific artifacts: `Employers/`, `archive/`.

Подтвержденные факты:

- `CV/` содержит актуальные ролевые резюме и историю версий;
- `profile/contact-regions.yml` отсутствует, хотя README и template ожидают его существование;
- `knowledge/roles/` и `adoptions/accepted|inbox` практически пусты;
- `vacancies/` сейчас содержит только несколько актуальных папок, но runtime history хранит ссылки на уже отсутствующие записи;
- в `Employers/TaxDome/` есть ручной PDF renderer и employer-specific resume artifacts вне submodule;
- `archive/` содержит старые PDF/DOCX outputs с разными naming conventions;
- `promts/` содержит большие prompt-файлы для master resume, role resumes, vacancy analysis и LinkedIn, а directory name написан как `promts`, не `prompts`.

Отдельный важный вывод: текущий инструмент почти не потребляет root templates и legacy prompt corpus напрямую. Значительная часть бизнес-логики пока живет либо в исторических prompt-файлах, либо в ручных output-артефактах, либо уже переписана в код частично и не всегда синхронно с root-документацией.

## Scope

### In scope

- source-of-truth map для всех значимых root directories и файловых семейств;
- нормализация ролей каталогов `CV/`, `profile/`, `knowledge/`, `adoptions/`, `vacancies/`, `templates/`, `Employers/`, `archive/`, `promts/`;
- определение target path для output pipeline: master/role resumes, LinkedIn outputs, screening prep, PDF export и employer-specific artifacts;
- решение, какие legacy docs/prompts надо мигрировать в спеку/тесты/шаблоны, а какие оставить историческими reference.

### Out of scope

- редактирование содержимого реальных резюме или контактных данных кандидата;
- генерация новых PDF/DOCX/LinkedIn материалов в рамках этого плана;
- переписывание core-кода workflow без отдельного workstream-плана;
- очистка архива без явного решения о retention policy.

## Assumptions

- `CV/MASTER.md` и ролевые CV являются основными фактологическими источниками для candidate profile, даже если future parsing/normalization будет меняться;
- пустые или отсутствующие файлы в `knowledge/`, `profile/`, `adoptions/` означают незавершенный слой данных, а не готовую intentional minimal state;
- `responses.md`, `adoptions_00.md` и `promts/*.md` содержат ценную бизнес-логику, но не должны оставаться единственным местом ее хранения;
- manual employer-specific outputs важны как evidence desired behavior, даже если финальная автоматизация будет устроена иначе.

## Risks and unknowns

- корневые артефакты содержат private data, поэтому любое переупорядочивание должно учитывать приватность и границы public/private split;
- часть naming/schema conventions уже расходится между шаблонами, кодом и ручными артефактами;
- возможны несколько конкурирующих источников истины для одного и того же семейства output-артефактов;
- неясно, какой процент legacy prompt corpus нужно конвертировать в formal specs/tests, а какой можно архивировать;
- неясно, где должен жить окончательный PDF/export pipeline: в public agent, в private root или в гибридной схеме.

## External touchpoints

- `C:\Users\avramko\OneDrive\Documents\Career\CV\` — чтение / проверка / возможное обновление — master и ролевые резюме, история версий, optional rules.
- `C:\Users\avramko\OneDrive\Documents\Career\profile\` — чтение / возможное обновление / проверка — контактные регионы и связанная metadata.
- `C:\Users\avramko\OneDrive\Documents\Career\knowledge\` — чтение / возможное обновление / проверка — нормализованные role/company signals.
- `C:\Users\avramko\OneDrive\Documents\Career\adoptions\` — чтение / возможное обновление / проверка — inbox, accepted, questions.
- `C:\Users\avramko\OneDrive\Documents\Career\vacancies\` — чтение / проверка — фактические vacancy artifacts и local adoptions.
- `C:\Users\avramko\OneDrive\Documents\Career\templates\` — чтение / возможное обновление / проверка — reusable templates и schema hints.
- `C:\Users\avramko\OneDrive\Documents\Career\promts\`, `responses.md`, `adoptions_00.md` — чтение / проверка — legacy business logic corpus.
- `C:\Users\avramko\OneDrive\Documents\Career\Employers\` и `archive\` — чтение / проверка — manual export traces и employer-specific outputs.
- `C:\Users\avramko\OneDrive\Documents\Career\plans\` — чтение / проверка — исторические design docs и target intent.

## Milestones

### M1. Root Artifact Inventory And Producer/Consumer Map

- Status: `planned`
- Goal:
  - собрать таблицу, где для каждого root-слоя указаны назначение, producer, consumer, status и проблемы.
- Deliverables:
  - inventory matrix по `CV/`, `profile/`, `knowledge/`, `adoptions/`, `vacancies/`, `templates/`, `promts/`, `Employers/`, `archive/`;
  - классификация артефактов: canonical / generated / template / historical / manual-only / stale.
- Acceptance criteria:
  - для каждого крупного каталога понятны его роль и связь с submodule;
  - отдельно отмечены пустые, отсутствующие, дублирующиеся и legacy-only области.
- Validation commands:
  - `Get-ChildItem CV,templates,profile,knowledge,adoptions,Employers,archive -Recurse -File`
  - `Test-Path "C:\Users\avramko\OneDrive\Documents\Career\profile\contact-regions.yml"`
  - `Get-ChildItem vacancies -Directory`
- Notes / discoveries:
  - `profile/contact-regions.yml` отсутствует.
  - `knowledge/roles` и `adoptions/accepted|inbox` пока не выполняют заявленную роль постоянной базы.

### M2. Canonical Root Contract Decisions

- Status: `planned`
- Goal:
  - определить, какие root-артефакты являются источником истины, какие являются производными, а какие остаются историческими reference-only материалами.
- Deliverables:
  - canonical contract map для `CV`, `profile`, `knowledge`, `adoptions`, `vacancies`, Excel и templates;
  - решения по naming, location и schema drift;
  - список материалов, подлежащих migration/deprecation.
- Acceptance criteria:
  - для каждого долгоживущего хранилища есть owner, expected shape и update path;
  - устранены или явно задокументированы противоречия вида `vacancy-local adoptions.md` vs `adoptions/inbox/<vacancy_id>.md`, `promts/` vs skill-first docs, missing `contact-regions.yml`.
- Validation commands:
  - `Get-Content -Raw C:\Users\avramko\OneDrive\Documents\Career\plans\resume-agent-spec.md`
  - `Get-Content -Raw C:\Users\avramko\OneDrive\Documents\Career\templates\excel\response-monitoring-mapping.md`
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\adoptions -Recurse -File`
- Notes / discoveries:
  - `resume-agent-spec.md` содержит целевую структуру, но часть путей и контрактов уже устарела относительно фактического workspace.

### M3. Output Pipeline Migration Path

- Status: `planned`
- Goal:
  - определить, как manual employer-specific и historical outputs переводятся в поддерживаемый pipeline для resume export, LinkedIn, screening prep и related artifacts.
- Deliverables:
  - migration path для ручных PDF/DOCX/export scripts;
  - target placement rules для будущих output-артефактов;
  - решение, какие существующие employer-specific traces сохраняются как examples/tests/reference.
- Acceptance criteria:
  - manual renderer и архивные outputs не остаются "висячими" артефактами без статуса;
  - для каждого важного output family понятно, где он должен жить и чем генерироваться в будущем;
  - определены границы между reusable pipeline и employer-specific one-off artifacts.
- Validation commands:
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\Employers -Recurse -File`
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\archive -File`
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\CV\versions -File`
- Notes / discoveries:
  - `Employers/TaxDome/render_resume_pdf.py` — явный пример manual-only export path с hardcoded filenames и font paths.
  - архив хранит outputs в нескольких naming styles, что указывает на отсутствие единого output contract.

### M4. Legacy Prompt Corpus Distillation

- Status: `planned`
- Goal:
  - превратить накопленные prompt- и corpus-материалы в управляемый knowledge/spec layer, а не в разрозненные reference files.
- Deliverables:
  - список prompt/doc artifacts, которые надо перенести в планы, тесты, templates или workflow specs;
  - список prompt/doc artifacts, которые можно оставить historical-only;
  - приоритизированный extraction backlog.
- Acceptance criteria:
  - для `promts/*.md`, `responses.md`, `adoptions_00.md` определен дальнейший статус;
  - ни один крупный слой бизнес-логики не остается только в одном громоздком legacy файле без migration path.
- Validation commands:
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\promts -File`
  - `rg -n "^#|^##|^###" C:\Users\avramko\OneDrive\Documents\Career\responses.md`
  - `rg -n "^#|^##|^###" C:\Users\avramko\OneDrive\Documents\Career\adoptions_00.md`
- Notes / discoveries:
  - corpus уже достаточно большой, чтобы без дистилляции он продолжал расходиться с кодом и актуальными планами.

## Decision log

- `2026-04-21 16:43` — Root data/template/output layer выделен в отдельный workstream. — Найденные проблемы относятся не к логике workflow как таковой, а к source-of-truth и artifact ownership. — Это уменьшает риск смешать contract work с feature implementation.
- `2026-04-21 16:43` — Legacy prompt corpus рассматривается как valuable input, но не как финальная форма хранения бизнес-правил. — Он уже пересекается со спецификациями и частично дублирует их. — План должен привести его к более управляемому виду.
- `2026-04-21 16:43` — Manual employer-specific outputs признаны частью архитектурного контекста, а не мусорными файлами. — Они помогают восстановить ожидаемый output pipeline и критерии качества. — Их нельзя игнорировать при реконструкции проекта.

## Progress log

- `2026-04-21 16:43` — Подтверждено, что `CV/` насыщен версиями, а `profile/`, `knowledge/`, `adoptions/` остаются в основном скелетными. — Проверка файловой структуры выявила отсутствие `profile/contact-regions.yml` и пустые long-lived stores. — Status: `planned`.
- `2026-04-21 16:43` — Найдены manual output traces в `Employers/` и `archive/`, а также крупный legacy prompt corpus в `promts/`, `responses.md`, `adoptions_00.md`. — Это указывает на незавершенную миграцию от prompt-first/manual workflows к tool-driven pipeline. — Status: `planned`.

## Current state

- Current milestone: `M1`
- Current status: `planned`
- Next step: `Собрать producer/consumer inventory для CV, profile, knowledge, adoptions, vacancies, templates, Employers, archive и legacy prompt corpus.`
- Active blockers:
  - Не определено, какой root-слой считается каноническим для контактов, постоянных сигналов и adoptions.
  - Не определен target home для PDF/LinkedIn/export pipeline.
  - Не определен статус крупных legacy prompt/doc artifacts.
- Open questions:
  - Нужно ли поддерживать employer-specific output directories как first-class part of workspace или перевести их в examples/fixtures?
  - Оставлять ли vacancy-local `adoptions.md` после введения корневого inbox workflow?
  - Должно ли `CV/MASTER.md` оставаться единственным facts source, если часть будущей нормализации будет переноситься в `knowledge/` и memory stores?
  - Стоит ли переименовывать `promts/` и какие последствия это создаст для уже существующих процессов?

## Completion summary

Заполняется после завершения workstream-а по нормализации root artifacts и output pipeline.
