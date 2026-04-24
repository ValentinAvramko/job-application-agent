# Build LinkedIn Workflow

- Название: `build-linkedin workflow`
- Slug: `2026-04-22-build-linkedin-workflow`
- Ответственный: `Codex`
- Создан: `2026-04-22`
- Обновлен: `2026-04-23 09:46`
- Общий статус: `done`

## Цель

Подготовить и реализовать исполнимый workflow `build-linkedin`, который читает уже стабилизированное resume family и формирует durable LinkedIn draft artifacts так, чтобы:

- `resumes/MASTER.md` оставался единственным factual source of truth;
- выбранное `resumes/<role>.md` могло влиять на позиционирование только как downstream derivative, а не как независимый источник фактов;
- результат жил в `profile/` как profile-specific derivative, пригодный для ручного заполнения LinkedIn без выдумывания данных и с явными `CHECK` / `GAP` маркерами там, где входов не хватает.

## Контекст

После завершения `rebuild-master` и `rebuild-role-resume` sequencing remaining workflows дошёл до `build-linkedin`.

Подтверждённый baseline на `2026-04-22`:

- `resumes/MASTER.md` уже стабилизирован как canonical factual source, а role-resume family (`CIO.md`, `CTO.md`, `HoE.md`, `HoD.md`, `EM.md`) существует как downstream derivative layer;
- `profile/` закреплён root-level contract'ом как home для durable profile derivatives, но фактически сейчас содержит только `README.md`;
- `profile/README.md` описывает служебный metadata layer (`contact-regions.yml`, name/location/contact variants, public profile links), однако самого `contact-regions.yml` в root сейчас нет;
- `knowledge/roles/` пока практически пуст и содержит только `README.md`, поэтому role-specific shaping layer для LinkedIn на текущем этапе минимален;
- в историческом root corpus есть `promts/promt-create-linkedin-profile.md` с deliverable map для RU/EN LinkedIn packs, но root-normalization plan уже закрепил этот файл как historical reference only, а не как canonical spec;
- в коде `tooling/application-agent` workflow `build-linkedin` пока отсутствует: есть только sequencing mentions в `README.md`, что этот шаг должен читать уже обновлённый canonical resume family.

Для first executable contract M2 зафиксированы следующие baseline-решения:

- workflow строит один per-role artifact `profile/linkedin/<target_role>.md`, а не россыпь отдельных файлов: внутри него живут executive summary, ready-to-paste RU pack, ready-to-paste EN pack, field-by-field filling guide и `GAP` list;
- `target_role` обязателен для первой версии, потому что LinkedIn workflow должен собирать один целевой positioning pack, а не угадывать между generic executive profile и role-specific angle;
- input precedence жёстко разделена по слоям: `resumes/MASTER.md` обязателен и остаётся единственным factual source, `resumes/<target_role>.md` обязателен как positioning overlay без права противоречить `MASTER`, `profile/contact-regions.yml` optional и может влиять только на name/location/contact/public-link surface;
- если `profile/contact-regions.yml` отсутствует, workflow использует только то, что уже явно есть в canonical resume family, и выводит `CHECK` / `GAP` вместо молчаливой подстановки profile metadata;
- private contact channels (`phone`, `email`, `telegram`, `whatsapp`) не попадают автоматически в public-ready copy blocks и остаются только в filling guide как `OPTIONAL` или `CHECK`, если их публикация требует ручного решения.

## Границы

### Входит в scope

- dedicated plan и baseline contract для `build-linkedin`;
- явное решение по input surface и precedence: `MASTER`, optional role resume, optional profile metadata;
- решение по output home и форме durable artifacts внутри `profile/`;
- baseline policy для `CHECK` / `GAP` / `OPTIONAL` markers и anti-hallucination rules;
- implementation-ready decomposition для helper layer, workflow/CLI wiring, runtime report и docs handoff.

### Не входит в scope

