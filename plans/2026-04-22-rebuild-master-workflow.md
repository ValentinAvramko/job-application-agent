# Rebuild Master Workflow

- Title: `rebuild-master workflow`
- Slug: `2026-04-22-rebuild-master-workflow`
- Owner: `Codex`
- Created: `2026-04-22`
- Last updated: `2026-04-22 18:36`
- Overall status: `in_progress`

## Objective

Подготовить и реализовать исполнимый workflow `rebuild-master`, который обновляет `resumes/MASTER.md` из подтверждённых постоянных сигналов так, чтобы:

- `resumes/MASTER.md` оставался единственным durable facts source по кандидату;
- approved permanent signals не терялись между `adoptions/accepted/MASTER.md`, `resumes/MASTER.md` и downstream workflow family;
- будущие `rebuild-role-resume` и `build-linkedin` читали уже согласованный `MASTER`, а не сырой vacancy corpus.

## Background and context

После закрытия `prepare-screening` и upstream workflow family `analyze-vacancy -> intake-adoptions -> agent-guided review`, следующим downstream этапом остаётся `rebuild-master`.

Подтверждённые факты на `2026-04-22`:

- `resumes/MASTER.md` существует и остаётся canonical resume source.
- `adoptions/accepted/MASTER.md` признан canonical approved staging layer для permanent signals, но файл может ещё физически отсутствовать и тогда должен читаться как empty current-state store.
- `knowledge/roles/` существует как downstream shaping layer, но не является direct input source для `rebuild-master`.
- `resumes/versions/` уже существует как historical/manual-only storage и не должен автоматически мутироваться baseline-версией workflow.
- `resumes/MASTER.md` уже имеет стабильную markdown-структуру (`О себе`, `Ключевые компетенции`, `Технологии и инструменты`, `Опыт работы`, `Образование`, `Языки`, `Рекомендации`), но accepted signals сейчас не содержат section-level mapping.

Главный вывод для первой исполнимой версии:

- deterministic baseline не должен пытаться переписывать existing profile/experience prose;
- approved signals нужно проецировать в отдельный managed section внутри `resumes/MASTER.md`;
- direct rescanning `vacancies/`, `adoptions/inbox/` и `questions/` не нужен, потому что upstream review уже дистиллировал vacancy corpus в `adoptions/accepted/MASTER.md`.

## Scope

### In scope

- current-state inventory для `resumes/MASTER.md`, `adoptions/accepted/`, `knowledge/roles/` и runtime trail;
- contract decisions для accepted signals, managed section и change report;
- implementation-ready decomposition для `rebuild-master`;
- deterministic helper layer для managed-section rebuild;
- workflow/CLI wiring и runtime artifact generation;
- docs and downstream handoff после реализации.

### Out of scope

- full narrative rewrite `resumes/MASTER.md` через LLM или ad-hoc text synthesis в первой версии;
- автоматическое обновление `resumes/versions/`;
- реализация `rebuild-role-resume`, `build-linkedin` или `export-resume-pdf`;
- direct merge из raw vacancy drafts, `adoptions/inbox/` или `questions/open.md`;
- изменение `knowledge/roles/` внутри `rebuild-master`.

## Assumptions

- `resumes/MASTER.md` остаётся единственным durable factual source для профиля кандидата.
- `adoptions/accepted/MASTER.md` хранит current-state approved signals, а не history log.
- baseline-версия `rebuild-master` обрабатывает весь current-state accepted-signal set за один прогон без batching policy.
- baseline-версия пишет change report в `agent_memory/runtime/rebuild-master/`, а не рядом с `resumes/MASTER.md`.
- downstream workflow family сможет читать managed section в `resumes/MASTER.md` до того, как появится более сложный editorial merge.

## Risks and unknowns

