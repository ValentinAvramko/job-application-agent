# Build LinkedIn Workflow

- Title: `build-linkedin workflow`
- Slug: `2026-04-22-build-linkedin-workflow`
- Owner: `Codex`
- Created: `2026-04-22`
- Last updated: `2026-04-22 19:33`
- Overall status: `blocked`

## Objective

Подготовить и реализовать исполнимый workflow `build-linkedin`, который читает уже стабилизированное resume family и формирует durable LinkedIn draft artifacts так, чтобы:

- `resumes/MASTER.md` оставался единственным factual source of truth;
- выбранное `resumes/<role>.md` могло влиять на позиционирование только как downstream derivative, а не как независимый источник фактов;
- результат жил в `profile/` как profile-specific derivative, пригодный для ручного заполнения LinkedIn без выдумывания данных и с явными `CHECK` / `GAP` маркерами там, где входов не хватает.

## Background and context

После завершения `rebuild-master` и `rebuild-role-resume` sequencing remaining workflows дошёл до `build-linkedin`.

Подтверждённый baseline на `2026-04-22`:

- `resumes/MASTER.md` уже стабилизирован как canonical factual source, а role-resume family (`CIO.md`, `CTO.md`, `HoE.md`, `HoD.md`, `EM.md`) существует как downstream derivative layer;
- `profile/` закреплён root-level contract'ом как home для durable profile derivatives, но фактически сейчас содержит только `README.md`;
- `profile/README.md` описывает служебный metadata layer (`contact-regions.yml`, name/location/contact variants, public profile links), однако самого `contact-regions.yml` в root сейчас нет;
- `knowledge/roles/` пока практически пуст и содержит только `README.md`, поэтому role-specific shaping layer для LinkedIn на текущем этапе минимален;
- в историческом root corpus есть `promts/promt-create-linkedin-profile.md` с deliverable map для RU/EN LinkedIn packs, но root-normalization plan уже закрепил этот файл как historical reference only, а не как canonical spec;
- в коде `tooling/application-agent` workflow `build-linkedin` пока отсутствует: есть только sequencing mentions в `README.md`, что этот шаг должен читать уже обновлённый canonical resume family.

Главная двусмысленность для первой исполнимой версии:

- ещё не закреплён first executable contract: должен ли workflow собирать один bilingual `profile/linkedin.md`, набор отдельных RU/EN artifacts, draft pack с field-by-field guide, либо более узкий baseline output;
- не определён input precedence между `resumes/MASTER.md`, выбранным `resumes/<role>.md` и будущим profile metadata layer;
- отсутствие `profile/contact-regions.yml` означает, что location/contact/public-profile overlay пока нельзя считать стабильным machine-readable input.

## Scope

### In scope

- dedicated plan и baseline contract для `build-linkedin`;
- явное решение по input surface и precedence: `MASTER`, optional role resume, optional profile metadata;
- решение по output home и форме durable artifacts внутри `profile/`;
- baseline policy для `CHECK` / `GAP` / `OPTIONAL` markers и anti-hallucination rules;
- implementation-ready decomposition для helper layer, workflow/CLI wiring, runtime report и docs handoff.

### Out of scope

- автоматическая публикация или browser automation внутри LinkedIn;
- изменение `resumes/MASTER.md`, role resumes или `knowledge/roles/` в рамках самого workflow;
- сбор новых profile facts через отдельную interactive session в первой версии;
- PDF export, public sharing artifacts и любые задачи `export-resume-pdf`;
- full social-profile strategy beyond LinkedIn.

## Assumptions

- `resumes/MASTER.md` остаётся единственным factual source; downstream LinkedIn draft не может добавлять новые факты, отсутствующие в canonical resume family.
- `resumes/<role>.md` может использоваться как optional positioning overlay для выбранной цели, но не должен противоречить `MASTER`.
- `profile/` остаётся корректным root home для durable LinkedIn derivatives.
- Отсутствующие metadata inputs (`contact-regions.yml`, location variants, public links beyond what already lives in root artifacts) должны приводить к явным `CHECK` / `GAP`, а не к молчаливой генерации.
- Первая исполнимая версия заканчивается draft artifact и runtime report, а не direct LinkedIn-side effect.

## Risks and unknowns

