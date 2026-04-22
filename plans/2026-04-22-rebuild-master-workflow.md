# Rebuild Master Workflow

- Title: `rebuild-master workflow`
- Slug: `2026-04-22-rebuild-master-workflow`
- Owner: `Codex`
- Created: `2026-04-22`
- Last updated: `2026-04-22 11:18`
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

Главная неопределённость сейчас не в коде, а в продуктовом контракте:

- что именно считается accepted permanent signal;
- где он живёт до merge в `resumes/MASTER.md`;
- должен ли `knowledge/roles/` участвовать как отдельный normalized store или оставаться downstream derivative.

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
- `adoptions/accepted/` может выступать review/approval layer, но это ещё не равнозначно окончательному merge destination;
- `knowledge/roles/` нужен для normalized role signals, но его точная роль относительно `MASTER` пока не закреплена;
- без явной policy нельзя безопасно автоматизировать merge permanent signals в `MASTER`.

## Risks and unknowns

- если accepted signals будут жить сразу в нескольких местах, появятся конкурирующие источники истины;
- если merge policy окажется слишком жёсткой, workflow превратится в опасный auto-editor для `MASTER.md`;
- если оставить `knowledge/roles/` и `adoptions/accepted/` без разделения ролей, последующие workflows снова упрётся в drift;
- неясно, должен ли workflow собирать сигналы только из `adoptions/accepted/MASTER.md` или ещё и из runtime/vacancy history.

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

- Status: `blocked`
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
  - этот milestone зависит от owner/product clarification и не должен закрываться молчаливым предположением.

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
  - implementation decomposition имеет смысл только после закрытия M2.

## Decision log

- `2026-04-22 11:18` — Следующим workflow после `prepare-screening` выбран `rebuild-master`, но стартовать его реализацию без отдельного plan нельзя. — Причина: ordered backlog уже фиксирует dependency gate по permanent-signal store. — Поэтому сначала открыт dedicated planning artifact, а не implementation branch.
- `2026-04-22 11:18` — `adoptions/accepted/` и `knowledge/roles/` рассматриваются как реальные candidate stores, а не как hypothetical future paths. — Они уже существуют в root repo и должны быть учтены в contract decision. — Это сужает вопрос с абстрактного “где хранить сигналы” до конкретного выбора ролей между существующими слоями.

## Progress log

- `2026-04-22 11:18` — Создан dedicated plan для `rebuild-master` и закрыт baseline milestone M1 на основе текущего состояния `resumes/MASTER.md`, `adoptions/` и `knowledge/`. — Root inspection подтвердил наличие intended review/knowledge layers, но не дал безопасного ответа, кто именно является canonical input для merge в `MASTER`. — Status: `blocked`.

## Current state

- Current milestone: `M2`
- Current status: `blocked`
- Next step: `Получить owner-level решение: accepted permanent signals должны сначала жить в `adoptions/accepted/MASTER.md`, в `knowledge/roles/`, или сразу редактировать `resumes/MASTER.md` как единственный staging destination перед rebuild.`
- Active blockers:
  - Не зафиксирован canonical destination для accepted permanent signals.
  - Не разделены роли review layer (`adoptions/accepted/`) и normalized knowledge layer (`knowledge/roles/`) относительно `MASTER`.
- Open questions:
  - Что считать canonical input для `rebuild-master`: только `adoptions/accepted/MASTER.md` или смесь accepted signals + normalized role knowledge?
  - Нужен ли `knowledge/roles/` как обязательный промежуточный слой до обновления `MASTER`, или он должен быть downstream derivative уже после `rebuild-master`?

## Completion summary

Заполняется после завершения всех milestones. На текущем этапе baseline создан, главный blocker явно сформулирован, и дальнейшее движение зависит от owner-level contract decision, а не от нехватки технической разведки.