- автоматическая публикация или browser automation внутри LinkedIn;
- изменение `resumes/MASTER.md`, role resumes или `knowledge/roles/` в рамках самого workflow;
- сбор новых profile facts через отдельную interactive session в первой версии;
- PDF export, public sharing artifacts и любые задачи `export-resume-pdf`;
- full social-profile strategy beyond LinkedIn.

## Допущения

- `resumes/MASTER.md` остаётся единственным factual source; downstream LinkedIn draft не может добавлять новые факты, отсутствующие в canonical resume family.
- `resumes/<role>.md` может использоваться как optional positioning overlay для выбранной цели, но не должен противоречить `MASTER`.
- `profile/` остаётся корректным root home для durable LinkedIn derivatives.
- Отсутствующие metadata inputs (`contact-regions.yml`, location variants, public links beyond what already lives in root artifacts) должны приводить к явным `CHECK` / `GAP`, а не к молчаливой генерации.
- Первая исполнимая версия заканчивается draft artifact и runtime report, а не direct LinkedIn-side effect.

## Риски и неизвестные

- отсутствие `profile/contact-regions.yml` остаётся реальным quality risk для location/contact/public-link recommendations: baseline fallback теперь понятен, но может быть беднее желаемого profile overlay;
- LinkedIn требует editorial condensation и section-specific formatting, поэтому helper layer должен быть достаточно структурным, чтобы не скатиться либо в дословный resume dump, либо в свободную генерацию с drift;
- единый bilingual per-role pack удобен для review и handoff, но может оказаться слишком объёмным; если это проявится на M3/M4, позже может понадобиться split без смены factual/input contract;
- первая версия жёстко требует `target_role`, поэтому generic executive LinkedIn profile без role overlay остаётся отдельным follow-up, а не implicit fallback.

## Внешние точки касания

- `C:\Users\avramko\OneDrive\Documents\Career\resumes\MASTER.md` — чтение / проверка — canonical factual input;
- `C:\Users\avramko\OneDrive\Documents\Career\resumes\CIO.md`, `CTO.md`, `HoE.md`, `HoD.md`, `EM.md` — чтение / проверка — optional downstream positioning inputs;
- `C:\Users\avramko\OneDrive\Documents\Career\profile\` — обновление / проверка — durable output home и future metadata layer;
- `C:\Users\avramko\OneDrive\Documents\Career\knowledge\roles\` — чтение / проверка — optional shaping input if role knowledge appears;
- `C:\Users\avramko\OneDrive\Documents\Career\promts\promt-create-linkedin-profile.md` — чтение / reference-only — historical deliverable map, not source of truth;
- `C:\Users\avramko\OneDrive\Documents\Career\agent_memory\runtime\` — обновление / проверка — runtime report и workflow trail;
- `C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\README.md` — чтение / возможное обновление — public workflow sequencing and operator contract.

## Этапы

### M1. Baseline Inventory And Contract Gap For Build-LinkedIn

- Статус: `done`
- Цель:
  - собрать current-state baseline по canonical resume family, `profile/`, historical LinkedIn prompt materials и code references;
  - свести активную неопределённость к одному product/contract step.
- Артефакты:
  - dedicated plan;
  - inventory текущих input/output слоёв;
  - явный blocker по first executable contract.
- Критерии приемки:
  - plan фиксирует, что `build-linkedin` стартует только после стабилизации `MASTER` и role-resume family;
  - отражено, что `profile/` пока почти пуст, `contact-regions.yml` отсутствует, а `promts/promt-create-linkedin-profile.md` имеет только historical reference status;
  - следующий шаг после baseline сводится к одному contract-decision milestone.
- Команды валидации:
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\resumes`
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\profile`
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\knowledge\roles`
  - `Test-Path C:\Users\avramko\OneDrive\Documents\Career\promts\promt-create-linkedin-profile.md`
  - `rg -n "build-linkedin|linkedin" C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\src C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\tests C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\README.md`
