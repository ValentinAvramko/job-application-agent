# Implement Adoptions Review And Acceptance Workflow

- Title: `implement adoptions review and acceptance workflow`
- Slug: `2026-04-22-implement-adoptions-review-and-acceptance-workflow`
- Owner: `Codex`
- Created: `2026-04-22`
- Last updated: `2026-04-22 17:04`
- Overall status: `in_progress`

## Objective

Реализовать operational workflow family для `adoptions/inbox/`, `adoptions/questions/`, `adoptions/accepted/` так, чтобы:

- deterministic intake step переводил vacancy-local `adoptions.md` в root review layers без ручного копирования;
- interactive review оставалась отдельной agent-guided stage, но опиралась на кодовые helper-контракты, а не на произвольное редактирование файлов;
- approved permanent signals оказывались в `adoptions/accepted/MASTER.md` в форме, пригодной для downstream `rebuild-master`;
- runtime/docs/tests явно разделяли generated drafts, unresolved questions и approved signals.

## Background and context

План `2026-04-22-adoptions-review-and-acceptance-workflow.md` уже закрыл product contract:

- `vacancies/<id>/adoptions.md` — generated draft;
- `adoptions/inbox/<vacancy_id>.md` — deterministic review input;
- `adoptions/questions/open.md` — shared ledger для unresolved/answered items;
- `adoptions/accepted/MASTER.md` — canonical approved current-state set of permanent signals;
- `knowledge/roles/` — shaping layer, которая может обновляться в review session;
- `resumes/MASTER.md` обновляется только downstream отдельным process.

При этом текущий код в `tooling/application-agent` умеет:

- bootstrap-ить нужные root directories через `WorkspaceLayout.bootstrap()`;
- работать с registry/CLI для deterministic workflows (`ingest-vacancy`, `analyze-vacancy`, `prepare-screening`);
- генерировать vacancy-local `adoptions.md` через `analyze-vacancy`.

Что ещё отсутствует:

- runtime workflow, который переносит vacancy-local adoption draft в root review layer;
- structured helper layer для question ledger и accepted master;
- operator/runtime docs и тесты, которые делают review process воспроизводимым;
- явный handoff от upstream review family к downstream `rebuild-master`.

## Scope

### In scope

- новый deterministic intake workflow в runtime CLI/registry;
- helper-контракты для `adoptions/questions/open.md` и `adoptions/accepted/MASTER.md`;
- agent-guided review support surface, пригодная для сессии Q&A и применения approved updates;
- tests, docs и runtime-memory alignment для нового sequencing;
- plan/docs handoff в `rebuild-master`.

### Out of scope

- прямое редактирование `resumes/MASTER.md`;
- реализация самого `rebuild-master`;
- автоматическая генерация role resumes;
- full standalone interactive CLI REPL для review session в первой версии;
- миграция historical `vacancies/*/adoptions.md` без отдельного owner request.

## Assumptions

- initial runtime catalog получит deterministic intake workflow; interactive review в первой версии останется agent-guided execution stage;
- `adoptions/questions/open.md` можно оставить одним shared markdown ledger, если helper layer нормализует записи и статусы;
- `adoptions/accepted/MASTER.md` должен обновляться идемпотентно и не превращаться в append-only log;
- runtime memory достаточно использовать для trail по intake workflow; review session может опираться на file/state contract и workflow docs без отдельного catalog entry на первом шаге;
- unit-test baseline остаётся на `unittest`.

## Risks and unknowns

- если helper layer для `questions` и `accepted` окажется слишком слабым, review session снова превратится в неаудируемое ручное редактирование;
- если intake workflow не будет идемпотентным, повторный прогон начнёт плодить дубликаты в `inbox/` и `questions/open.md`;
- если docs/runtime memory будут описывать review как автоматический workflow, а фактически это agent-guided stage, снова появится contract drift;
- последующая productization review stage в отдельный CLI command может потребовать рефакторинга, но это допустимый future step.

## External touchpoints

