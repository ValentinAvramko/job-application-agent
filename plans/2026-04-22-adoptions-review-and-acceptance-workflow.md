# Adoptions Review And Acceptance Workflow

- Title: `adoptions review and acceptance workflow`
- Slug: `2026-04-22-adoptions-review-and-acceptance-workflow`
- Owner: `Codex`
- Created: `2026-04-22`
- Last updated: `2026-04-22 15:53`
- Overall status: `done`

## Objective

Подготовить отдельный workflow/process для review и принятия постоянных сигналов так, чтобы:

- vacancy-specific предложения сначала попадали в `adoptions/inbox/<vacancy_id>.md`;
- unresolved вопросы накапливались в `adoptions/questions/`;
- отдельная interactive agent-guided session переводила approved signals в `adoptions/accepted/MASTER.md`;
- в этой же session при необходимости пересматривались `knowledge/roles/`;
- downstream `rebuild-master` получал уже только approved permanent signals, а не сырые vacancy drafts.

## Background and context

После завершения `prepare-screening` следующим remaining workflow по backlog initially выглядел `rebuild-master`, но owner-level clarification зафиксировала другое sequencing:

1. после анализа каждой вакансии сырые предложения должны жить в `adoptions/inbox/<vacancy_id>.md`;
2. параллельно должны накапливаться вопросы в `adoptions/questions/`;
3. отдельный ручной/agent-guided process должен разбирать `inbox/`, собирать ответы на `questions/`, формировать `accepted/` и при необходимости пересматривать `knowledge/roles/`;
4. только после этого отдельный, более редкий process обновляет `resumes/MASTER.md`, а затем downstream role resumes.

Дополнительно подтверждено:

- `vacancies/<id>/adoptions.md` уже существует как generated staging artifact после `analyze-vacancy`;
- `adoptions/` уже содержит `inbox/`, `accepted/`, `questions/`;
- `adoptions/questions/open.md` уже существует как placeholder shared ledger;
- `knowledge/roles/` пока практически пуст, но остаётся intended normalized store;
- accepted permanent signals должны сначала жить в `adoptions/accepted/MASTER.md`, а не попадать напрямую в `resumes/MASTER.md`;
- role resumes всегда должны строиться только downstream от согласованного `resumes/MASTER.md`.

Это означает, что review/acceptance process стал самостоятельным upstream workflow family и больше не должен быть скрытой частью `rebuild-master`.

## Scope

### In scope

- file/state contract для `adoptions/inbox/`, `adoptions/questions/`, `adoptions/accepted/`, `knowledge/roles/`;
- sequencing между vacancy-local `adoptions.md` и root review layers;
- минимальный contract для deterministic intake step и отдельной interactive acceptance session;
- implementation-ready decomposition для последующей автоматизации этого review process.

### Out of scope

- прямое обновление `resumes/MASTER.md`;
- реализация `rebuild-master` и role resume rebuild;
- ретроспективная миграция всех historical vacancy artifacts в `inbox/`;
- redesign форматов vacancy-local `analysis.md` или `screening.md`.

## Assumptions

- `vacancies/<id>/adoptions.md` остаётся generated draft, а не durable review layer;
- `adoptions/inbox/<vacancy_id>.md` хранит один review input file на одну вакансию;
- `adoptions/questions/open.md` остаётся initial shared ledger для unresolved/answered items;
- ответы на вопросы получаются в agent-guided Q&A session внутри review process, а не отдельным ручным merge вне него;
- `adoptions/accepted/MASTER.md` хранит нормализованный current-state набор approved permanent signals без обязательной полной истории решений;
- role-specific accepted artifacts на этом этапе не вводятся;
- `knowledge/roles/` пересматривается в acceptance session как shaping layer для будущих role resumes;
- role resumes всегда downstream-зависят от согласованного `resumes/MASTER.md`, а не от `accepted/` напрямую.

## Risks and unknowns

- если deterministic intake step и interactive review session снова смешаются в один workflow, generated drafts и approved signals опять окажутся без чёткой границы;
- если `adoptions/questions/open.md` начнёт использоваться как неструктурированный notes dump, Q&A session не сможет надёжно отслеживать unresolved vs answered items;
- если `accepted/MASTER.md` начнёт хранить историю вместо current-state набора сигналов, downstream merge в `MASTER` станет нестабильным;
- future scale может потребовать per-vacancy question files и отдельной history/archive policy, но это не блокирует initial implementation.

## External touchpoints

