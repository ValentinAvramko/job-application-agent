# Rebuild Role Resume Workflow

- Title: `rebuild-role-resume workflow`
- Slug: `2026-04-22-rebuild-role-resume-workflow`
- Owner: `Codex`
- Created: `2026-04-22`
- Last updated: `2026-04-22 20:05`
- Overall status: `done`

## Objective

Подготовить и реализовать исполнимый workflow `rebuild-role-resume`, который обновляет выбранное ролевое резюме из уже согласованного `resumes/MASTER.md` так, чтобы:

- `resumes/MASTER.md` оставался единственным canonical facts source;
- downstream role resume синхронизировал approved permanent signals из `MASTER`, а не читал `adoptions/accepted/` напрямую;
- optional shaping layer из `knowledge/roles/<role>.md` могла влиять на результат без превращения workflow в full auto-editor всего документа.

## Background and context

После завершения `rebuild-master` очередь remaining workflows перешла к `rebuild-role-resume`.

Подтверждённый baseline на `2026-04-22`:

- `resumes/MASTER.md` существует и уже используется как canonical source для approved permanent signals через managed section `rebuild-master`;
- ролевые файлы `resumes/CIO.md`, `CTO.md`, `HoE.md`, `HoD.md`, `EM.md` существуют как производные resume artifacts;
- `knowledge/roles/` в реальном root пока почти пуст и содержит только `README.md`, но в планах закреплён как intended shaping layer для role-specific signals;
- `adoptions/accepted/README.md` исторически перечисляет role targets, но upstream plan `2026-04-22-adoptions-review-and-acceptance-workflow.md` явно закрепил, что role-specific accepted artifacts на этом этапе не вводятся;
- реальный root сейчас не содержит `adoptions/accepted/MASTER.md`, поэтому downstream workflow не должен зависеть от direct read этого слоя, а должен брать уже согласованный результат из `resumes/MASTER.md`.

Главный вывод для первой исполнимой версии:

- full narrative rewrite существующих role resumes слишком рискован без richer editorial contract и role-specific knowledge corpus;
- baseline implementation должен быть strictly deterministic и работать через отдельный managed block внутри `resumes/<role>.md`;
- input surface первой версии: `resumes/MASTER.md` как canonical source approved signals и optional `knowledge/roles/<role>.md` как shaping overlay.

## Scope

### In scope

- dedicated plan и baseline contract для `rebuild-role-resume`;
- explicit decision, что первая версия читает `MASTER`, а не `adoptions/accepted/<role>.md`;
- deterministic helper layer для managed role-resume section;
- workflow/CLI wiring, runtime report и memory trail;
- targeted tests, docs update и handoff в следующий workflow.

### Out of scope

- full narrative rewrite role resume через LLM или свободную text synthesis;
- пакетный rebuild всех ролей за один запуск;
- прямое чтение `adoptions/accepted/CIO.md`, `CTO.md`, `HoE.md`, `HoD.md`, `EM.md` в первой версии;
- изменение `knowledge/roles/` внутри workflow;
- обновление `resumes/versions/` или автоматическая публикация в git.

## Assumptions

- `resumes/MASTER.md` остаётся единственным factual source для downstream role resume rebuild.
- managed section `rebuild-master` в `MASTER` является единственным approved-signals input для role resume baseline.
- `knowledge/roles/<role>.md` optional: его отсутствие трактуется как empty shaping layer, а не как ошибка.
- первая версия rebuild работает только по одному `target_role` за запуск.
- runtime report должен жить в `agent_memory/runtime/rebuild-role-resume/`, а не рядом с `resumes/`.

## Risks and unknowns

- если workflow начнёт переписывать narrative sections без явного editorial contract, он может испортить уже существующие сильные role resumes;
- если downstream contract позже введёт role-specific accepted stores, baseline helper придётся расширять без breaking current semantics;
- так как `knowledge/roles/` почти пуст, первая версия будет полезнее как sync/update layer, чем как полноценный generator role-specific positioning;
- `adoptions/accepted/README.md` уже расходится с актуальным sequencing и может потребовать документационную синхронизацию.

## External touchpoints