- Заметки / находки:
  - dedicated workflow ещё не реализован в коде;
  - `profile/` готов как output home по root contract, но ещё не содержит stable metadata artifacts кроме `README.md`;
  - главный blocker не технический, а contract-level: надо определить first executable output shape и input precedence.

### M2. First Executable LinkedIn Contract

- Статус: `done`
- Цель:
  - закрепить минимальный, но полноценный contract для первой исполнимой версии `build-linkedin`.
- Артефакты:
  - решение по output artifact layout в `profile/`;
  - input precedence policy между `MASTER`, `resumes/<role>.md` и optional profile metadata;
  - правила для bilingual packaging, contact exposure и `CHECK` / `GAP` markers.
- Критерии приемки:
  - однозначно определено, какие root inputs обязательны, какие optional и как они приоритизируются;
  - однозначно определено, какой именно durable artifact или набор artifacts создаёт workflow;
  - policy не требует выдумывать missing facts и не заставляет workflow напрямую менять `MASTER` или role resumes.
- Команды валидации:
  - `Get-Content -Raw C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\plans\2026-04-22-build-linkedin-workflow.md`
  - `Get-Content -Raw C:\Users\avramko\OneDrive\Documents\Career\profile\README.md`
  - `Get-Content -Raw C:\Users\avramko\OneDrive\Documents\Career\promts\promt-create-linkedin-profile.md`
- Заметки / находки:
  - first executable artifact закреплён как per-role file `profile/linkedin/<target_role>.md` с five-part pack: executive summary, RU pack, EN pack, filling guide, `GAP` list;
  - `target_role` обязателен в baseline-версии, чтобы workflow не гадал между несколькими role angles;
  - `resumes/MASTER.md` остаётся единственным factual source, `resumes/<target_role>.md` используется только как positioning overlay, `profile/contact-regions.yml` — optional metadata overlay только для profile surface;
  - private contact channels не должны автоматически попадать в public-ready output sections.

### M3. Draft Builder For LinkedIn Profile Artifacts

- Статус: `done`
- Цель:
  - реализовать helper layer, который читает `resumes/MASTER.md`, выбранное `resumes/<target_role>.md` и optional `profile/contact-regions.yml`, а затем рендерит deterministic per-role LinkedIn pack без фактического drift.
- Артефакты:
  - builder module для load/merge/render `profile/linkedin/<target_role>.md`;
  - explicit section model для five-part output pack;
  - targeted tests на no-hallucination, idempotency и missing-input markers.
- Критерии приемки:
  - helper layer не invents facts beyond `MASTER` plus approved optional overlays;
  - одинаковые inputs дают idempotent output;
  - missing optional metadata отражается маркерами, а не silent omission без trace;
  - private contact channels не попадают в ready-to-paste public sections автоматически.
- Команды валидации:
  - `python -m unittest tests.test_build_linkedin_helpers`
- Заметки / находки:
  - helper implementation оформлен отдельным модулем `application_agent.linkedin_builder`, чтобы M4 мог переиспользовать deterministic load/merge/render logic без дублирования;
  - builder использует front matter `MASTER.md` как fallback profile surface и optional `profile/contact-regions.yml` как override only для name/location/public-link/private-contact recommendations;
  - private contacts остаются только во filling guide, а missing EN/public profile surface превращаются в явные `CHECK` / `GAP` маркеры вместо выдумывания copy.

### M4. Workflow, CLI And Runtime Wiring

- Статус: `done`
- Цель:
  - добавить executable workflow `build-linkedin` в runtime catalog с безопасными side effects только на LinkedIn draft artifacts и runtime memory.
- Артефакты:
  - workflow module и request contract;
  - wiring в `registry`, `cli`, `config` и workflow memory catalog;
  - runtime report under `agent_memory/runtime/build-linkedin/`;
  - workflow/CLI tests.
- Критерии приемки:
  - `list-workflows` показывает `build-linkedin`;
  - successful run меняет только agreed LinkedIn artifact(s) в `profile/`, runtime report и workflow memory trail;
  - invalid role/language/contract inputs дают явную ошибку, а не partial artifact drift.
