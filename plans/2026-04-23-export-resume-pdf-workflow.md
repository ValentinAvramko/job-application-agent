# Export Resume PDF Workflow

- Title: `export-resume-pdf workflow`
- Slug: `2026-04-23-export-resume-pdf-workflow`
- Owner: `Codex`
- Created: `2026-04-23`
- Last updated: `2026-04-23 15:04`
- Overall status: `done`

## Objective

Подготовить и реализовать исполнимый workflow `export-resume-pdf`, который читает уже стабилизированные resume/profile derivatives и формирует проверяемый PDF-артефакт так, чтобы:

- factual source оставался в существующем markdown resume (`resumes/MASTER.md` или выбранный `resumes/<role>.md`), а не переносился в отдельный PDF-specific source layer;
- profile metadata (`profile/contact-regions.yml`) влияло только на contact/location/public-link surface и не подменяло narrative contents резюме;
- результатом были не только сам PDF, но и render-verification artifacts, достаточные для визуальной проверки layout без ручных guesswork.

## Background and context

После завершения `build-linkedin` очередь remaining workflows дошла до `export-resume-pdf`.

Подтверждённый baseline на `2026-04-23`:

- текущий runtime stack уже умеет строить canonical resume family (`rebuild-master`, `rebuild-role-resume`) и profile derivatives (`build-linkedin`);
- отдельного workflow `export-resume-pdf` в коде пока нет: в `src/application_agent/workflows/` отсутствует модуль PDF export, а `list-workflows` не содержит соответствующий entrypoint;
- в корне есть только historical/manual reference path `employers/TaxDome/render_resume_pdf.py`, который жёстко завязан на один markdown input, Windows fonts (`arial.ttf`, `arialbd.ttf`), фиксированные filenames и employer-local `tmp_pdf_preview/`;
- в `archive/` лежат historical PDF exports, но они классифицированы как evidence/manual traces, а не как runtime contract;
- `templates/` пока не содержит PDF-specific templates или style packs: есть только `adoptions/`, `excel/`, `interview/`, `knowledge/`, `profile/`;
- `profile/contact-regions.yml` уже существует и содержит `RU`, `KZ`, `EU`, а также public links и default contact-region mapping;
- `resumes/MASTER.md` содержит rich front matter с multi-region contacts/links и остаётся основным factual source; current role resumes (`CIO`, `CTO`, `HoE`, `HoD`, `EM`) уже существуют как downstream derivative layer;
- `pyproject.toml` пока не декларирует `reportlab`, `pypdf`, `pdfplumber` или Poppler-bound tooling как runtime/test dependency, поэтому dependency contract ещё нужно закрепить;
- PDF skill требует visual verification через PNG render и рекомендует `reportlab` как baseline generator, но repo-level output contract должен подчиняться root normalization: durable public profile derivatives живут в `profile/`, а verification/runtime traces — в `agent_memory/runtime/`.

Контрактная неоднозначность, с которой стартует этот plan:

- не зафиксировано, какой именно resume source экспортируется первой версией: только role resumes, только `MASTER` или оба варианта;
- не зафиксировано, где должен жить durable PDF artifact и где должны храниться preview PNG/report;
- не решено, является ли `output_language` реальным translation input или лишь validation/filename selector для already-authored resume source;
- не решено, нужен ли отдельный template layer в `templates/` уже в первой версии или baseline workflow может стартовать с одного встроенного style contract.

## Scope

### In scope

- dedicated plan и baseline contract для `export-resume-pdf`;
- решение по input surface: selected resume, `contact_region`, `output_language`, optional template selector;
- решение по output home для durable PDF artifact и render-verification artifacts;
- implementation-ready decomposition для parser/projection layer, renderer, preview generation, workflow/CLI wiring и docs handoff;
- определение baseline dependency/runtime expectations для `reportlab` и preview rendering.

### Out of scope

- генерация нового markdown resume content внутри PDF workflow;
- browser upload/publication в job portals или LinkedIn;
- employer-specific визуальные кастомизации уровня `TaxDome` как часть первой версии;
- DOCX export, ATS parsing, watermarks, cover letters и любые side outputs вне PDF + verification trail;
- автоматический выбор вакансии, страны или языка из vacancy-local context в первой версии.

## Assumptions