- `C:\Users\avramko\OneDrive\Documents\Career\resumes\MASTER.md` — чтение / проверка — canonical input source;
- `C:\Users\avramko\OneDrive\Documents\Career\resumes\CIO.md`, `CTO.md`, `HoE.md`, `HoD.md`, `EM.md` — чтение / обновление / проверка — target role resumes;
- `C:\Users\avramko\OneDrive\Documents\Career\knowledge\roles\` — чтение / проверка — optional shaping input;
- `C:\Users\avramko\OneDrive\Documents\Career\agent_memory\runtime\` — обновление / проверка — runtime report и workflow trail;
- `C:\Users\avramko\OneDrive\Documents\Career\adoptions\accepted\README.md` — чтение / возможное обновление — sync historical README with current contract;
- `C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\plans\2026-04-22-rebuild-master-workflow.md` — чтение / проверка — upstream handoff contract.

## Milestones

### M1. Source-Of-Truth Baseline For Role Resume Rebuild

- Status: `done`
- Goal:
  - собрать baseline inventory по `MASTER`, existing role resumes и `knowledge/roles/`, чтобы зафиксировать безопасную input surface.
- Deliverables:
  - dedicated plan;
  - baseline inventory;
  - снятая двусмысленность по input source.
- Acceptance criteria:
  - plan явно фиксирует, что первая версия идёт downstream от `resumes/MASTER.md`;
  - в плане отражено текущее состояние root: role resumes существуют, `knowledge/roles/` почти пуст, `accepted/MASTER.md` может отсутствовать;
  - следующий шаг после baseline уже implementation-facing.
- Validation commands:
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\resumes`
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\knowledge\roles`
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\adoptions -Recurse`
- Notes / discoveries:
  - реальный root подтвердил, что `adoptions/accepted/MASTER.md` сейчас отсутствует, а значит downstream rebuild должен читать уже согласованный `MASTER`, а не ожидать direct accepted-store presence.

### M2. Deterministic Managed Projection For A Single Role Resume

- Status: `done`
- Goal:
  - реализовать helper layer, который синхронизирует managed block в `resumes/<role>.md` из approved signals внутри `MASTER` и optional role shaping signals.
- Deliverables:
  - helper module для load/render/write managed role block;
  - diff/report model;
  - targeted tests на empty shaping layer, insert/update/remove semantics и idempotency.
- Acceptance criteria:
  - helper layer не читает `adoptions/accepted/<role>.md` напрямую;
  - отсутствие `knowledge/roles/<role>.md` допустимо и не ломает rebuild;
  - workflow может повторно запускаться без повторных изменений, если inputs не поменялись.
- Validation commands:
  - `python -m unittest tests.test_rebuild_role_resume_helpers`
- Notes / discoveries:
  - managed block должен быть parseable и иметь explicit begin/end markers;
  - report должен отдельно показывать состояние master-derived signals и role-shaping signals.

### M3. Workflow, CLI And Runtime Wiring

- Status: `done`
- Goal:
  - добавить executable workflow `rebuild-role-resume` в runtime catalog с безопасными side effects на выбранный role resume и per-role runtime report.
- Deliverables:
  - workflow module и request contract с `target_role`;
  - wiring в `registry`, `cli`, `config` и runtime memory catalog;
  - workflow/CLI tests.
- Acceptance criteria:
  - `list-workflows` показывает `rebuild-role-resume`;
  - успешный run меняет только `resumes/<role>.md`, runtime report и workflow memory trail;
  - запуск без `target_role` или с неизвестной ролью даёт явную ошибку.
- Validation commands:
  - `python -m unittest tests.test_rebuild_role_resume_helpers tests.test_rebuild_role_resume_workflow tests.test_cli tests.test_memory_store`
  - `python run_agent.py --root ../.. list-workflows`
- Notes / discoveries:
  - runtime report должен быть per-role, чтобы прогоны разных ролей не затирали друг друга.

### M4. Docs Sync And Downstream Handoff

- Status: `done`
- Goal:
  - синхронизировать документацию, full validation baseline и handoff в следующий downstream workflow после `rebuild-role-resume`.
- Deliverables:
  - README update;
  - при необходимости sync `adoptions/accepted/README.md` с current contract;
  - full validation baseline;
  - explicit next step в master plan.
- Acceptance criteria:
  - docs объясняют, что baseline-версия обновляет managed role block, а не делает full rewrite;
  - relevant tests и CLI checks проходят;
  - master plan получает новый следующий шаг после завершения этого workflow.
