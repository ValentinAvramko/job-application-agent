# Rebuild Master Workflow

- Title: `rebuild-master workflow`
- Slug: `2026-04-22-rebuild-master-workflow`
- Owner: `Codex`
- Created: `2026-04-22`
- Last updated: `2026-04-22 11:42`
- Overall status: `blocked`

## Objective

Подготовить исполнимый workflow `rebuild-master`, который обновляет `resumes/MASTER.md` из подтверждённых постоянных сигналов и накопленного vacancy corpus так, чтобы:

- был один явный source-of-truth для durable candidate facts;
- permanent adoptions не терялись между vacancy-local артефактами, review layer и role-specific knowledge;
- будущие `rebuild-role-resume` и `build-linkedin` опирались на стабилизированный `MASTER`, а не на разрозненные заметки.

## Background and context

После закрытия `prepare-screening` master plan перешёл к следующему remaining workflow по очереди из safety backlog: `rebuild-master`.

Подтверждённые факты на `2026-04-22`:

- `resumes/MASTER.md` существует и остаётся canonical resume source;
- `adoptions/` уже имеет заготовленную структуру `inbox/`, `accepted/`, `questions/`;
- `adoptions/accepted/README.md` рекомендует целевые файлы `MASTER.md`, `CIO.md`, `CTO.md`, `HoE.md`, `HoD.md`, `EM.md`, но реальный merge contract пока не описан;
- `knowledge/roles/` существует как intended normalized layer, но сейчас содержит только `README.md`, без живых role signal files;
- root-normalization workstream закрепил `adoptions/` как long-lived review layer, а `vacancies/<id>/adoptions.md` — как generated staging artifact;
- safety backlog уже зафиксировал, что `rebuild-master` нельзя начинать без explicit permanent-signal store и accepted-signal destination.

Главная неопределённость теперь сместилась из product contract в sequencing:

- accepted permanent signals уже закреплены как approved staging items в `adoptions/accepted/MASTER.md`;
- `resumes/MASTER.md` должен обновляться отдельным, более редким шагом;
- `knowledge/roles/` пересматривается в review-процессе, но не является canonical input для `rebuild-master`;
- перед `rebuild-master` появился отдельный upstream process: vacancy-specific proposals должны сначала пройти через `inbox/` и `questions/`, затем превратиться в `accepted/`.

## Scope

### In scope

- current-state inventory для `resumes/MASTER.md`, `adoptions/accepted/`, `adoptions/inbox/`, `knowledge/roles/`;
- contract decisions для permanent signals, accepted adoptions и destination layer;
- определение минимального input/output contract будущего `rebuild-master` workflow;
- создание implementation-ready plan/handoff для последующей кодовой реализации.

### Out of scope

- непосредственное редактирование `resumes/MASTER.md`;
- реализация `rebuild-master` в коде;
- реализация `rebuild-role-resume`, `build-linkedin` или `export-resume-pdf`;
- массовая миграция historical vacancy-local `adoptions.md` без отдельного решения по policy.

## Assumptions

- `resumes/MASTER.md` должен оставаться единственным durable factual source для профиля кандидата;
- `adoptions/accepted/MASTER.md` является canonical approved staging layer для future merge в `resumes/MASTER.md`;
- `knowledge/roles/` обновляется в review-процессе и нужен downstream для role resume rebuild, но не как direct source-of-truth для `rebuild-master`;
- роль-резюме всегда должны строиться только после обновлённого и согласованного `resumes/MASTER.md`.

## Risks and unknowns

- если merge policy окажется слишком жёсткой, workflow превратится в опасный auto-editor для `MASTER.md`;
- если upstream review process не будет формализован отдельно, `rebuild-master` снова начнёт смешивать raw vacancy drafts и approved signals;
- если не развести cadence между `accepted/ -> MASTER` и `MASTER -> role resumes`, появится drift между canonical master и ролевыми версиями.

## External touchpoints