- первая версия `export-resume-pdf` работает поверх уже существующего markdown resume и не переписывает `MASTER`/role resumes;
- `profile/contact-regions.yml` остаётся единственным profile overlay для location/contact/public-link surface;
- baseline PDF workflow должен оставаться deterministic: одинаковые inputs дают одинаковый PDF path, одинаковый verification path и повторяемый summary/report;
- первая версия не делает перевода resume content: она экспортирует already-authored markdown source и использует `output_language` как validation/file-contract input, а не как генеративный translation layer;
- first executable template contract может быть встроенным в код renderer; external template packs в `templates/` — это follow-up, а не prerequisite первой версии.

## Risks and unknowns

- historical renderer опирается на Windows system fonts; без отдельного portability-решения baseline renderer может оказаться хрупким на других окружениях;
- preview verification зависит от наличия `pdftoppm`/Poppler или эквивалентного render path; отсутствие инструмента нужно либо явно требовать, либо превращать в осмысленную validation error;
- current markdown resumes содержат rich structure и front matter placeholders, поэтому parser/projection layer может быстро разрастись, если не ограничить первую версию supported markdown contract;
- role resumes и `MASTER` сейчас в основном русскоязычные; если разрешить arbitrary `output_language`, workflow рискует silently drift в translation/problematic relabeling;
- отсутствие готовых PDF templates в `templates/` создаёт риск смешать renderer logic и future template system, если M2 не закрепит границы встроенного layout contract;
- render verification outputs могут оказаться слишком тяжёлыми для durable profile layer, если их не вынести в runtime memory.

## External touchpoints

