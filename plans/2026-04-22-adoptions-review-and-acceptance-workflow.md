# Adoptions Review And Acceptance Workflow

- Title: `adoptions review and acceptance workflow`
- Slug: `2026-04-22-adoptions-review-and-acceptance-workflow`
- Owner: `Codex`
- Created: `2026-04-22`
- Last updated: `2026-04-22 11:42`
- Overall status: `in_progress`

## Objective

Подготовить отдельный workflow/process для review и принятия постоянных сигналов так, чтобы:

- vacancy-specific предложения сначала попадали в `adoptions/inbox/<vacancy_id>.md`;
- unresolved вопросы накапливались в `adoptions/questions/`;
- ручная agent-guided session переводила approved signals в `adoptions/accepted/MASTER.md`;
- в этой же session при необходимости пересматривались `knowledge/roles/`;
- downstream `rebuild-master` получал уже только approved permanent signals, а не сырые vacancy drafts.

## Background and context

После завершения `prepare-screening` следующим по safety backlog был `rebuild-master`, но owner-level clarification уточнила sequencing:

1. после анализа каждой вакансии сырые предложения по конкретной вакансии должны жить в `adoptions/inbox/<vacancy_id>.md`;
2. в том же контуре должны накапливаться вопросы в `adoptions/questions/`;
3. отдельный ручной process должен разбирать `inbox/`, собирать ответы на `questions/`, формировать `accepted/` и пересматривать `knowledge/roles/`;
4. только после этого, более редким отдельным process, обновляется `resumes/MASTER.md`, а затем downstream role resumes.

Это означает, что review/acceptance process стал самостоятельным upstream workflow family и больше не должен быть скрытой частью `rebuild-master`.

Подтверждённые факты:

- `vacancies/<id>/adoptions.md` уже существует как generated staging artifact после `analyze-vacancy`;
- `adoptions/` уже содержит `inbox/`, `accepted/`, `questions/`;
- `adoptions/questions/open.md` уже существует как placeholder;
- `knowledge/roles/` существует как intended normalized store, но пока практически пуст;
- accepted permanent signals должны сначала жить в `adoptions/accepted/MASTER.md`, а не попадать напрямую в `resumes/MASTER.md`.

## Scope

### In scope

- file/state contract для `adoptions/inbox/`, `adoptions/questions/`, `adoptions/accepted/`, `knowledge/roles/`;
- sequencing между vacancy-local `adoptions.md` и root review layers;
- минимальный contract для ручной/agent-guided acceptance session;
- implementation-ready plan для последующей автоматизации этого review process.

### Out of scope

- прямое обновление `resumes/MASTER.md`;
- реализация `rebuild-master` и role resume rebuild;
- ретроспективная миграция всех historical vacancy artifacts в `inbox/`;
- redesign формата vacancy-local `analysis.md` или `screening.md`.

## Assumptions

- `vacancies/<id>/adoptions.md` остаётся generated draft, а не durable review layer;
- `adoptions/inbox/<vacancy_id>.md` хранит один review input file на вакансию;
- `adoptions/accepted/MASTER.md` хранит нормализованный current-state набор approved permanent signals без обязательной полной истории решений;
- `knowledge/roles/` пересматривается в acceptance session как downstream shaping layer для будущих role resumes;
- вопросы могут разрешаться через agent-guided Q&A session, а не только руками вне системы.

## Risks and unknowns

- не зафиксирован точный формат `adoptions/questions/`: один общий ledger или набор файлов по вакансиям/темам;
- не зафиксировано, должна ли acceptance session быть одним интерактивным workflow или набором отдельных CLI-команд;
- если перенос из vacancy-local `adoptions.md` в `inbox/` окажется неявным, снова смешаются generated drafts и review layer;
- если `accepted/MASTER.md` начнёт хранить историю вместо нормализованного current-state, downstream merge в `MASTER` станет нестабильным.

## External touchpoints