- если merge strategy станет слишком агрессивной, workflow превратится в опасный auto-editor для `MASTER.md`;
- если accepted-signal contract изменится без синхронизации с `rebuild-master`, появится новый contract drift;
- dedicated managed section безопасен для baseline, но позже может потребоваться отдельный editorial pass, чтобы естественно встроить approved signals в narrative sections;
- остаётся product question для будущих версий: нужен ли когда-нибудь richer signal schema с section/priority mapping.

## External touchpoints

- `C:\Users\avramko\OneDrive\Documents\Career\resumes\MASTER.md` — чтение / обновление / проверка — canonical target;
- `C:\Users\avramko\OneDrive\Documents\Career\adoptions\accepted\MASTER.md` — чтение / проверка — canonical approved input store;
- `C:\Users\avramko\OneDrive\Documents\Career\agent_memory\runtime\` — обновление / проверка — runtime report и trail;
- `C:\Users\avramko\OneDrive\Documents\Career\knowledge\roles\` — чтение / проверка — downstream-only non-input layer;
- `C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\plans\2026-04-22-implement-adoptions-review-and-acceptance-workflow.md` — чтение / проверка — upstream handoff contract.

## Milestones

### M1. Source-Of-Truth Baseline For Master Rebuild

- Status: `done`
- Goal:
  - собрать baseline inventory по `MASTER`, `accepted`, `knowledge` и зафиксировать главный contract gap.
- Deliverables:
  - dedicated plan;
  - baseline inventory;
  - явный blocker по permanent-signal destination.
- Acceptance criteria:
  - plan описывает существующие слои и нехватку contract clarity для безопасного `rebuild-master`;
  - следующий шаг после baseline сводится к одному contract decision.
- Validation commands:
  - `Test-Path C:\Users\avramko\OneDrive\Documents\Career\resumes\MASTER.md`
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\adoptions -Recurse`
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\knowledge -Recurse`
- Notes / discoveries:
  - baseline показал наличие intended stores, но не дал safe answer, кто является canonical input для merge в `MASTER`.

### M2. Permanent Signal Contract Decision

- Status: `done`
- Goal:
  - закрепить, где живут accepted permanent signals и как они переходят в `resumes/MASTER.md`.
- Deliverables:
  - owner-level destination/store decision;
  - обновлённый workflow contract для `rebuild-master`;
  - снятый blocker на implementation planning.
- Acceptance criteria:
  - однозначно определён input source для `rebuild-master`;
  - разделены роли `adoptions/accepted/`, `knowledge/roles/` и `resumes/MASTER.md`;
  - решение достаточно конкретно для перехода к implementation milestones.
- Validation commands:
  - `Get-Content -Raw plans\2026-04-22-rebuild-master-workflow.md`
- Notes / discoveries:
  - canonical approved staging layer закреплён как `adoptions/accepted/MASTER.md`;
  - `knowledge/roles/` не является direct input для `rebuild-master`;
  - role resumes остаются строго downstream от обновлённого `MASTER`.

### M3. Implementation-Ready Rebuild-Master Plan

- Status: `done`
- Goal:
  - разложить `rebuild-master` на исполнимые code-facing milestones.
- Deliverables:
  - updated plan с milestones M4-M6;
  - зафиксированная merge strategy для baseline implementation;
  - handoff в execution cycle.
- Acceptance criteria:
  - следующий инженер может начать реализацию `rebuild-master` только по этому plan;
  - в плане больше нет product ambiguity по report location, batching и baseline merge surface.
- Validation commands:
  - `Get-Content -Raw plans\2026-04-22-rebuild-master-workflow.md`
- Notes / discoveries:
  - baseline implementation будет поддерживать dedicated managed section внутри `resumes/MASTER.md`;
  - change report живёт в `agent_memory/runtime/rebuild-master/`;
  - batching в первой версии не нужен: input already current-state and full-set.

### M4. Managed Signals Projection For MASTER

- Status: `done`
- Goal:
  - реализовать deterministic helper layer, который читает `resumes/MASTER.md` и `adoptions/accepted/MASTER.md`, синхронизирует managed approved-signals section и считает change set.
- Deliverables:
  - helper module для load/render/write managed section;
  - change-set model и renderer для runtime report;
  - targeted tests на empty store, no-op и idempotency semantics.
- Acceptance criteria:
  - отсутствие `adoptions/accepted/MASTER.md` обрабатывается как valid empty input;
  - повторный rebuild с тем же accepted set не меняет `resumes/MASTER.md`;
  - helper layer не трогает `knowledge/roles/`, role resumes, `adoptions/inbox/` и `adoptions/questions/`.
- Validation commands:
  - `python -m unittest tests.test_rebuild_master_helpers`
- Notes / discoveries:
  - managed block должен иметь явные begin/end markers;
  - report должен явно перечислять `added`, `updated`, `removed`, `unchanged` signals и общий outcome `changed` / `no-op`;
  - helper implementation оформлен отдельным модулем `application_agent.master_rebuild`, чтобы M5 обернул уже готовую merge/report logic без дублирования.

### M5. Workflow, CLI And Runtime Wiring

- Status: `done`
- Goal:
  - добавить executable workflow `rebuild-master` в runtime catalog с детерминированными side effects на `resumes/MASTER.md` и runtime report.
- Deliverables:
  - workflow module и request/result contract;
  - wiring в `registry`, `cli`, `config`;
  - runtime artifact output under `agent_memory/runtime/rebuild-master/`;
  - workflow/CLI tests.
- Acceptance criteria:
  - `python run_agent.py --root ../.. list-workflows` показывает `rebuild-master`;
  - successful run обновляет только `resumes/MASTER.md`, runtime report artifact и workflow memory trail;
  - workflow не мутирует `resumes/CIO.md`, `resumes/CTO.md`, `resumes/HoE.md`, `resumes/HoD.md`, `resumes/EM.md`, `knowledge/roles/`, `adoptions/questions/open.md`.
- Validation commands:
  - `python -m unittest tests.test_rebuild_master_helpers tests.test_rebuild_master_workflow tests.test_cli tests.test_memory_store`
  - `python run_agent.py --root ../.. list-workflows`
- Notes / discoveries:
  - request в первой версии должен быть минимальным: без `vacancy_id`, потому что input source full-set;
  - runtime report path лучше держать deterministic, например `agent_memory/runtime/rebuild-master/latest.md`.

### M6. Integration Validation And Downstream Resume Handoff

- Status: `planned`
- Goal:
  - синхронизировать docs, full validation baseline и downstream handoff после реализации `rebuild-master`.
- Deliverables:
  - README / runtime docs updates;
  - full validation baseline;
  - updated downstream references для `rebuild-role-resume`.
- Acceptance criteria:
  - docs явно описывают managed-section strategy и runtime report;
  - full relevant tests проходят;
  - downstream workflow family может читать `MASTER` без ambiguity, где живут approved permanent signals.
- Validation commands:
  - `python -m unittest discover -s tests`
  - `python run_agent.py --root ../.. list-workflows`
  - `python run_agent.py --root ../.. show-memory`
- Notes / discoveries:
  - этот milestone закрывает не только `rebuild-master`, но и снимает ambiguity для следующего workflow family.

## Decision log

- `2026-04-22 11:18` — Следующим workflow после `prepare-screening` выбран `rebuild-master`, но без отдельного plan стартовать реализацию нельзя. — Причина: backlog уже фиксировал dependency gate по permanent-signal store. — Сначала открыт dedicated planning artifact.
- `2026-04-22 11:42` — Принят owner-level contract: approved permanent signals сначала живут в `adoptions/accepted/MASTER.md`, а попадание в `resumes/MASTER.md` является отдельным downstream шагом. — Это жёстко разделяет review/approval layer и canonical resume mutation layer. — `rebuild-master` больше не должен напрямую зависеть от raw vacancy drafts.
- `2026-04-22 13:50` — Upstream review flow закреплён как `intake -> questions -> accepted`, отдельно от `rebuild-master`. — Это исключает смешение review logic и master mutation. — `rebuild-master` становится чистым downstream workflow.
- `2026-04-22 17:21` — Upstream execution plan завершён до стабильного contract state. — Это снимает sequencing blocker. — `rebuild-master` может переходить в собственные implementation milestones.
- `2026-04-22 18:02` — Для first executable version выбран deterministic managed-section contract внутри `resumes/MASTER.md`, а не попытка full narrative rewrite. — Причина: current accepted store не несёт section mapping, и безопасный baseline merge должен быть строго deterministic. — Это делает M4/M5 исполнимыми без нового product drift.
- `2026-04-22 18:02` — Change report вынесен в `agent_memory/runtime/rebuild-master/`, а accepted signals обрабатываются full-set без batching. — Причина: report не должен становиться новым canonical resume artifact, а current-state semantics accepted store уже делают slicing ненужным в baseline. — Это закрывает последние open questions.

## Progress log

- `2026-04-22 11:18` — Создан dedicated plan и закрыт baseline milestone M1 по текущему состоянию `resumes/MASTER.md`, `adoptions/` и `knowledge/`. — Status: `blocked`.
- `2026-04-22 11:42` — M2 contract decision закрыт: canonical approved staging layer — `adoptions/accepted/MASTER.md`, а `knowledge/roles/` не является direct input для `rebuild-master`. — Status: `blocked`.
- `2026-04-22 13:50` — Upstream plan review/acceptance снял session-shape ambiguity; `rebuild-master` остаётся blocked только на upstream completion. — Status: `blocked`.
- `2026-04-22 17:21` — Upstream workflow family закрыт до стабильного `inbox/questions/accepted` contract и handoff зафиксирован в public/runtime docs. — `rebuild-master` больше не blocked. — Status: `in_progress`.
- `2026-04-22 18:02` — M3 planning milestone закрыт: plan получил explicit milestones M4-M6, managed-section merge contract, runtime report location и baseline no-batching semantics. — Следующий шаг уже чисто implementation-oriented. — Status: `in_progress`.
- `2026-04-22 18:18` — M4 helper milestone закрыт: добавлен модуль `application_agent.master_rebuild` с deterministic managed-section projection, begin/end markers и runtime report generation; новые tests `tests.test_rebuild_master_helpers` закрывают empty-store, insert+idempotency и update/remove diff semantics. — Validation: `python -m unittest tests.test_rebuild_master_helpers` -> `OK`. — Status: `in_progress`.
- `2026-04-22 18:36` — M5 wiring milestone закрыт: добавлен executable workflow `rebuild-master`, он подключен в `registry`, `cli` и runtime workflow catalog, а tests `tests.test_rebuild_master_workflow`, `tests.test_cli`, `tests.test_memory_store` зафиксировали deterministic side effects только на `resumes/MASTER.md`, runtime report и workflow memory trail. — Validation: `python -m unittest tests.test_rebuild_master_helpers tests.test_rebuild_master_workflow tests.test_cli tests.test_memory_store` -> `OK`; `python run_agent.py --root ../.. list-workflows` -> shows `rebuild-master`. — Status: `in_progress`.

## Current state

- Current milestone: `M6`
- Current status: `in_progress`
- Next step: `Обновить README/runtime docs по strategy managed section и прогнать full validation baseline для закрытия M6.`
- Active blockers:
  - none
- Open questions:
  - none

## Completion summary

Заполняется после завершения всех milestones. На текущем этапе baseline и product contract уже зафиксированы, upstream review/acceptance workflow family доведён до стабильного execution contract, а remaining work для `rebuild-master` теперь состоит из helper implementation, workflow wiring и integration validation.
