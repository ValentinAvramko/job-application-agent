# Root Artifacts And Output Normalization

- Title: `Root artifacts and output normalization`
- Slug: `2026-04-21-root-artifacts-and-output-normalization`
- Owner: `Codex`
- Created: `2026-04-21`
- Last updated: `2026-04-22 09:10`
- Overall status: `done`

## Objective

Превратить root workspace из смеси active, partial, historical и manual-only артефактов в понятный data/template/output layer с явными source-of-truth правилами и одновременно:

- перенести содержательные решения из superseded root planning artifacts в актуальные plan files;
- убрать конкурирующие источники истины по структуре workspace и workflow roadmap;
- подготовить удаление старых root plan/spec files после миграции.

## Background and context

Разведка root показала несколько слоёв артефактов:

- активные источники фактов и рабочих материалов: `resumes/`, `vacancies/`, `response-monitoring.xlsx`, `agent_memory/`;
- partially initialized long-lived stores: `knowledge/`, `profile/`, `adoptions/`;
- reusable templates: `templates/`;
- legacy prompt/doc corpus: `promts/`, `responses.md`, `adoptions_00.md`;
- manual output traces и employer-specific artifacts: `employers/`, `archive/`;
- superseded planning artifacts в удалённом root `plans/`.

Подтверждённые факты:

- `resumes/MASTER.md` и ролевые resumes остаются основным resume-слоем о кандидате;
- `profile/contact-regions.yml` ожидается целевой моделью, но сейчас отсутствует;
- `knowledge/roles` и `adoptions/accepted|inbox` почти пусты и не участвуют в runtime;
- `vacancies/` содержит реальные workflow artifacts и сегодня является главным рабочим output layer;
- `employers/TaxDome/render_resume_pdf.py` и файлы в `archive/` фиксируют manual-only historical traces;
- содержимое старых root docs `plans/resume-agent-spec.md` и `plans/repository-topology.md` уже перенесено в active plans; сами root files удалены и больше не должны существовать как отдельные источники истины.

Мигрируемые решения из superseded root docs:

- public/private split: код и implementation plans живут в `tooling/application-agent`, root хранит данные, шаблоны и outputs;
- target workflow catalog: после текущего стека предполагаются `prepare-screening`, `rebuild-master`, `rebuild-role-resume`, `build-linkedin`, `export-resume-pdf`;
- source-of-truth rules: `resumes/MASTER.md` — главный facts source, role resumes — производные, contact/profile overlays должны жить отдельно от resume text;
- целевая root topology: `resumes/`, `vacancies/`, `knowledge/`, `adoptions/`, `profile/`, `agent_memory/`, `templates/`, `employers/`, `archive/`.

## Scope

### In scope

- source-of-truth map для значимых root directories и file families;
- нормализация ролей каталогов `resumes/`, `profile/`, `knowledge/`, `adoptions/`, `vacancies/`, `templates/`, `employers/`, `archive/`, `promts/`;
- определение target path для output pipeline: resume text artifacts, LinkedIn outputs, screening prep, PDF export и employer-specific artifacts;
- migration superseded root planning artifacts в актуальные plan files;
- удаление старых root plan/spec files после переноса содержательных решений.

### Out of scope

- изменение core-кода workflow без отдельного workstream-плана;
- генерация новых PDF/DOCX/LinkedIn материалов;
- редактирование фактического содержимого resume/profile data;
- удаление исторических output artifacts без явной retention policy.

## Assumptions

- `resumes/MASTER.md` остаётся главным facts source для candidate profile;
- role resumes представляют производные ролевые представления, а не независимые источники истины;
- missing/empty files в `knowledge/`, `profile/`, `adoptions/` означают незавершённый data layer, а не intentional final state;
- superseded root planning artifacts можно удалять после того, как их целевые решения явно встроены в active plans.

## Risks and unknowns