- `C:\Users\avramko\OneDrive\Documents\Career\vacancies\` — чтение / проверка — source generated vacancy-local `adoptions.md`;
- `C:\Users\avramko\OneDrive\Documents\Career\adoptions\inbox\` — обновление / проверка — per-vacancy review inputs;
- `C:\Users\avramko\OneDrive\Documents\Career\adoptions\questions\` — обновление / проверка — unresolved questions for review;
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
  - role `vacancies/<id>/adoptions.md` vs `adoptions/inbox/<vacancy_id>.md` разделена явно;
  - есть один конкретный следующий шаг для implementation planning.
- Validation commands:
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\adoptions -Recurse`
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\knowledge -Recurse`
- Notes / discoveries:
  - owner-approved sequencing делает этот workflow upstream dependency для `rebuild-master`.

### M2. Session Shape And File Contract

- Status: `in_progress`
- Goal:
  - определить точный interaction model и file-level contract для acceptance session.
- Deliverables:
  - decision record по interaction shape;
  - format expectations для `inbox/`, `questions/`, `accepted/MASTER.md`;
  - updated current state без архитектурной двусмысленности.
- Acceptance criteria:
  - ясно, это один interactive workflow или несколько явных commands/stages;
  - ясно, как вопросы живут в `questions/` и как ответы влияют на `accepted/MASTER.md`;
  - ясно, когда и как пересматривается `knowledge/roles/`.
- Validation commands:
  - `Get-Content -Raw plans\2026-04-22-adoptions-review-and-acceptance-workflow.md`
- Notes / discoveries:
  - user уже подтвердил high-level sequencing, но точная форма session остаётся архитектурным выбором.

### M3. Implementation-Ready Acceptance Workflow Plan

- Status: `planned`
- Goal:
  - разбить review/acceptance process на исполнимые implementation milestones.
- Deliverables:
  - code-facing milestone decomposition;
  - validation baseline;
  - handoff в execution cycle перед `rebuild-master`.
- Acceptance criteria:
  - следующий инженер сможет начать реализацию review/acceptance workflow только по этому plan;
  - downstream handoff в `rebuild-master` будет описан без дополнительных устных пояснений.
- Validation commands:
  - `Get-Content -Raw plans\2026-04-22-adoptions-review-and-acceptance-workflow.md`
- Notes / discoveries:
  - implementation decomposition имеет смысл только после закрытия M2.

## Decision log

- `2026-04-22 11:42` — Owner-approved sequencing закрепил отдельный upstream process: `vacancies/<id>/adoptions.md` -> `adoptions/inbox/<vacancy_id>.md` + `adoptions/questions/` -> `adoptions/accepted/MASTER.md` + `knowledge/roles/`. — Это убирает скрытую перегрузку из `rebuild-master`. — Дальнейшая реализация resume mutation должна идти только downstream от этого процесса.
- `2026-04-22 11:42` — `accepted/MASTER.md` признан canonical approved staging layer, а не history log. — Это делает downstream merge в `resumes/MASTER.md` детерминированнее. — Историю, если она потребуется, нужно будет проектировать отдельно, не смешивая с current-state layer.

## Progress log

- `2026-04-22 11:42` — Создан dedicated plan для review/acceptance workflow и закрыт baseline milestone M1 на основе owner-approved process. — Блокировка на уровне product sequencing снята, но interaction model acceptance session ещё не выбран. — Status: `in_progress`.

## Current state

- Current milestone: `M2`
- Current status: `in_progress`
- Next step: `Зафиксировать, должен ли review/acceptance process быть одним interactive workflow с Q&A session или набором отдельных explicit commands/stages.`
- Active blockers:
  - Не выбрана точная interaction shape для acceptance session.
- Open questions:
  - `questions/` должен оставаться одним общим ledger (`open.md`) или лучше перейти на per-vacancy question files?
  - Acceptance session должна сама переносить vacancy-local `adoptions.md` в `inbox/`, или это должен быть отдельный preparatory step?

## Completion summary

Заполняется после завершения всех milestones. На текущем этапе baseline и sequencing уже зафиксированы; текущая неопределённость сведена к interaction model и file contract, а не к source-of-truth drift.