- Validation commands:
  - `python -m unittest discover -s tests`
  - `python run_agent.py --root ../.. list-workflows`
  - `python run_agent.py --root ../.. show-memory`
- Notes / discoveries:
  - после закрытия этого workflow следующий remaining-workflow step нужно выбирать уже между `build-linkedin` и `export-resume-pdf`.

## Decision log

- `2026-04-22 19:55` — Для первой исполнимой версии input source закреплён как `resumes/MASTER.md` плюс optional `knowledge/roles/<role>.md`, а не direct read `adoptions/accepted/<role>.md`. — Причина: upstream acceptance contract явно оставил accepted-layer master-only, а реальный root сейчас не содержит `accepted/MASTER.md`. — Это делает baseline rebuild безопасным и согласованным с sequencing.
- `2026-04-22 19:55` — Full narrative rewrite role resume отложен вне первой версии; baseline работает через отдельный managed block внутри `resumes/<role>.md`. — Причина: current role artifacts уже содержат существенную ручную редактуру, а role knowledge corpus ещё почти пуст. — Это снижает риск destructive rewrite и позволяет внедрить workflow incremental-способом.
- `2026-04-22 20:05` — Runtime report для `rebuild-role-resume` закреплён как per-role artifact `agent_memory/runtime/rebuild-role-resume/<role>.md`. — Причина: прогоны разных ролей не должны затирать друг друга в общем `latest.md`. — Это делает workflow trace deterministic и review-friendly.

## Progress log

- `2026-04-22 19:55` — Создан dedicated plan и закрыт baseline milestone M1 по текущему состоянию `MASTER`, role resumes, `knowledge/roles/` и `adoptions/accepted/`. — Validation опиралась на реальный root inventory, содержимое `MASTER.md`, role resumes, `README.md` и upstream plans. — Status: `in_progress`.
- `2026-04-22 19:58` — M2 закрыт: добавлен helper module `application_agent.role_resume_rebuild` с deterministic managed block, parseable markers и per-signal diff report; tests `tests.test_rebuild_role_resume_helpers` проходят (`2 tests, OK`). — Helper не читает `adoptions/accepted/<role>.md` и допускает пустой `knowledge/roles/<role>.md`. — Status: `in_progress`.
- `2026-04-22 20:01` — M3 закрыт: добавлен executable workflow `rebuild-role-resume`, wiring в `registry`, `cli`, `config` и runtime memory catalog, а targeted suite `tests.test_rebuild_role_resume_helpers tests.test_rebuild_role_resume_workflow tests.test_cli tests.test_memory_store` проходит (`13 tests, OK`). — `python run_agent.py --root ../.. list-workflows` показывает новый workflow. — Status: `in_progress`.
- `2026-04-22 20:05` — M4 закрыт: `README.md` и `adoptions/accepted/README.md` синхронизированы с новым master-only acceptance contract, полный `python -m unittest discover -s tests` остаётся зелёным (`62 tests, OK`), `list-workflows` и `show-memory` выполняются успешно. — Dedicated plan завершён end-to-end и возвращает handoff в master sequencing. — Status: `done`.

## Current state

- Current milestone: `completed`
- Current status: `done`
- Next step: `Вернуться в master plan `2026-04-21-repository-reconstruction-and-backlog.md` и открыть next remaining-workflow plan для `build-linkedin`.`
- Active blockers:
  - none
- Open questions:
  - none

## Completion summary

Завершён executable workflow `rebuild-role-resume`: deterministic helper layer, runtime wiring и docs now согласованы вокруг безопасного managed-block contract для одного выбранного role resume.

Провалидировано:

- `python -m unittest tests.test_rebuild_role_resume_helpers tests.test_rebuild_role_resume_workflow tests.test_cli tests.test_memory_store` -> `OK`
- `python -m unittest discover -s tests` -> `OK (62 tests)`
- `python run_agent.py --root ../.. list-workflows`
- `python run_agent.py --root ../.. show-memory`

Follow-up вне этого dedicated plan остался один: открыть next remaining-workflow plan для `build-linkedin`, который теперь может читать stabilised `MASTER` и уже обновлённую role-resume family без direct dependency на accepted stores.

Затронутые root-level artifacts в рамках этого plan: обновлён `adoptions/accepted/README.md` как документационный handoff; реальные `resumes/*.md` в корневом workspace не мутировались во время validation.