- Команды валидации:
  - `python -m unittest tests.test_build_linkedin_helpers tests.test_build_linkedin_workflow tests.test_cli tests.test_memory_store`
  - `python run_agent.py --root ../.. list-workflows`
- Заметки / находки:
  - пока нет

### M5. Docs Sync And Downstream Handoff To Export-Resume-Pdf

- Статус: `done`
- Цель:
  - синхронизировать docs, full validation baseline и handoff в следующий remaining workflow после `build-linkedin`.
- Артефакты:
  - README update;
  - при необходимости sync root docs по `profile/` artifacts;
  - full validation baseline;
  - explicit next step в master plan для `export-resume-pdf`.
- Критерии приемки:
  - docs объясняют, какие LinkedIn artifacts создаёт workflow и какие входы он читает;
  - full relevant tests и CLI checks проходят;
  - master plan получает новый следующий шаг после закрытия этого workflow.
- Команды валидации:
  - `python -m unittest discover -s tests`
  - `python run_agent.py --root ../.. list-workflows`
  - `python run_agent.py --root ../.. show-memory`
- Заметки / находки:
  - `tooling/application-agent/README.md` теперь описывает `build-linkedin` как executable workflow, его CLI entrypoint, output artifact `profile/linkedin/<target_role>.md` и runtime report path;
  - root `profile/README.md` синхронизирован с новым derivative layer `linkedin/<target_role>.md`, чтобы публичный output home был зафиксирован не только в кодовом README;
  - `show-memory` успешно исполняется на текущем workspace и по-прежнему показывает historical reconciliation gaps по старым run records; для этого milestone это допустимо, потому что acceptance criterion требовал успешного CLI-check, а не очистки истории.

## Журнал решений

- `2026-04-22 19:33` — Dedicated plan для `build-linkedin` открыт только после завершения `rebuild-master` и `rebuild-role-resume`. — Причина: downstream LinkedIn workflow должен читать уже стабилизированный canonical resume family, а не raw vacancy/adoption layers. — Это сохраняет последовательность `accepted -> MASTER -> role resume -> LinkedIn`.
- `2026-04-22 19:33` — Исторический файл `promts/promt-create-linkedin-profile.md` закреплён как reference-only deliverable map, а не как source-of-truth спецификация. — Причина: root-normalization уже классифицировал legacy prompt corpus как historical material. — Реальный executable contract должен жить в dedicated plan и затем в коде/README.
- `2026-04-23 08:57` — First executable artifact закреплён как один per-role pack `profile/linkedin/<target_role>.md`, а не как набор разрозненных RU/EN файлов. — Причина: historical prompt map требует не только тексты по языкам, но и executive summary, filling guide и `GAP` list; один pack сохраняет reviewability и не плодит лишние file contracts. — Это делает M3 implementation scope конкретным и совместимым с future split при необходимости.
- `2026-04-23 08:57` — `target_role` объявлен обязательным input первой версии; `resumes/MASTER.md` остаётся единственным factual source, `resumes/<target_role>.md` — обязательным positioning overlay, а `profile/contact-regions.yml` — optional metadata overlay только для contact/location/public-link surface. — Причина: baseline workflow не должен угадывать целевой angle и не должен создавать новый source-of-truth drift между resume и profile слоями. — Это снимает product ambiguity для helper/workflow milestones M3-M4.
- `2026-04-23 08:57` — Private contact channels не включаются автоматически в public-ready output sections и остаются только в filling guide как `OPTIONAL` / `CHECK`. — Причина: LinkedIn artifact живёт в `profile/` и затрагивает privacy-sensitive surface; безопасный baseline не должен публиковать телефоны, мессенджеры и почту без ручного решения. — Это фиксирует contact exposure policy до начала реализации.

## Журнал прогресса