- `C:\Users\avramko\OneDrive\Documents\Career\resumes\MASTER.md` — чтение / проверка — главный target/source-of-truth для master resume;
- `C:\Users\avramko\OneDrive\Documents\Career\adoptions\` — чтение / проверка — review layers `inbox/`, `accepted/`, `questions/`;
- `C:\Users\avramko\OneDrive\Documents\Career\knowledge\roles\` — чтение / проверка — intended normalized role signal store;
- `C:\Users\avramko\OneDrive\Documents\Career\agent_memory\runtime\` — чтение / проверка — processed vacancy history и potential inputs для signal distillation;
- `C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\plans\2026-04-21-workflow-contract-alignment-and-safety.md` — чтение / проверка — ordered backlog и dependency gate;
- `C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\plans\2026-04-21-root-artifacts-and-output-normalization.md` — чтение / проверка — canonical roles для `resumes/`, `adoptions/` и `knowledge/`.

## Milestones

### M1. Source-Of-Truth Baseline For Master Rebuild

- Status: `done`
- Goal:
  - собрать фактическую картину по `MASTER`, `adoptions/accepted`, `knowledge/roles` и зафиксировать главный contract gap перед реализацией.
- Deliverables:
  - этот plan;
  - baseline inventory по relevant root stores;
  - зафиксированный blocker по permanent-signal destination.
- Acceptance criteria:
  - plan описывает, какие слои уже существуют и чего именно не хватает для безопасного `rebuild-master`;
  - следующий шаг после baseline сводится к одному конкретному contract decision.
- Validation commands:
  - `Test-Path C:\Users\avramko\OneDrive\Documents\Career\resumes\MASTER.md`
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\adoptions -Recurse`
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\knowledge -Recurse`
- Notes / discoveries:
  - `adoptions/accepted/` и `knowledge/roles/` уже существуют как контейнеры, но не имеют зафиксированного runtime contract;
  - это делает текущую задачу сначала product/contract clarification, а не implementation-first workflow.

### M2. Permanent Signal Contract Decision

- Status: `done`
- Goal:
  - закрепить, где живут accepted permanent signals и как они переходят в `resumes/MASTER.md`.
- Deliverables:
  - decision record по destination/store split;
  - обновлённый workflow contract для `rebuild-master`;
  - снятый blocker на implementation planning.
- Acceptance criteria:
  - однозначно определено, что является input source для `rebuild-master`;
  - разделены роли `adoptions/accepted/`, `knowledge/roles/` и `resumes/MASTER.md`;
  - решение достаточно конкретно, чтобы перейти к implementation milestones без нового product drift.
- Validation commands:
  - `Get-Content -Raw plans\2026-04-22-rebuild-master-workflow.md`
- Notes / discoveries:
  - Решение зафиксировано:
    - raw vacancy-specific proposals сначала живут в `adoptions/inbox/<vacancy_id>.md`;
    - unresolved questions накапливаются параллельно в `adoptions/questions/`;
    - review/acceptance process формирует `adoptions/accepted/MASTER.md` и при необходимости обновляет `knowledge/roles/`;
    - `rebuild-master` читает approved signals из `adoptions/accepted/MASTER.md` и отдельно редактирует `resumes/MASTER.md`;
    - role resumes обновляются только отдельным downstream process после согласованного `MASTER`.

### M3. Implementation-Ready Rebuild-Master Plan

- Status: `planned`
- Goal:
  - после contract decision разбить `rebuild-master` на исполнимые implementation milestones.
- Deliverables:
  - обновлённый plan с code-facing milestones;
  - validation baseline для будущей реализации;
  - handoff в следующий execution cycle.
- Acceptance criteria:
  - следующий инженер сможет начать реализацию `rebuild-master` только по этому plan;
  - dependencies на `rebuild-role-resume` и `build-linkedin` описаны явно.
- Validation commands:
  - `Get-Content -Raw plans\2026-04-22-rebuild-master-workflow.md`
- Notes / discoveries:
  - implementation decomposition теперь зависит не от product ambiguity, а от отдельного upstream workflow plan для review/acceptance process.

## Decision log

- `2026-04-22 11:18` — Следующим workflow после `prepare-screening` выбран `rebuild-master`, но стартовать его реализацию без отдельного plan нельзя. — Причина: ordered backlog уже фиксирует dependency gate по permanent-signal store. — Поэтому сначала открыт dedicated planning artifact, а не implementation branch.
- `2026-04-22 11:18` — `adoptions/accepted/` и `knowledge/roles/` рассматриваются как реальные candidate stores, а не как hypothetical future paths. — Они уже существуют в root repo и должны быть учтены в contract decision. — Это сужает вопрос с абстрактного “где хранить сигналы” до конкретного выбора ролей между существующими слоями.
- `2026-04-22 11:42` — Принят owner-level contract: approved permanent signals сначала живут в `adoptions/accepted/MASTER.md`, а попадание в `resumes/MASTER.md` является отдельным, более редким шагом. — Это жёстко разделяет review/approval layer и canonical resume mutation layer. — `rebuild-master` больше не должен напрямую зависеть от raw vacancy drafts или от `knowledge/roles/` как competing source of truth.
- `2026-04-22 11:42` — Перед `rebuild-master` выделен отдельный upstream process `inbox/questions -> accepted + knowledge/roles`. — Причина: именно там происходит human/agent review, ответы на вопросы и нормализация постоянных сигналов. — Следовательно, `rebuild-master` остаётся downstream workflow и не является ближайшим implementation step.

## Progress log

- `2026-04-22 11:18` — Создан dedicated plan для `rebuild-master` и закрыт baseline milestone M1 на основе текущего состояния `resumes/MASTER.md`, `adoptions/` и `knowledge/`. — Root inspection подтвердил наличие intended review/knowledge layers, но не дал безопасного ответа, кто именно является canonical input для merge в `MASTER`. — Status: `blocked`.
- `2026-04-22 11:42` — M2 contract decision закрыт по ответу owner: canonical approved staging layer — `adoptions/accepted/MASTER.md`, а `knowledge/roles/` пересматривается в отдельном review process и не является direct input для `rebuild-master`. — Это снимает product ambiguity внутри самого `rebuild-master`, но переводит блокировку на upstream process planning. — Status: `blocked`.

## Current state

- Current milestone: `M3`
- Current status: `blocked`
- Next step: `Дождаться стабилизации отдельного upstream plan для review/acceptance process (`inbox/` -> `questions/` -> `accepted/` + `knowledge/roles`), затем разложить `rebuild-master` на кодовые implementation milestones.`
- Active blockers:
  - Upstream review/acceptance process ещё не оформлен отдельным implementation plan.
- Open questions:
  - Должен ли `rebuild-master` дополнительно формировать change report/diff artifact рядом с `MASTER.md`, или достаточно обновления самого файла?
  - Нужен ли batching policy для `accepted/MASTER.md`, чтобы merge в `MASTER` работал по срезам, а не по всему файлу целиком?

## Completion summary

Заполняется после завершения всех milestones. На текущем этапе baseline и product contract уже зафиксированы; текущий blocker для `rebuild-master` теперь чисто sequencing-oriented и связан с отсутствием отдельного implementation plan для upstream review/acceptance process.