- `C:\Users\avramko\OneDrive\Documents\Career\vacancies\` — чтение / проверка — vacancy-local `adoptions.md` input;
- `C:\Users\avramko\OneDrive\Documents\Career\adoptions\inbox\` — обновление / проверка — intake destination;
- `C:\Users\avramko\OneDrive\Documents\Career\adoptions\questions\open.md` — обновление / проверка — shared question ledger;
- `C:\Users\avramko\OneDrive\Documents\Career\adoptions\accepted\MASTER.md` — обновление / проверка — approved permanent signals;
- `C:\Users\avramko\OneDrive\Documents\Career\knowledge\roles\` — обновление / проверка — optional role-shaping edits during review;
- `C:\Users\avramko\OneDrive\Documents\Career\agent_memory\workflows\` — обновление / проверка — operator/runtime workflow docs;
- `C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\plans\2026-04-22-rebuild-master-workflow.md` — чтение / проверка — downstream handoff contract.

## Milestones

### M1. Deterministic Intake Workflow

- Status: `done`
- Goal:
  - добавить reproducible runtime step, который переводит vacancy-local `adoptions.md` в `adoptions/inbox/` и `adoptions/questions/open.md`.
- Deliverables:
  - новый workflow и request/result contract;
  - CLI/registry wiring;
  - deterministic rendering/update rules для `inbox/<vacancy_id>.md` и initial question ledger entries;
  - targeted tests.
- Acceptance criteria:
  - можно запустить intake для конкретной вакансии без ручного копирования файлов;
  - повторный запуск не создаёт неуправляемые дубликаты;
  - workflow не мутирует `accepted/MASTER.md`, `knowledge/roles/` и `resumes/MASTER.md`.
- Validation commands:
  - `python -m unittest tests.test_adoptions_intake_workflow tests.test_cli tests.test_memory_store`
  - `python run_agent.py --root ../.. list-workflows`
- Notes / discoveries:
  - final CLI name выбран как `intake-adoptions`: он остаётся явно stage-specific и не выдаёт intake за review/acceptance;
  - vacancy-local `adoptions.md` оказался не копией будущего inbox-формата, а source draft с секциями, поэтому intake нормализует его в табличный `inbox` contract и синхронизирует только `questions/open.md` pending rows для текущей вакансии.

### M2. Review Helper Layer For Questions And Accepted Signals

- Status: `done`
- Goal:
  - сделать review session опирающейся на структурированные helper-операции, а не на ad-hoc markdown editing.
- Deliverables:
  - helper-модули для чтения/обновления `adoptions/questions/open.md` и `adoptions/accepted/MASTER.md`;
  - normal form для question status/answer state;
  - tests на merge/idempotency/update semantics.
- Acceptance criteria:
  - agent-guided review может использовать кодовые helper-операции для применения approved updates;
  - shared ledger `questions/open.md` поддерживает различие между pending, answered и closed items;
  - `accepted/MASTER.md` обновляется как current-state layer, а не как append-only журнал.
- Validation commands:
  - `python -m unittest tests.test_adoptions_review_state`
- Notes / discoveries:
  - helper layer должен быть независим от того, станет ли review позже отдельным CLI command;
  - для `questions/open.md` зафиксирован трёхсостояний формат `Pending / Answered / Closed`, при этом loader остаётся backward-compatible с legacy pending-only файлом;
  - для `accepted/MASTER.md` выбран markdown current-state table `Signal / Target / Source Vacancy / Rationale / Updated At`, чтобы downstream merge читал актуальный набор сигналов, а не history log.

### M3. Agent-Guided Review Support Surface

- Status: `done`
- Goal:
  - оформить interactive review как воспроизводимую agent-guided stage с явным workflow contract.
- Deliverables:
  - workflow doc/runbook для review session;
  - code path или helper entrypoints, которые собирают pending context и применяют approved updates;
  - test-backed examples для typical review cycle.
- Acceptance criteria:
  - агент может провести Q&A session, обновить `questions/open.md`, `accepted/MASTER.md` и при необходимости `knowledge/roles/` по явному контракту;
  - docs не обещают standalone interactive CLI REPL, если его нет;
  - runtime/operator contract чётко разделяет intake и review.
- Validation commands:
  - `python -m unittest tests.test_adoptions_review_state tests.test_adoptions_review_session`
  - `Get-Content -Raw ..\..\agent_memory\workflows\adoptions-review.md`
- Notes / discoveries:
  - review остаётся operator-driven stage, поэтому docs и helper APIs важнее, чем попытка эмулировать чат внутри CLI;
  - минимальный code path оформлен как `load_review_session_context(...)` + `apply_review_decision(...)` без ввода отдельной CLI-команды, чтобы не смешивать review conversation и deterministic runtime catalog.

### M4. Integration Validation And Rebuild-Master Handoff

- Status: `in_progress`
- Goal:
  - синхронизировать docs/tests/runtime memory и передать стабильный upstream contract в `rebuild-master`.
- Deliverables:
  - README / workflow docs updates;
  - full validation baseline;
  - updated `2026-04-22-rebuild-master-workflow.md` с новым blocker state.
- Acceptance criteria:
  - новый sequencing отражён в public docs и workflow docs;
  - full relevant tests проходят;
  - `rebuild-master` blocked уже только на upstream execution completion, а не на source-of-truth ambiguity.
- Validation commands:
  - `python -m unittest discover -s tests`
  - `python run_agent.py --root ../.. list-workflows`
  - `python run_agent.py --root ../.. show-memory`
- Notes / discoveries:
  - этот milestone завершает upstream workflow family как input contract для `rebuild-master`.

## Decision log

- `2026-04-22 15:53` — Initial implementation split выбран как `runtime intake` + `agent-guided review support`, а не как два fully productized CLI workflows. — Причина: user описал review как ручную Q&A session, а текущая архитектура инструмента уже хорошо поддерживает deterministic stages и плохо подходит для встроенного conversational REPL. — Это уменьшает implementation risk и не мешает позже productize review stage отдельно.
- `2026-04-22 16:33` — Для deterministic intake выбран CLI command `intake-adoptions`, а не review/acceptance-oriented имя. — Причина: runtime step делает только normalizing handoff `vacancies/<id>/adoptions.md -> adoptions/inbox/<vacancy_id>.md + adoptions/questions/open.md` и не должен создавать ложное впечатление, что он уже решает review или acceptance. — Это удерживает контракт M1 узким и совместимым с последующим M2 helper layer.
- `2026-04-22 16:58` — Review helper state зафиксирован в двух markdown contracts: `questions/open.md` с секциями `Pending / Answered / Closed` и `accepted/MASTER.md` как current-state table approved signals. — Причина: этого достаточно для agent-guided review без отдельного CLI REPL и без перехода к append-only history log. — Это делает M3 про orchestration поверх стабильных helper APIs, а не про повторное проектирование file format.
- `2026-04-22 17:04` — Agent-guided review surface оставлен вне workflow registry и оформлен как module-level API плюс workflow doc. — Причина: review по-прежнему driven by operator conversation, а не deterministic command invocation. — Это удерживает каталог runtime workflows чистым и даёт downstream `rebuild-master` уже стабильный upstream contract.

## Progress log

- `2026-04-22 15:53` — Создан execution plan на основе завершённого planning plan `2026-04-22-adoptions-review-and-acceptance-workflow.md`. — Следующий шаг уже не про product ambiguity, а про код: начать deterministic intake workflow. — Status: `in_progress`.
- `2026-04-22 16:33` — M1 завершён: добавлен workflow `intake-adoptions`, он зарегистрирован в runtime CLI/registry/catalog, детерминированно рендерит `adoptions/inbox/<vacancy_id>.md`, синхронизирует initial unresolved items в `adoptions/questions/open.md` и не трогает `adoptions/accepted/MASTER.md`, `knowledge/roles/` или `resumes/MASTER.md`. — Validation: `python -m unittest tests.test_adoptions_intake_workflow tests.test_cli tests.test_memory_store` -> `OK`, `python run_agent.py --root ../.. list-workflows` показывает `intake-adoptions`. — Status: `in_progress`.
- `2026-04-22 16:58` — M2 завершён: добавлен reusable helper module `review_state.py`, intake переведён на общий question-ledger API, а новые tests `tests.test_adoptions_review_state` фиксируют merge/idempotency/update semantics для question statuses и accepted current-state store. — Validation: `python -m unittest tests.test_adoptions_review_state` -> `OK`, повторная проверка `python -m unittest tests.test_adoptions_intake_workflow tests.test_cli tests.test_memory_store` -> `OK`. — Status: `in_progress`.
- `2026-04-22 17:04` — M3 завершён: добавлен review support module `adoptions_review.py`, тесты `tests.test_adoptions_review_session` покрывают загрузку pending context и применение approved updates, а `agent_memory/workflows/adoptions-review.md` фиксирует operator-facing contract без standalone CLI REPL. — Validation: `python -m unittest tests.test_adoptions_review_state tests.test_adoptions_review_session` -> `OK`, `Get-Content ..\..\agent_memory\workflows\adoptions-review.md`, повторная проверка `python -m unittest tests.test_adoptions_intake_workflow tests.test_cli tests.test_memory_store` -> `OK`. — Status: `in_progress`.

## Current state

- Current milestone: `M4`
- Current status: `in_progress`
- Next step: `Синхронизировать integration/docs/handoff слой: обновить public docs, зафиксировать upstream contract для `rebuild-master` и прогнать full validation baseline.`
- Active blockers:
  - none
- Open questions:
  - none

## Completion summary

Заполняется после завершения всех milestones.