- `C:\Users\avramko\OneDrive\Documents\Career\resumes\MASTER.md` — чтение / проверка — canonical factual source и fallback source для full-profile export;
- `C:\Users\avramko\OneDrive\Documents\Career\resumes\CIO.md`, `CTO.md`, `HoE.md`, `HoD.md`, `EM.md` — чтение / проверка — role-specific export sources;
- `C:\Users\avramko\OneDrive\Documents\Career\resumes\OPTIONAL_RULES.yml` — чтение / reference-only — current language/length conventions для existing resume corpus;
- `C:\Users\avramko\OneDrive\Documents\Career\profile\contact-regions.yml` — чтение / проверка — contact-region and public-link overlay;
- `C:\Users\avramko\OneDrive\Documents\Career\profile\` — обновление / проверка — durable home для final PDF artifacts;
- `C:\Users\avramko\OneDrive\Documents\Career\agent_memory\runtime\` — обновление / проверка — render report и preview verification trail;
- `C:\Users\avramko\OneDrive\Documents\Career\templates\` — чтение / проверка — future template touchpoint; first version currently has no PDF template there;
- `C:\Users\avramko\OneDrive\Documents\Career\employers\TaxDome\render_resume_pdf.py` и `tmp_pdf_preview\` — чтение / reference-only — historical manual prototype for reverse engineering;
- `C:\Users\avramko\OneDrive\Documents\Career\archive\*.pdf` — чтение / reference-only — historical output evidence, not runtime contract.

## Milestones

### M1. Baseline Inventory And Contract Gap For Export-Resume-Pdf

- Status: `done`
- Goal:
  - собрать current-state baseline по resume sources, profile metadata, historical manual renderers и отсутствующим runtime pieces;
  - свести активную неопределённость к одному contract-definition milestone.
- Deliverables:
  - dedicated plan;
  - inventory текущих input/output/reference layers;
  - явный blocker/unknown set для first executable PDF export contract.
- Acceptance criteria:
  - plan фиксирует, что `export-resume-pdf` стартует только после стабилизации resume family и profile metadata overlays;
  - отражено отсутствие runtime workflow-кода, отсутствие PDF templates в `templates/` и наличие только manual reference renderer в `employers/TaxDome/`;
  - следующий шаг после baseline сводится к одному contract-decision milestone.
- Validation commands:
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\resumes`
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\profile -Recurse`
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\templates -Recurse`
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\employers\TaxDome`
  - `Get-ChildItem C:\Users\avramko\OneDrive\Documents\Career\archive -Recurse -Include *.pdf,*.png`
  - `rg -n "export-resume-pdf|render_resume_pdf|pdf" C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\plans C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\README.md C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\src C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\tests`
- Notes / discoveries:
  - dedicated workflow ещё не реализован в коде;
  - `profile/contact-regions.yml` теперь уже существует и делает contact-region overlay реальным runtime input, а не hypothetical future file;
  - current repo содержит только один hardcoded historical renderer, поэтому M2 обязан жёстко отделить reference prototype от new runtime contract.

### M2. First Executable PDF Export Contract

- Status: `done`
- Goal:
  - закрепить минимальный, но полноценный contract для первой исполнимой версии `export-resume-pdf`.
- Deliverables:
  - решение по supported inputs и их precedence;
  - решение по durable PDF output path и render verification trail;
  - baseline dependency/render policy для generator и preview rendering.
- Acceptance criteria:
  - однозначно определено, какой resume source может экспортироваться первой версией и как накладывается profile metadata;
  - однозначно определено, где лежит final PDF, где лежат preview/report artifacts и что именно считается успешным run result;
  - policy не требует translation/hallucination layer и не заставляет workflow напрямую мутировать resume markdown.
- Validation commands:
  - `Get-Content -Raw C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\plans\2026-04-23-export-resume-pdf-workflow.md`
  - `Get-Content -Raw C:\Users\avramko\OneDrive\Documents\Career\profile\contact-regions.yml`
  - `Get-Content -Raw C:\Users\avramko\OneDrive\Documents\Career\employers\TaxDome\render_resume_pdf.py`
  - `Get-Content -Raw C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\pyproject.toml`
- Notes / discoveries:
  - first executable version принимает обязательный `target_resume`, где допустимы `MASTER`, `CIO`, `CTO`, `HoE`, `HoD`, `EM`; workflow экспортирует уже существующий markdown source, а не строит новый resume text;
  - `output_language` сохраняется в contract как явный input, но baseline-версия не переводит контент: она поддерживает только `ru` и должна падать с explicit error при запросе другого языка до появления отдельного bilingual resume source;
  - `contact_region` остаётся explicit input с supported values `RU`, `KZ`, `EU`; если не передан, baseline использует `profile/contact-regions.yml` default fallback (`EU`) и применяет overlay только к top-card contacts/location/public links;
  - optional `template_id` сохраняется в request contract, но первая версия поддерживает только встроенный `default`; `templates/` не становится blocking dependency до появления отдельного template milestone;
  - durable final artifact живёт в `profile/pdf/<target_resume>/<OUTPUT_LANGUAGE>-<CONTACT_REGION>.pdf`, потому что PDF — это публичный derivative profile output, а не runtime-only trace;
  - render verification trail живёт отдельно в `agent_memory/runtime/export-resume-pdf/<target_resume>/<OUTPUT_LANGUAGE>-<CONTACT_REGION>/` и включает как минимум `report.md` и preview PNG pages; preview generation входит в success contract и должна опираться на `pdftoppm`/Poppler либо завершаться явной dependency error без silent partial success;
  - baseline renderer stack закреплён как `reportlab` + deterministic markdown-to-layout projection; historical `employers/TaxDome/render_resume_pdf.py` используется только как reverse-engineering reference по typography/pagination ideas, но не как source-of-truth implementation path.

### M3. Markdown Projection And PDF Rendering Helpers

- Status: `done`
- Goal:
  - реализовать helper layer, который читает выбранный resume markdown, применяет contact-region overlay и детерминированно рендерит PDF + verification previews.
- Deliverables:
  - parser/projection module для resume markdown и contact overlay;
  - renderer module на `reportlab`;
  - preview helper и targeted tests на deterministic paths, invalid inputs и missing dependencies.
- Acceptance criteria:
  - helper layer не меняет исходный markdown resume и не invents content beyond selected source plus allowed profile surface overlay;
  - одинаковые inputs дают idempotent output paths и repeatable render summaries;
  - missing renderer/preview dependencies дают explicit validation error, а не partially-written success state.
- Validation commands:
  - `python -m unittest tests.test_export_resume_pdf_helpers`
- Notes / discoveries:
  - helper layer реализован в `src/application_agent/export_resume_pdf.py`: parser/projection читает выбранный resume markdown, применяет `contact_region` overlay только к contact/location/public-link surface, рендерит PDF через `reportlab` и пишет verification report + preview PNGs;
  - `reportlab` в текущем окружении не даёт побайтово стабильный PDF даже при одинаковом projection, поэтому idempotency helper layer закреплена через стабильный render fingerprint (`projection + renderer version`) и repeatable report/preview outputs, а не через raw PDF byte comparison;
  - staging/write path перенесён в workspace-local runtime area рядом с final preview/report outputs, чтобы не зависеть от системного `%TEMP%` и не оставлять partial success state при ошибке preview dependency.

### M4. Workflow, CLI And Runtime Verification Wiring

- Status: `done`
- Goal:
  - добавить executable workflow `export-resume-pdf` в runtime catalog с контролируемыми side effects только на agreed PDF outputs и runtime verification trail.
- Deliverables:
  - workflow module и request contract;
  - wiring в `registry`, `cli`, `config` и workflow memory catalog;
  - runtime report path under `agent_memory/runtime/export-resume-pdf/`;
  - workflow/CLI tests.
- Acceptance criteria:
  - `list-workflows` показывает `export-resume-pdf`;
  - successful run пишет только agreed PDF artifact, preview/report trail и workflow memory records;
  - invalid resume/language/contact-region/template/dependency inputs дают явную ошибку.
- Validation commands:
  - `python -m unittest tests.test_export_resume_pdf_helpers tests.test_export_resume_pdf_workflow tests.test_cli tests.test_memory_store`
  - `python run_agent.py --root ../.. list-workflows`
- Notes / discoveries:
  - Добавлен executable workflow `export-resume-pdf` с request normalization для `target_resume`, `output_language`, `contact_region` и `template_id`;
  - default `contact_region` теперь берётся из `profile/contact-regions.yml` (`defaults.contact_region_by_vacancy_country.default`) с fallback на `EU`, а final artifact contract остаётся `profile/pdf/<target_resume>/<language>-<region>.pdf`;
  - runtime verification report продолжает жить в `agent_memory/runtime/export-resume-pdf/<target_resume>/<language>-<region>/report.md`, а workflow memory записывает PDF, report и preview PNG files как явные artifacts;
  - public CLI, registry и `project_memory.workflow_catalog` теперь знают `export-resume-pdf`, а targeted tests покрывают workflow side effects, CLI routing и catalog bootstrap/upgrade.

### M5. Docs Sync, Full Validation And Master-Plan Handoff

- Status: `done`
- Goal:
  - синхронизировать docs, прогнать full validation baseline и закрыть handoff обратно в master plan после последнего remaining workflow.
- Deliverables:
  - README update;
  - при необходимости sync root docs по `profile/pdf/` outputs;
  - full validation baseline;
  - explicit handoff в master plan после завершения `export-resume-pdf`.
- Acceptance criteria:
  - docs объясняют inputs, output paths и verification expectations;
  - full relevant tests и CLI checks проходят;
  - master plan получает явный следующий шаг или completion update после последнего remaining workflow.
- Validation commands:
  - `python -m unittest discover -s tests`
  - `python run_agent.py --root ../.. list-workflows`
  - `python run_agent.py --root ../.. show-memory`
- Notes / discoveries:
  - `README.md` теперь описывает CLI-входы `export-resume-pdf`, итоговый PDF path, runtime verification trail и требование preview generation через `pdftoppm`/Poppler;
  - root-level `profile/README.md` синхронизирован с новым durable artifact family `profile/pdf/<target_resume>/<language>-<region>.pdf`;
  - full validation baseline после docs sync проходит: `python -m unittest discover -s tests` -> `OK (74 tests)`, `list-workflows` включает `export-resume-pdf`, `show-memory` исполняется успешно;
  - этот milestone закрывает последний remaining workflow в master sequencing, поэтому handoff возвращается не в следующий dedicated workflow plan, а в completion update master plan.

## Decision log

- `2026-04-23 10:08` — First executable PDF workflow закреплён как downstream derivative от уже существующего markdown resume (`MASTER` или one role resume), а не как новый content-generation stage. — Причина: canonical resume family уже стабилизирован отдельными workflows, и PDF export не должен становиться новым source-of-truth branch. — Это удерживает scope первой версии в рамках rendering, а не rewriting.
- `2026-04-23 10:08` — `output_language` сохранён в contract, но baseline-версия ограничена `ru` и не выполняет перевод содержимого. — Причина: current resume corpus уже authored на русском, а отдельного bilingual resume source пока нет; translation inside PDF export создала бы новый high-risk drift layer. — Это делает M3/M4 исполнимыми без генеративной локализации.
- `2026-04-23 10:08` — Durable PDF artifact живёт в `profile/pdf/...`, а preview/report trail — в `agent_memory/runtime/export-resume-pdf/...`. — Причина: root normalization уже закрепил `profile/` как home для durable profile derivatives, тогда как preview PNGs и technical reports являются verification artifacts, а не публичными deliverables. — Это не повторяет manual `tmp_pdf_preview/` contract из `employers/`.
- `2026-04-23 10:08` — Baseline renderer stack зафиксирован как встроенный `reportlab` renderer с обязательной preview verification через `pdftoppm`/Poppler и explicit dependency error при отсутствии preview toolchain. — Причина: PDF skill и historical prototype одинаково показывают, что без визуальной проверки layout нельзя считать экспорт надёжным. — Это заранее фиксирует quality gate до начала кодовой реализации.
- `2026-04-23 10:08` — External `templates/` не является blocking dependency первой версии; `template_id=default` остаётся встроенным contract value. — Причина: в репозитории пока нет PDF templates, и попытка ввести template system до базового renderer только распылит scope. — Future template packs остаются follow-up после working baseline.
- `2026-04-23 10:57` — Idempotency helper layer закреплена через render fingerprint и repeatable verification artifacts, а не через direct PDF byte equality. — Причина: `reportlab` в текущем окружении генерирует различающиеся PDF bytes при одинаковом projection, хотя layout contract и report surface остаются одинаковыми. — Это сохраняет детерминированность M3 без ложных `changed=True` на повторных identical runs.

## Progress log

- `2026-04-23 10:08` — Создан dedicated plan и закрыт baseline milestone M1 по текущему состоянию `resumes/`, `profile/contact-regions.yml`, `templates/`, historical manual renderer в `employers/TaxDome/` и existing PDF traces в `archive/`. — Validation опиралась на реальный root inventory, `pyproject.toml`, `README.md` и search по plans/src/tests. — Status: `in_progress`.
- `2026-04-23 10:08` — M2 contract milestone закрыт: first executable version теперь жёстко фиксирует source selection (`MASTER` или один role resume), `ru`-only baseline language policy, explicit `contact_region`, built-in `template_id=default`, durable output path under `profile/pdf/` и mandatory preview/report trail under `agent_memory/runtime/export-resume-pdf/`. — Validation выполнена повторным чтением dedicated plan, `profile/contact-regions.yml`, historical renderer и `pyproject.toml`; product ambiguity для M3 снята. — Status: `in_progress`.
- `2026-04-23 10:57` — M3 helper milestone завершён: добавлен модуль `application_agent.export_resume_pdf` с markdown projection, contact-region overlay, `reportlab` renderer, preview helper и render report generation; `pyproject.toml` теперь явно декларирует `reportlab`. — Validation: `python -m unittest tests.test_export_resume_pdf_helpers` -> `OK`. — Status: `in_progress`.
- `2026-04-23 14:59` — M4 завершён: добавлен workflow `src/application_agent/workflows/export_resume_pdf.py`, wiring в `registry`, `cli` и `config`, а новые tests `tests.test_export_resume_pdf_workflow` плюс обновлённые `tests.test_cli` и `tests.test_memory_store` подтверждают controlled side effects, CLI routing и runtime catalog bootstrap. — Validation: `python -m unittest tests.test_export_resume_pdf_helpers tests.test_export_resume_pdf_workflow tests.test_cli tests.test_memory_store` -> `OK`; `python run_agent.py --root ../.. list-workflows` показывает `export-resume-pdf`. — Status: `in_progress`.
- `2026-04-23 15:04` — M5 завершён: operator docs в `README.md` и root profile docs в `profile/README.md` синхронизированы с final PDF contract, после чего full validation baseline подтверждён (`python -m unittest discover -s tests` -> `OK (74 tests)`, `python run_agent.py --root ../.. list-workflows`, `python run_agent.py --root ../.. show-memory`). — Dedicated plan переведён в `done` и отдаёт handoff обратно в master plan как для последнего remaining workflow. — Status: `done`.

## Current state

- Current milestone: `completed`
- Current status: `done`
- Next step: `Вернуться в master plan `2026-04-21-repository-reconstruction-and-backlog.md` и отметить очередь remaining workflows полностью завершённой.`
- Active blockers:
  - none
- Open questions:
  - none

## Completion summary

Завершён executable workflow `export-resume-pdf`: публичный CLI, request contract, deterministic PDF output path, verification trail и workflow memory теперь согласованы и задокументированы.

Провалидировано:

- `python -m unittest discover -s tests` -> `OK (74 tests)`
- `python run_agent.py --root ../.. list-workflows`
- `python run_agent.py --root ../.. show-memory`

Follow-up вне этого dedicated plan:

- отдельный template system для PDF beyond `template_id=default`;
- поддержка дополнительных языков только после появления отдельного bilingual resume source.

Остаточный риск один и он уже зафиксирован в контракте: preview generation зависит от внешнего `pdftoppm`/Poppler и при его отсутствии workflow должен завершаться явной ошибкой.

Затронутые root-level artifacts: обновлён `C:\Users\avramko\OneDrive\Documents\Career\profile\README.md`; durable PDF outputs и runtime previews этим milestone не генерировались.