- без owner-level решения по форме output artifact можно либо переусложнить первую версию, либо потерять ключевые deliverables из historical prompt map;
- если input precedence между `MASTER`, role resume и profile metadata не будет жёстко зафиксирован, появится новый contract drift внутри resume/profile family;
- отсутствие `profile/contact-regions.yml` создаёт риск некорректного выбора contact/location blocks и публичных ссылок;
- LinkedIn требует editorial condensation и section-specific formatting, поэтому слишком deterministic baseline может дать слабый результат, а слишком свободная генерация — начать выдумывать факты;
- bilingual output увеличивает объём и сложность acceptance surface, особенно если для публикации реально нужен только один язык;
- profile-specific artifact может затронуть privacy-sensitive данные, если заранее не закрепить правила публикации контактов.

## External touchpoints

- `C:\Users\avramko\OneDrive\Documents\Career\resumes\MASTER.md` — чтение / проверка — canonical factual input;
- `C:\Users\avramko\OneDrive\Documents\Career\resumes\CIO.md`, `CTO.md`, `HoE.md`, `HoD.md`, `EM.md` — чтение / проверка — optional downstream positioning inputs;
- `C:\Users\avramko\OneDrive\Documents\Career\profile\` — обновление / проверка — durable output home и future metadata layer;
- `C:\Users\avramko\OneDrive\Documents\Career\knowledge\roles\` — чтение / проверка — optional shaping input if role knowledge appears;
- `C:\Users\avramko\OneDrive\Documents\Career\promts\promt-create-linkedin-profile.md` — чтение / reference-only — historical deliverable map, not source of truth;
- `C:\Users\avramko\OneDrive\Documents\Career\agent_memory\runtime\` — обновление / проверка — runtime report и workflow trail;
- `C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\README.md` — чтение / возможное обновление — public workflow sequencing and operator contract.

## Milestones

### M1. Baseline Inventory And Contract Gap For Build-LinkedIn

- Status: `done`
- Goal:
  - собрать current-state baseline по canonical resume family, `profile/`, historical LinkedIn prompt materials и code references;
  - свести активную неопределённость к одному product/contract step.
- Deliverables:
  - dedicated plan;
  - inventory текущих input/output слоёв;
  - явный blocker по first executable contract.
- Acceptance criteria:
  - plan фиксирует, что `build-linkedin` стартует только после стабилизации `MASTER` и role-resume family;
  - отражено, что `profile/` пока почти пуст, `contact-regions.yml` отсутствует, а `promts/promt-create-linkedin-profile.md` имеет только historical reference status;
  - следующий шаг после baseline сводится к одному contract-decision milestone.
- Validation commands:
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\resumes`
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\profile`
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\knowledge\roles`
  - `Test-Path C:\Users\avramko\OneDrive\Documents\Career\promts\promt-create-linkedin-profile.md`
  - `rg -n "build-linkedin|linkedin" C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\src C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\tests C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\README.md`
- Notes / discoveries:
  - dedicated workflow ещё не реализован в коде;
  - `profile/` готов как output home по root contract, но ещё не содержит stable metadata artifacts кроме `README.md`;
  - главный blocker не технический, а contract-level: надо определить first executable output shape и input precedence.

### M2. First Executable LinkedIn Contract

- Status: `planned`
- Goal:
  - закрепить минимальный, но полноценный contract для первой исполнимой версии `build-linkedin`.
- Deliverables:
  - решение по output artifact layout в `profile/`;
  - input precedence policy между `MASTER`, `resumes/<role>.md` и optional profile metadata;
  - правила для bilingual packaging, contact exposure и `CHECK` / `GAP` markers.
- Acceptance criteria:
  - однозначно определено, какие root inputs обязательны, какие optional и как они приоритизируются;
  - однозначно определено, какой именно durable artifact или набор artifacts создаёт workflow;
  - policy не требует выдумывать missing facts и не заставляет workflow напрямую менять `MASTER` или role resumes.
- Validation commands:
  - `Get-Content -Raw C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\plans\2026-04-22-build-linkedin-workflow.md`
  - `Get-Content -Raw C:\Users\avramko\OneDrive\Documents\Career\profile\README.md`
  - `Get-Content -Raw C:\Users\avramko\OneDrive\Documents\Career\promts\promt-create-linkedin-profile.md`
- Notes / discoveries:
  - пока нет

### M3. Draft Builder For LinkedIn Profile Artifacts

- Status: `planned`
- Goal:
  - реализовать helper layer, который читает canonical inputs и рендерит deterministic LinkedIn draft artifact(s) без фактического drift.