- `2026-04-22 19:33` — Создан dedicated plan и закрыт baseline milestone M1 по текущему состоянию `resumes/`, `profile/`, `knowledge/roles/`, historical LinkedIn prompt material и code references. — Validation опиралась на реальный root inventory, `MASTER.md`, `profile/README.md`, historical prompt и `rg` по submodule-коду. — Статус: `blocked`.
- `2026-04-23 08:57` — M2 закрыт: first executable contract теперь жёстко фиксирует per-role output `profile/linkedin/<target_role>.md`, обязательный `target_role`, input precedence (`MASTER` -> role resume -> optional profile metadata`) и privacy-safe contact policy. — Validation выполнена повторным чтением dedicated plan, `profile/README.md` и historical prompt map; product ambiguity для M3 снята. — Статус: `in_progress`.
- `2026-04-23 09:17` — M3 helper milestone закрыт: добавлен модуль `application_agent.linkedin_builder` с deterministic projection `MASTER` + selected role resume + optional `profile/contact-regions.yml` -> `profile/linkedin/<target_role>.md`, five-part artifact model и marker-based fallback policy для missing EN/profile-surface inputs. — Валидация: `python -m unittest tests.test_build_linkedin_helpers` -> `OK`; targeted tests покрывают metadata precedence, idempotency, privacy-safe handling private contacts и явные `CHECK` / `GAP` markers. — Статус: `in_progress`.
- `2026-04-23 09:27` — M4 закрыт: helper layer обёрнут в executable workflow `build-linkedin`, добавлены wiring в `registry`, `cli`, `config` и runtime workflow catalog, runtime report пишется в `agent_memory/runtime/build-linkedin/<role>.md`, а новые tests `tests.test_build_linkedin_workflow` плюс обновлённые `tests.test_cli` и `tests.test_memory_store` фиксируют safe side effects и CLI routing. — Валидация: `python -m unittest tests.test_build_linkedin_helpers tests.test_build_linkedin_workflow tests.test_cli tests.test_memory_store` -> `OK`; `python run_agent.py --root ../.. list-workflows` показывает `build-linkedin`. — Статус: `in_progress`.
- `2026-04-23 09:46` — M5 закрыт: docs синхронизированы в `tooling/application-agent/README.md` и root `profile/README.md`, full validation baseline остаётся зелёным (`python -m unittest discover -s tests` -> `OK (67 tests)`), а CLI checks подтверждают доступность workflow и целостность runtime surface (`list-workflows` показывает `build-linkedin`, `show-memory` исполняется успешно). — Dedicated plan завершён end-to-end и возвращает sequencing в master plan для следующего workflow `export-resume-pdf`. — Статус: `done`.

## Текущее состояние

- Текущий milestone: `completed`
- Текущий статус: `done`
- Следующий шаг: `Вернуться в master plan `2026-04-21-repository-reconstruction-and-backlog.md` и открыть dedicated plan для `export-resume-pdf`.`
- Активные блокеры:
  - нет
- Открытые вопросы:
  - нет

## Итог завершения

Завершён полный baseline workflow `build-linkedin`: helper layer, runtime wiring, operator docs и root profile-output contract теперь согласованы вокруг одного deterministic output `profile/linkedin/<target_role>.md`.

Провалидировано:

- `python -m unittest discover -s tests` -> `OK (67 tests)`;
- `python run_agent.py --root ../.. list-workflows` -> каталог содержит `build-linkedin`;
- `python run_agent.py --root ../.. show-memory` -> команда исполняется успешно на текущем workspace.

Follow-up после этого dedicated plan ровно один: открыть и выполнить следующий remaining-workflow plan для `export-resume-pdf`.

Остаточный риск минимальный и известный: `show-memory` продолжает отражать historical reconciliation gaps по старым run records, но этот workflow не добавил нового drift и не менял runtime-memory contract.

Корневой репозиторий затронут только на уровне docs/output contract: обновлён `profile/README.md`, код или runtime artifacts в корне этим milestone не изменялись.