- `C:\Users\avramko\OneDrive\Documents\Career\vacancies\` — чтение / проверка — source generated vacancy-local `adoptions.md`;
- `C:\Users\avramko\OneDrive\Documents\Career\adoptions\inbox\` — обновление / проверка — per-vacancy review inputs;
- `C:\Users\avramko\OneDrive\Documents\Career\adoptions\questions\` — обновление / проверка — unresolved questions ledger;
- `C:\Users\avramko\OneDrive\Documents\Career\adoptions\accepted\` — обновление / проверка — approved permanent signals;
- `C:\Users\avramko\OneDrive\Documents\Career\knowledge\roles\` — обновление / проверка — role-shaping knowledge revised during review;
- `C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\plans\2026-04-22-rebuild-master-workflow.md` — чтение / проверка — downstream dependency and handoff.

## Milestones

### M1. Review Layer Contract Baseline

- Status: `done`
- Goal:
  - зафиксировать owner-approved process sequencing и существующие root stores для review/acceptance layer.
- Deliverables:
  - этот plan;
  - baseline contract для `inbox/`, `questions/`, `accepted/`, `knowledge/roles/`;
  - явная привязка к downstream `rebuild-master`.
- Acceptance criteria:
  - plan описывает, какие слои используются до обновления `MASTER`;
  - роль `vacancies/<id>/adoptions.md` vs `adoptions/inbox/<vacancy_id>.md` разделена явно;
  - есть один конкретный следующий шаг для implementation planning.
- Validation commands:
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\adoptions -Recurse`
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\knowledge -Recurse`
- Notes / discoveries:
  - owner-approved sequencing делает этот workflow upstream dependency для `rebuild-master`.

### M2. Session Shape And File Contract

- Status: `done`
- Goal:
  - определить точный interaction model и file-level contract для acceptance session.
- Deliverables:
  - decision record по interaction shape;
  - format expectations для `inbox/`, `questions/`, `accepted/MASTER.md`;
  - updated current state без архитектурной двусмысленности.
- Acceptance criteria:
  - ясно, что workflow разделён на deterministic intake step и отдельную interactive review session;
  - ясно, как вопросы живут в `questions/` и как ответы влияют на `accepted/MASTER.md`;
  - ясно, когда и как пересматривается `knowledge/roles/`.
- Validation commands:
  - `Get-Content -Raw plans\2026-04-22-adoptions-review-and-acceptance-workflow.md`
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\adoptions -Recurse | Select-Object FullName`
  - `Get-Content -Raw C:\Users\avramko\OneDrive\Documents\Career\adoptions\questions\open.md`
- Notes / discoveries:
  - acceptance path зафиксирован как два explicit stages, а не один монолитный workflow;
  - `adoptions/inbox/` хранит один файл на одну вакансию;
  - `adoptions/questions/open.md` остаётся initial shared ledger, а ответы получаются в interactive agent Q&A session;
  - `adoptions/accepted/MASTER.md` остаётся единственным approved current-state artifact для permanent signals;
  - role-specific accepted artifacts на этом этапе не вводятся.

### M3. Implementation-Ready Acceptance Workflow Plan

- Status: `done`
- Goal:
  - разложить review/acceptance process на исполнимые implementation milestones.
- Deliverables:
  - code-facing milestone decomposition;
  - validation baseline;
  - dedicated execution plan `2026-04-22-implement-adoptions-review-and-acceptance-workflow.md`;
  - handoff в execution cycle перед `rebuild-master`.
- Acceptance criteria:
  - следующий инженер сможет начать реализацию review/acceptance workflow только по этому plan;
  - downstream handoff в `rebuild-master` будет описан без дополнительных устных пояснений.
- Validation commands:
  - `Get-Content -Raw plans\2026-04-22-adoptions-review-and-acceptance-workflow.md`
  - `Get-Content -Raw plans\2026-04-22-implement-adoptions-review-and-acceptance-workflow.md`
- Notes / discoveries:
  - initial implementation path зафиксирован как hybrid model: deterministic intake становится runtime workflow, а interactive review остаётся agent-guided session, поддержанной кодовыми helper-модулями, тестами и workflow docs, без обязательного standalone interactive CLI REPL.

## Interaction and file contract

- `vacancies/<id>/adoptions.md` — generated vacancy-local draft; не является durable review layer.
- `adoptions/inbox/<vacancy_id>.md` — deterministic review input, один файл на одну вакансию.
- `adoptions/questions/open.md` — shared unresolved ledger; записи должны идентифицировать vacancy, topic, current status и latest answer state.
- `adoptions/accepted/MASTER.md` — canonical approved current-state set of permanent signals; не history log.
- `knowledge/roles/` — reference/shaping layer, которая может обновляться в acceptance session, но не подменяет `accepted/MASTER.md` и `resumes/MASTER.md`.
- `resumes/MASTER.md` не мутируется в acceptance workflow; это downstream отдельный process.

## Implementation decomposition draft

- `A1 Intake workflow`:
  - отдельная deterministic CLI/runtime operation;
  - читает `vacancies/<id>/adoptions.md`;
  - готовит `adoptions/inbox/<vacancy_id>.md`;
  - обновляет `adoptions/questions/open.md` initial unresolved items;
  - не трогает `accepted/` и `resumes/`.
- `A2 Review support layer`:
  - helper-модули и форматы для загрузки pending inbox items, question ledger и `accepted/MASTER.md`;
  - подготовка данных для agent-guided Q&A session;
  - применение approved updates к `accepted/MASTER.md`, `questions/open.md` и при необходимости `knowledge/roles/`.