- часть naming/schema conventions уже расходится между templates, кодом и manual artifacts;
- неясно, какой процент legacy prompt/doc corpus должен стать tests/specs, а какой можно оставить historical-only;
- при migration старых planning artifacts легко потерять полезный target intent по topology и workflow roadmap;
- неясно, где в итоге должен жить окончательный export pipeline: в public agent, private root или в hybrid scheme.

## External touchpoints

- `C:\Users\avramko\OneDrive\Documents\Career\resumes\` — чтение / проверка — master и role resumes, версии и facts source;
- `C:\Users\avramko\OneDrive\Documents\Career\profile\` — чтение / возможное обновление / проверка — contact regions и metadata;
- `C:\Users\avramko\OneDrive\Documents\Career\knowledge\` — чтение / возможное обновление / проверка — role/company signals;
- `C:\Users\avramko\OneDrive\Documents\Career\adoptions\` — чтение / возможное обновление / проверка — inbox, accepted, questions;
- `C:\Users\avramko\OneDrive\Documents\Career\vacancies\` — чтение / проверка — vacancy-local artifacts;
- `C:\Users\avramko\OneDrive\Documents\Career\templates\` — чтение / возможное обновление / проверка — reusable templates и schema hints;
- `C:\Users\avramko\OneDrive\Documents\Career\promts\`, `responses.md`, `adoptions_00.md` — чтение / проверка — legacy business logic corpus;
- `C:\Users\avramko\OneDrive\Documents\Career\employers\` и `archive\` — чтение / проверка — manual historical/reference traces;
- `C:\Users\avramko\OneDrive\Documents\Career\plans\` — чтение / migration / removal — superseded root planning artifacts; каталог уже отсутствует и не должен возвращаться.

## M1 Inventory Matrix

| Root artifact | Representative contents | Producer | Consumer | Classification | Current status / issue |
| --- | --- | --- | --- | --- | --- |
| `resumes/` | `MASTER.md`, `CIO.md`, `CTO.md`, `HoE.md`, `HoD.md`, `EM.md`, `versions/`, `OPTIONAL_RULES.yml` | Manual profile maintenance and historical exports | `analyze-vacancy`, `prepare-screening`, manual resume editing | `MASTER.md` is canonical; role resumes are derived; `versions/` is historical/manual-only; `OPTIONAL_RULES.yml` is legacy/manual-only for now | Active runtime uses `MASTER.md` and role resumes, but not `versions/` or `OPTIONAL_RULES.yml`; active and historical resume artifacts live side by side |
| `profile/` | `README.md`, missing `contact-regions.yml`, template in `templates/profile/` | `bootstrap` creates the directory; expected human-maintained metadata later | Planned contact/profile-aware workflows only | Intended canonical metadata store | Structurally declared but functionally missing: the target file does not exist and no current workflow reads it |
| `knowledge/` | `README.md`, `roles/README.md`, empty `company_signals/` | `bootstrap` creates the store; future normalization/adoption workflow should populate it | Future resume rebuild and signal accumulation workflows | Intended canonical long-lived signal store | Mostly skeletal; no current runtime writer or reader |
| `adoptions/` | `README.md`, empty `inbox/`, empty `accepted/`, `questions/open.md` | `bootstrap` creates the store; future review workflow should write to it | Future resume rebuild/adoption workflows | Intended canonical review store | Conflicts with the current reality: live workflow writes `vacancies/<id>/adoptions.md`, while root inbox/accepted remain unused |
| `vacancies/` | per-vacancy `meta.yml`, `source.md`, `analysis.md`, `adoptions.md` | `ingest-vacancy`, `analyze-vacancy`, `prepare-screening` | Runtime memory, operator review, future downstream workflows | Active generated workspace per vacancy | This is the real active artifact family today; it mixes local record, analysis output and vacancy-local adoptions |
| `response-monitoring.xlsx` | ingest ledger workbook, schema map in `templates/excel/response-monitoring-mapping.md` | `ingest-vacancy` integration plus manual spreadsheet edits | Operator tracking and reconciliation | Active canonical tracking ledger | Real business contract exists, but part of the schema still lives in spreadsheet/template documentation instead of a dedicated root contract file |
| `templates/` | profile, knowledge, adoptions, interview and Excel templates | Manual design/spec work | Humans and plan documents; current runtime does not read these files directly | Template/spec layer | Useful reference corpus, but not wired into bootstrap or workflow rendering, so drift risk is high |
| `agent_memory/` | runtime memory, schemas, workflow contracts | `bootstrap`, memory store, workflow execution | CLI workflows and operator diagnostics | Active private runtime/state layer | Canonical for runtime state, but may keep stale vacancy references until explicit reconciliation |
| `promts/` + `responses.md` + `adoptions_00.md` | legacy prompts and large historical corpora | Legacy manual/prompt-first workflow | Human reference only for now | Legacy / stale but potentially mineable corpus | Still valuable as raw input, but now competes with active plans if treated as current spec |
| `employers/` | employer-specific resumes, notes, `TaxDome/render_resume_pdf.py`, preview PNGs | Manual one-off tailoring/export work | Human/operator only | Manual-only / historical examples | Contains unsupported manual pipeline fragments outside current tool contract and is not used by agents |
| `archive/` | historical specialized vacancy/resume exports and related artifacts | Manual archival flow | Human archive only | Historical output store | Manual-only archive; not used by runtime or agent workflows |
| historical root `plans/` | removed root `plans/` directory and superseded spec files | Legacy planning process | None after migration | Stale / removed | Content was migrated; the directory is absent by design and must not reappear as a source of truth |

## M1 Migration Map For Superseded Planning Artifacts

| Old artifact | Current status | Active destination after migration | Notes |
| --- | --- | --- | --- |
| `C:\Users\avramko\OneDrive\Documents\Career\plans\resume-agent-spec.md` | removed | `plans/2026-04-21-repository-reconstruction-and-backlog.md`, `plans/2026-04-21-root-artifacts-and-output-normalization.md` | Public/private split, workflow catalog, source-of-truth rules and cleanup ordering were redistributed into active plans |
| `C:\Users\avramko\OneDrive\Documents\Career\plans\repository-topology.md` | removed | `AGENTS.MD`, `plans/2026-04-21-repository-reconstruction-and-backlog.md`, `plans/2026-04-21-root-artifacts-and-output-normalization.md` | Root topology and routing rules now live in root instructions plus active submodule plans |
| `C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\plans\ingest-refactor-plan.md` | removed | `plans/2026-04-21-workflow-contract-alignment-and-safety.md`, `README.md` | Workflow/safety decisions were retained in the dedicated safety plan and in the repository README architecture notes |

## M2 Canonical Contract Map

| Artifact family | Canonical role | Non-canonical / derived layer | Owner / update path | Decision |
| --- | --- | --- | --- | --- |
| `resumes/MASTER.md` | Single source of truth for durable candidate facts and verified career narrative | `resumes/<role>.md` are derived role views; `resumes/versions/` is historical manual snapshot storage outside runtime; `resumes/OPTIONAL_RULES.yml` is legacy/manual-only until code explicitly consumes it | Human-maintained; future rebuild workflows may read from it but should not supersede it | `MASTER.md` remains the only durable facts source for resume content |
| `profile/contact-regions.yml` | Canonical store for contact overlays, region-specific contacts, relocation/location and public profile links | `templates/profile/contact-regions.template.yml` is only a seed template, not fallback runtime data | Human-maintained file under `profile/`; current workflows remain contact-agnostic until file exists | Missing file is a documented data gap, not a signal to duplicate contacts back into resume text |
| `knowledge/roles/*.md`, `knowledge/company_signals/*.md` | Canonical normalized reusable signals after review/promotion from vacancy analysis | Vacancy-local notes and prompt corpora are raw inputs only | Curated manually or by future normalization workflows after review | `knowledge/` is a long-lived signal layer, but not a co-equal facts source with `resumes/MASTER.md` |
| `adoptions/inbox/<vacancy_id>.md` | Canonical per-vacancy review record for proposed resume changes | `vacancies/<id>/adoptions.md` is a generated staging/compatibility artifact for the current runtime | Future path: analyze flow may stage locally, then reviewed content is normalized into root inbox | Root `adoptions/inbox/` is the long-lived store; vacancy-local `adoptions.md` is not long-lived source of truth |
| `adoptions/accepted/<target>.md` | Canonical accepted change log per target resume family (`MASTER.md`, `CIO.md`, `CTO.md`, `HoE.md`, `HoD.md`, `EM.md`) | Vacancy-local recommendations and prompt corpora | Manual review and promotion from inbox into accepted | Accepted adoptions are durable reusable guidance, not per-vacancy scratch notes |
| `adoptions/questions/open.md` | Canonical backlog of unresolved data gaps that block durable normalization | Questions embedded in vacancy-local analysis/adoptions | Manual review from vacancy outputs into root questions backlog | Open questions should be centralized here once they become reusable across vacancies |
| `vacancies/<id>/meta.yml`, `source.md` | Canonical per-vacancy raw record: metadata plus captured vacancy text/source | None for the same vacancy scope | Written by `ingest-vacancy` and updated by downstream workflows | `vacancies/` remains the canonical working folder for per-vacancy execution state |
| `vacancies/<id>/analysis.md`, `screening.md` | Generated downstream artifacts for the same vacancy | Historical manual notes elsewhere | Written by `analyze-vacancy` and `prepare-screening` | These files stay vacancy-local and do not compete with long-lived root stores |
| `response-monitoring.xlsx` | Canonical application ledger for ingest/application tracking | `templates/excel/response-monitoring-mapping.md` is a human-readable contract mirror | Workbook updated by integration code and manual spreadsheet review | Workbook columns are authoritative runtime contract; the template doc must mirror them, not replace them |
| `templates/` | Human-facing reference/spec layer for future files and workflows | None | Manual upkeep only | Templates are not runtime inputs today and must not be treated as canonical data sources |
| `agent_memory/` | Canonical runtime state, workflow contract and reconciliation layer for the tool | None | Managed by bootstrap, memory store and workflow execution | Canonical for execution state, but not a source of candidate/profile truth |
| `promts/`, `responses.md`, `adoptions_00.md` | Legacy reference corpus only | Any attempt to treat them as current spec or runtime input | Read-only mining input for future distillation | Legacy corpus is explicitly non-canonical after M2 |
| `employers/`, `archive/` | Historical/manual output and one-off tailoring traces | None | Manual-only | These paths are not sources of truth for pipeline behavior and are outside runtime/agent workflows |

## M3 Output Placement Rules

| Output family | Canonical placement | Lifecycle / status | Producer | Consumer | Decision |
| --- | --- | --- | --- | --- | --- |
| `vacancies/<id>/analysis.md`, `screening.md` and future vacancy-scoped generated artifacts | `vacancies/<id>/` | Generated working state for one vacancy | Current and future vacancy workflows | Operator review, downstream vacancy workflows | Vacancy-scoped outputs stay vacancy-local and must not be promoted into `resumes/`, `employers/` or `archive/` by default |
| Future vacancy-specific tailored resume/export staging artifacts | `vacancies/<id>/` or a vacancy-local subfolder introduced later by code | Temporary/generated until explicit promotion | Future tailoring and export workflows | Operator review before publication | Productized pipeline should stage per-vacancy deliverables near the vacancy record, not inside employer-specific manual folders |
| `resumes/versions/*.md` and existing historical master snapshots | `resumes/versions/` | Historical manual snapshot archive for durable resume texts | Manual snapshotting only | Human audit / rollback only | `resumes/versions/` stores manual text history, is not used by runtime or agent workflows, and is not a target for transient per-vacancy outputs |
| `archive/*` | `archive/` | Historical manual archive for specialized vacancy/resume versions and related artifacts | Manual archival only | Human archive lookup only | `archive/` is not a runtime sink, not a working directory, and not used by agent workflows |
| `profile/linkedin.md` or equivalent durable profile artifact | `profile/` | Durable generated or edited profile representation | Future `build-linkedin` workflow | Human review and profile publishing | LinkedIn-style outputs belong with profile overlays, because they are durable profile derivatives rather than vacancy-local notes |
| Employer-specific notes, tailored one-off resumes, local helper scripts and previews under `employers/<company>/` | `employers/` | Manual-only workspace and historical reference examples | Human/manual experiments | Human/operator only | `employers/` remains outside the supported runtime pipeline, is not used by agents, and must never be the default write target for reusable workflows |
| Manual render helpers such as `employers/TaxDome/render_resume_pdf.py` and `tmp_pdf_preview/*.png` | `employers/<company>/` until replaced | Reference-only prototype artifacts | Manual one-off rendering | Human/operator only | Keep as reverse-engineering/reference material for future renderer design, but do not treat them as productized pipeline entrypoints |

## M3 Migration Path For Manual Output Traces

| Existing trace | Current classification | Future role after migration | Retention rule |
| --- | --- | --- | --- |
| `employers/TaxDome/render_resume_pdf.py` | Manual prototype renderer tied to one employer case | Reference input for future analysis only, not executable runtime contract | Keep as manual example while `employers/` exists |
| `employers/*/*.md` employer notes and tailored resume drafts | One-off manual tailoring workspace | Historical/reference corpus only; never pipeline output target | Keep as employer-local historical/reference material |
| `employers/*/*.pdf` and preview PNGs | Manual case-specific exports and render previews | Historical evidence of one-off outputs only | Keep, but classify as unsupported by runtime and agents |
| `archive/*` | Historical specialized exports and related artifacts | Historical archive only | Keep as manual archive; do not model as runtime output sink |
| `resumes/versions/*.md` historical snapshots | Resume text history | Manual snapshot archive for master or role resume evolution | Keep as manual snapshot history; do not mix with runtime artifacts |

## M4 Legacy Corpus Distillation Map

| Legacy artifact | Observed role in corpus | Managed status after distillation | Target destination for reusable content | Notes |
| --- | --- | --- | --- | --- |
| `promts/promt-analyze-vacancies-and-respond.md` | Monolithic manual playbook for vacancy analysis, fit scoring, resume adaptation, cover letter, contact handling and interview prep | Historical reference only; explicitly non-canonical | Reusable parts should inform active workflow plans: fit/adaptation rules for current stack, interview/storyline material for `plans/2026-04-21-prepare-screening-workflow.md`, and any future response/correspondence workflow spec | The file still contains valuable business intent, but bundles too many concerns and legacy file assumptions to remain a live contract |
| `promts/promt-create-master-resume.md` | Manual prompt for synthesizing a master resume from a candidate resume plus vacancy corpus | Historical reference only; explicitly non-canonical | Future `rebuild-master` workflow plan/spec, checklists and example fixtures | Useful as a requirements seed for desired roles extraction, fit consolidation, gap questions and modular adaptation logic |
| `promts/promt-create-custom-resumes.md` | Manual batch playbook for generating five role resumes from `MASTER` | Historical reference only; explicitly non-canonical | Future `rebuild-role-resume` workflow plan/spec, role-positioning rules and example fixtures | Valuable for role differentiation logic, but the monolithic batch-generation prompt should not become the runtime contract |
| `promts/promt-create-linkedin-profile.md` | Manual guide for building bilingual LinkedIn profile content from the master resume | Historical reference only; explicitly non-canonical | Future `build-linkedin` workflow plan/spec, templates and output checklist | Useful as a deliverable map and section checklist, not as a current source of truth |
| `promts/OPTIONAL_RULES.yml` | Lightweight formatting/localization preferences for manual resume generation | Legacy/manual-only helper | Future template or workflow-owned formatting policy if productized later | Not consumed by current runtime; keep outside canonical contracts until code explicitly adopts it |
| `responses.md` | Large manual vacancy corpus with 160+ role descriptions and one-off role decompositions | Historical corpus and potential eval/example bank; explicitly non-canonical | Future planning inputs, eval cases and example fixtures for vacancy analysis and screening workflows | Treat as mined evidence and sample data only; do not use as runtime input or current spec |
| `adoptions_00.md` | Large role-oriented bank of resume adaptation suggestions with `TEMP` / `PERM` statuses across CIO/CTO/HoE/HoD/EM | Historical corpus and potential example/rules bank; explicitly non-canonical | Future adoptions-review contracts, role-resume rebuild specs, examples and eval fixtures | Valuable for reusable suggestion patterns, but root `adoptions/` remains the canonical long-lived review layer after M2 |

## M4 Final Cleanup Decisions

- Superseded root planning artifacts were already removed before M4 and no additional plan/spec deletions remain open.
- `promts/`, `responses.md` and `adoptions_00.md` stay in the repository as read-only historical/reference corpus until successor workflow specs and examples fully absorb the reusable parts.
- Active plans and runtime stores remain the only current sources of truth; the legacy corpus must not be edited to represent live workflow behavior.
- Reusable rules mined from the legacy corpus should move into one of three destinations only: active plans, future templates/spec artifacts, or eval/example fixtures.

## Milestones

### M1. Root Artifact Inventory And Migration Map

- Status: `done`
- Goal:
  - собрать inventory matrix, где для каждого root-слоя указаны назначение, producer, consumer, status и проблемы;
  - составить migration map для superseded root planning artifacts.
- Deliverables:
  - inventory matrix по `resumes/`, `profile/`, `knowledge/`, `adoptions/`, `vacancies/`, `templates/`, `promts/`, `employers/`, `archive/`, historical root `plans/`, `response-monitoring.xlsx`, `agent_memory/`;
  - классификация артефактов: canonical / generated / template / historical / manual-only / stale;
  - mapping `old artifact -> new active plan/doc destination`.
- Acceptance criteria:
  - для каждого крупного каталога понятна его роль и связь с submodule;
  - отдельно отмечены пустые, отсутствующие, дублирующиеся и legacy-only области;
  - для `plans/resume-agent-spec.md` и `plans/repository-topology.md` определено, куда именно мигрирует их содержимое.
- Validation commands:
  - `Get-ChildItem resumes,templates,profile,knowledge,adoptions,employers,archive -Recurse -File`
  - `Test-Path "C:\Users\avramko\OneDrive\Documents\Career\plans"`
  - `Test-Path "C:\Users\avramko\OneDrive\Documents\Career\profile\contact-regions.yml"`
  - `Get-ChildItem vacancies -Directory`
- Notes / discoveries:
  - `profile/contact-regions.yml` отсутствует.
  - `knowledge/roles` и `adoptions/accepted|inbox` пока не выполняют заявленную роль постоянной базы.
  - Current code активно читает/пишет только `resumes/`, `vacancies/`, `agent_memory/` и `response-monitoring.xlsx`; `profile/`, `knowledge/`, `adoptions/` остаются target stores, а не active workflow stores.
  - Vacancy-local `vacancies/<id>/adoptions.md` — единственное adoptions family, которое сейчас генерирует инструмент.
  - Historical root `plans/` уже удалён; дальнейшая работа должна решать контракты без восстановления root plan/spec corpus.

### M2. Canonical Root Contract Decisions

- Status: `done`
- Goal:
  - определить, какие root-артефакты являются источником истины, какие производными, а какие историческими;
  - встроить migrated target intent из старых root docs в новую структуру планов.
- Deliverables:
  - canonical contract map для `resumes`, `profile`, `knowledge`, `adoptions`, `vacancies`, Excel и templates;
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
  - `resumes/MASTER.md` сохранён как единственный durable facts source; `knowledge/` и `profile/` признаны вспомогательными canonical stores, но не заменой `MASTER`.
  - `adoptions/inbox/` и `adoptions/accepted/` зафиксированы как long-lived canonical review layer, а vacancy-local `adoptions.md` — как generated staging/compatibility artifact текущего runtime.
  - `templates/` и legacy prompt corpus признаны non-runtime reference layers; они не должны конкурировать с plan files и runtime stores как sources of truth.

### M3. Output Pipeline Migration Path

- Status: `done`
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
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\employers -Recurse -File`
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\archive -File`
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\resumes\versions -File`
- Notes / discoveries:
  - `employers/TaxDome/render_resume_pdf.py` is a manual-only reference path.
  - `resumes/versions/` is a manual historical text-version archive and is not used by runtime or agent workflows.
  - `archive/` is a manual historical archive for specialized versions and related artifacts, not a runtime sink.
  - `employers/` is a manual workspace/reference layer and is not used by runtime or agent workflows.
  - Productized outputs should stage only in workflow-owned runtime directories; `archive/`, `resumes/versions/` and `employers/` remain outside agent-managed flows.

### M4. Legacy Prompt And Superseded Plan Distillation

- Status: `done`
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
  - `promts/*.md` распались на четыре будущих workflow направления: analyze/respond, rebuild-master, rebuild-role-resume и build-linkedin.
  - `responses.md` — это исторический vacancy corpus/manual evidence bank, полезный для future eval/spec work, но не runtime input.
  - `adoptions_00.md` — это исторический банк role-specific adoption suggestions; он не конкурирует с canonical root `adoptions/`, а может служить только reference/examples corpus.
  - Superseded root plan/spec artifacts уже удалены; M4 зафиксировал, что дальнейшая работа состоит не в дополнительных удалениях, а в controlled reuse legacy corpus.

## Decision log

- `2026-04-21 16:43` — Root data/template/output layer выделен в отдельный workstream. — Найденные проблемы относятся к source-of-truth и artifact ownership, а не только к логике workflow. — Это уменьшает риск смешать cleanup и feature implementation.
- `2026-04-21 16:43` — Legacy prompt corpus рассматривается как valuable input, но не как финальная форма хранения бизнес-правил. — Он уже пересекается со спецификациями и частично дублирует их. — Нужна управляемая distillation.
- `2026-04-21 19:51` — Superseded root plan/spec artifacts должны быть не просто помечены, а полностью мигрированы в актуальные plans и затем удалены. — Это убирает параллельные источники истины в root `plans/`. — Migration/removal встроены в milestones M1-M4.
- `2026-04-21 20:35` — `vacancies/<id>/adoptions.md` зафиксирован как текущий generated vacancy-local artifact, а не как long-lived canonical adoptions store. — Root `adoptions/` существует как целевая структура, но еще не подключен к runtime. — M2 должен был зафиксировать separation between vacancy-local staging and long-lived review storage.
- `2026-04-21 20:35` — Текущий runtime root-контракт фактически опирается на `resumes/`, `vacancies/`, `agent_memory/` и `response-monitoring.xlsx`; `templates/`, `resumes/versions/`, `archive/`, `employers/` и legacy prompt corpus пока не являются runtime inputs. — Это подтверждено поиском по коду и фактической файловой структурой. — Дальнейшие решения нужно принимать относительно реального producer/consumer graph.
- `2026-04-21 21:02` — Root canonical contracts разделены на три слоя: durable source-of-truth stores, vacancy-local generated execution artifacts и historical/reference layers. — Это позволило снять конфликт между root `adoptions/` и vacancy-local `adoptions.md`, а также между workbook-контрактом и template docs. — После M2 следующий фокус смещается на output pipeline migration path.
- `2026-04-21 20:33` — Output placement зафиксирован как разделение между runtime-owned vacancy-local artifacts и manual-only historical/reference layers. — Это снимает конфликт между `resumes/versions/`, `archive/` и `employers/`: все три пути остаются ручными архивными слоями вне productized pipeline. — M3 считается закрытым, следующий фокус смещается на legacy corpus distillation.
- `2026-04-22 09:10` — Legacy corpus зафиксирован как read-only historical/reference layer с явным distillation map по будущим workflow-направлениям. — Это снимает неопределённость вокруг `promts/`, `responses.md` и `adoptions_00.md`: полезное содержимое можно переиспользовать только через active plans, templates/specs или eval/examples, но не как live contract. — Workstream root normalization считается завершённым.

## Progress log

- `2026-04-21 16:43` — Подтверждено, что `resumes/` насыщен версиями, а `profile/`, `knowledge/`, `adoptions/` остаются в основном скелетными. — Проверка файловой структуры выявила отсутствие `profile/contact-regions.yml` и пустые long-lived stores. — Status: `planned`.
- `2026-04-21 16:43` — Найдены manual output traces в `employers/` и `archive/`, а также крупный legacy prompt corpus в `promts/`, `responses.md`, `adoptions_00.md`. — Это указывает на незавершенную миграцию от prompt-first/manual workflows к tool-driven pipeline. — Status: `planned`.
- `2026-04-21 19:51` — План переприоритизирован в следующий активный этап master plan и расширен migration/removal задачей для superseded root planning artifacts. — Следующий фокус: inventory + migration map, а не feature work. — Status: `in_progress`.
- `2026-04-21 19:51` — Содержательные решения superseded root planning artifacts перенесены в active plans, а сами root files удалены. — Дальнейший focus смещается с migration/removal на оставшиеся root contracts и producer/consumer inventory. — Status: `in_progress`.
- `2026-04-21 20:35` — В план добавлены M1 inventory matrix и migration map по реальным root artifacts, включая `response-monitoring.xlsx`, `agent_memory/`, legacy corpus и уже удаленный root `plans/`. — Проверка кода показала, что runtime сегодня реально работает через `resumes/`, `vacancies/`, `agent_memory/` и Excel, а `profile/`, `knowledge/`, `adoptions/` пока остаются целевыми stores; validation confirmed `Test-Path root/plans = False`, `Test-Path profile/contact-regions.yml = False`, `vacancies/` currently contains 3 directories. — Status: `done`.
- `2026-04-21 21:02` — M2 canonical contract map добавлен в workstream-план и зафиксировал роли для `resumes`, `profile`, `knowledge`, `adoptions`, `vacancies`, Excel, templates, legacy corpus и manual output traces. — Ключевые решения: `resumes/MASTER.md` остается единственным durable facts source, root `adoptions/` — long-lived review layer, а vacancy-local `adoptions.md` — generated staging artifact. — Status: `done`.
- `2026-04-21 20:33` — M3 output placement rules добавлены в workstream plan и закрепили, что vacancy-scoped generation живет в `vacancies/<id>/`, а `resumes/versions/`, `archive/` и `employers/` остаются manual-only historical/reference layers вне runtime и agent workflows. — Валидация подтвердила фактическое contents `employers/`, `archive/` и `resumes/versions/`, включая one-off renderer script и historical artifacts. — Status: `done`.
- `2026-04-22 09:10` — M4 закрыт: добавлена distillation map для `promts/*.md`, `responses.md` и `adoptions_00.md`, а legacy corpus закреплён как historical/reference layer без права конкурировать с active plans и runtime stores. — Review структуры файлов показал четыре будущих workflow направления в `promts/`, исторический vacancy corpus в `responses.md` и historical adoption bank в `adoptions_00.md`; старые root plan/spec files по-прежнему отсутствуют. — Status: `done`.

## Current state

- Current milestone: `M4`
- Current status: `done`
- Next step: `Перейти к master milestone M4 и зафиксировать current workflow completion gate для `bootstrap`, `ingest-vacancy` и `analyze-vacancy`.`
- Active blockers:
  - none
- Open questions:
  - none

## Completion summary

- Поставлена полная карта root artifact contracts: active runtime stores, target long-lived stores, manual historical layers и legacy reference corpus.
- Провалидированы и закрыты M1-M4: inventory/migration map, canonical contracts, output placement и distillation legacy corpus.
- Подтверждено, что superseded root plan/spec artifacts удалены, а `promts/`, `responses.md` и `adoptions_00.md` остаются только historical/reference слоями.
- Следующий follow-up — не продолжение cleanup, а master-level completion gate по текущему workflow-стеку.