- Deliverables:
  - builder module для load/merge/render LinkedIn pack;
  - explicit section model для output artifact(s);
  - targeted tests на no-hallucination, idempotency и missing-input markers.
- Acceptance criteria:
  - helper layer не invents facts beyond `MASTER` plus approved optional overlays;
  - одинаковые inputs дают idempotent output;
  - missing optional metadata отражается маркерами, а не silent omission без trace.
- Validation commands:
  - `python -m unittest tests.test_build_linkedin_helpers`
- Notes / discoveries:
  - пока нет

### M4. Workflow, CLI And Runtime Wiring

- Status: `planned`
- Goal:
  - добавить executable workflow `build-linkedin` в runtime catalog с безопасными side effects только на LinkedIn draft artifacts и runtime memory.
- Deliverables:
  - workflow module и request contract;
  - wiring в `registry`, `cli`, `config` и workflow memory catalog;
  - runtime report under `agent_memory/runtime/build-linkedin/`;
  - workflow/CLI tests.
- Acceptance criteria:
  - `list-workflows` показывает `build-linkedin`;
  - successful run меняет только agreed LinkedIn artifact(s) в `profile/`, runtime report и workflow memory trail;
  - invalid role/language/contract inputs дают явную ошибку, а не partial artifact drift.
- Validation commands:
  - `python -m unittest tests.test_build_linkedin_helpers tests.test_build_linkedin_workflow tests.test_cli tests.test_memory_store`
  - `python run_agent.py --root ../.. list-workflows`
- Notes / discoveries:
  - пока нет

### M5. Docs Sync And Downstream Handoff To Export-Resume-Pdf

- Status: `planned`
- Goal:
  - синхронизировать docs, full validation baseline и handoff в следующий remaining workflow после `build-linkedin`.
- Deliverables:
  - README update;
  - при необходимости sync root docs по `profile/` artifacts;
  - full validation baseline;
  - explicit next step в master plan для `export-resume-pdf`.
- Acceptance criteria:
  - docs объясняют, какие LinkedIn artifacts создаёт workflow и какие входы он читает;
  - full relevant tests и CLI checks проходят;
  - master plan получает новый следующий шаг после закрытия этого workflow.
- Validation commands:
  - `python -m unittest discover -s tests`
  - `python run_agent.py --root ../.. list-workflows`
  - `python run_agent.py --root ../.. show-memory`
- Notes / discoveries:
  - пока нет

## Decision log

- `2026-04-22 19:33` — Dedicated plan для `build-linkedin` открыт только после завершения `rebuild-master` и `rebuild-role-resume`. — Причина: downstream LinkedIn workflow должен читать уже стабилизированный canonical resume family, а не raw vacancy/adoption layers. — Это сохраняет последовательность `accepted -> MASTER -> role resume -> LinkedIn`.
- `2026-04-22 19:33` — Исторический файл `promts/promt-create-linkedin-profile.md` закреплён как reference-only deliverable map, а не как source-of-truth спецификация. — Причина: root-normalization уже классифицировал legacy prompt corpus как historical material. — Реальный executable contract должен жить в dedicated plan и затем в коде/README.

## Progress log

- `2026-04-22 19:33` — Создан dedicated plan и закрыт baseline milestone M1 по текущему состоянию `resumes/`, `profile/`, `knowledge/roles/`, historical LinkedIn prompt material и code references. — Validation опиралась на реальный root inventory, `MASTER.md`, `profile/README.md`, historical prompt и `rg` по submodule-коду. — Status: `blocked`.

## Current state

- Current milestone: `M2`
- Current status: `blocked`
- Next step: `Закрепить first executable contract для `build-linkedin`: input precedence (`MASTER` vs role resume vs profile metadata), output artifact layout в `profile/`, bilingual policy и правила `CHECK` / `GAP` markers.`
- Active blockers:
  - Не закреплён first executable contract для LinkedIn artifacts и profile metadata overlay.
- Open questions:
  - Нужен один bilingual `profile/linkedin.md`, два language-specific artifacts или более дробный pack с field-by-field guide?
  - Является ли `target_role` обязательным input для первой версии или workflow должен уметь строить generic executive profile только из `MASTER`?
  - Нужно ли first version читать отдельный profile metadata file, если `profile/contact-regions.yml` пока отсутствует?

## Completion summary

Заполняется только после завершения задачи.