- `A3 Runtime/docs/tests alignment`:
  - registry/CLI/docs/tests явно описывают intake как runtime workflow, а review как отдельную agent-guided stage;
  - generated drafts, unresolved questions и approved signals разделены и валидируются по тестам/докам;
  - runtime memory и operator docs отражают новый sequencing.
- `A4 Rebuild-master handoff`:
  - `2026-04-22-rebuild-master-workflow.md` читает этот upstream workflow как стабильный input contract;
  - downstream `rebuild-master` не зависит от raw vacancy drafts и не редактирует role resumes.

## Decision log

- `2026-04-22 11:42` — Owner-approved sequencing закрепил отдельный upstream process: `vacancies/<id>/adoptions.md` -> `adoptions/inbox/<vacancy_id>.md` + `adoptions/questions/` -> `adoptions/accepted/MASTER.md` + `knowledge/roles/`. — Это убирает скрытую перегрузку из `rebuild-master`. — Дальнейшая реализация resume mutation должна идти только downstream от этого process.
- `2026-04-22 11:42` — `accepted/MASTER.md` признан canonical approved staging layer, а не history log. — Это делает downstream merge в `resumes/MASTER.md` детерминированнее. — Историю, если она потребуется, нужно будет проектировать отдельно.
- `2026-04-22 13:50` — Interaction model зафиксирован как два explicit stages: deterministic intake prep и отдельная interactive agent-guided review session. — Это разводит generated vacancy drafts и human/agent adjudication. — Implementation decomposition должна опираться именно на эту границу.
- `2026-04-22 13:50` — `adoptions/questions/open.md` остаётся initial shared ledger, а ответы на вопросы получаются в interactive agent Q&A session. — Это совместимо с текущим root baseline и не требует сразу вводить per-vacancy question files. — Initial implementation можно делать без миграции формата `questions/`.
- `2026-04-22 13:50` — Role-specific accepted artifacts не вводятся на acceptance stage. — Причина: role resumes должны строиться только downstream от согласованного `resumes/MASTER.md`. — `accepted/` на этом этапе остаётся master-only approved staging layer.
- `2026-04-22 15:53` — Initial implementation shape выбрана как hybrid: deterministic intake productized в runtime CLI, а interactive review остаётся agent-guided session, поддержанной helper-кодом и workflow docs. — Причина: owner описал review как ручной Q&A process, а текущая архитектура CLI ориентирована на deterministic runs, а не на встроенный REPL. — Это позволяет идти в код без ложной сложности и не смешивать operator conversation с runtime catalog.

## Progress log

- `2026-04-22 11:42` — Создан dedicated plan для review/acceptance workflow и закрыт baseline milestone M1 на основе owner-approved process. — Блокировка на уровне product sequencing снята, но interaction model acceptance session ещё не был выбран. — Status: `in_progress`.
- `2026-04-22 13:50` — M2 closed: interaction shape и file contract зафиксированы на основе owner confirmation и реального root baseline (`adoptions/questions/open.md`, existing `adoptions/`/`knowledge/roles/` layout). — Следующий шаг теперь чисто implementation-facing: разложить кодовые milestones и handoff. — Status: `in_progress`.
- `2026-04-22 15:53` — M3 closed: создан dedicated execution plan `2026-04-22-implement-adoptions-review-and-acceptance-workflow.md`, где intake и review support разложены на отдельные code-facing milestones с validation baseline и handoff в `rebuild-master`. — Planning ambiguity для этого workflow family снята; следующий шаг уже execution-oriented. — Status: `done`.

## Current state

- Current milestone: `done`
- Current status: `done`
- Next step: `Перейти к `2026-04-22-implement-adoptions-review-and-acceptance-workflow.md` и начать M1 по deterministic intake workflow.`
- Active blockers:
  - none
- Open questions:
  - none

## Completion summary

Поставлено:

- owner-approved sequencing для `inbox/`, `questions/`, `accepted/`, `knowledge/roles/`;
- session/file contract с отдельными deterministic intake и interactive review stages;
- dedicated execution plan `2026-04-22-implement-adoptions-review-and-acceptance-workflow.md`.

Провалидировано:

- обновлённые plan files читаются без двусмысленности;
- текущий root baseline соответствует принятому контракту: `adoptions/questions/open.md` существует, `adoptions/` уже содержит `inbox/`, `accepted/`, `questions/`, а `knowledge/roles/` пока остаётся mostly-empty shaping layer.

Follow-up:

- реализовать `M1` deterministic intake workflow в новом execution plan;
- затем добавить review support helpers, docs/tests alignment и handoff в `rebuild-master`.

Остаточные риски:

- interactive review остаётся agent-guided stage и потребует аккуратного helper/API дизайна, чтобы не превратиться в ad-hoc file editing без верифицируемого контракта.
