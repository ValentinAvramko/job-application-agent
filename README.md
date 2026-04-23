# Application Agent

Публичный код агента для сопровождения карьерного workflow.

## Что уже есть

- файловый `JsonMemoryStore` для трёх слоёв памяти и журнала запусков;
- registry workflow;
- CLI setup-команда `bootstrap` для private workspace;
- workflow `ingest-vacancy`, который создаёт каркас вакансии и обновляет runtime-память;
- стартовый workflow `analyze-vacancy`, который выбирает ролевое резюме и собирает первый fit-анализ;
- workflow `intake-adoptions`, который переносит vacancy-local `adoptions.md` в root review layer (`adoptions/inbox/` + `adoptions/questions/open.md`);
- workflow `prepare-screening`, который по готовой вакансии собирает vacancy-local `screening.md` для первичного интервью;
- workflow `rebuild-master`, который синхронизирует managed approved-signals section в `resumes/MASTER.md` из `adoptions/accepted/MASTER.md` и пишет runtime report в `agent_memory/runtime/rebuild-master/latest.md`.
- workflow `rebuild-role-resume`, который синхронизирует managed canonical block в выбранном `resumes/<role>.md` из уже согласованного `resumes/MASTER.md` и optional `knowledge/roles/<role>.md`.
- workflow `build-linkedin`, который собирает per-role LinkedIn draft pack в `profile/linkedin/<target_role>.md` из canonical `MASTER`, выбранного role resume и optional profile metadata, а runtime report пишет в `agent_memory/runtime/build-linkedin/<target_role>.md`.
- workflow `export-resume-pdf`, который рендерит проверяемый PDF-артефакт из `resumes/MASTER.md` или выбранного `resumes/<role>.md`, пишет итоговый файл в `profile/pdf/<target_resume>/<language>-<region>.pdf` и сохраняет verification trail в `agent_memory/runtime/export-resume-pdf/<target_resume>/<language>-<region>/`.

## Структура private workspace

Агент ожидает, что private repo содержит каталоги:

- `vacancies/`
- `adoptions/`
- `knowledge/`
- `profile/`
- `agent_memory/`

## Быстрый старт

```powershell
python run_agent.py --root ../.. bootstrap
python run_agent.py --root ../.. list-workflows
python run_agent.py --root ../.. ingest-vacancy --company "Example" --position "Engineering Manager" --source-channel "Manual" --source-text "Short vacancy text"
python run_agent.py --root ../.. analyze-vacancy --vacancy-id 20260420-example-engineering-manager
python run_agent.py --root ../.. intake-adoptions --vacancy-id 20260420-example-engineering-manager
python run_agent.py --root ../.. prepare-screening --vacancy-id 20260420-example-engineering-manager
python run_agent.py --root ../.. rebuild-master
python run_agent.py --root ../.. rebuild-role-resume --target-role CTO
python run_agent.py --root ../.. build-linkedin --target-role CTO
python run_agent.py --root ../.. export-resume-pdf --target-resume CTO --contact-region EU
python run_agent.py --root ../.. show-memory
```

Что делает каждая команда:

- `python run_agent.py --root ../.. bootstrap`
  Проверяет и создаёт базовую структуру рабочего каталога агента в указанном root. Это setup-команда, а не runtime workflow.
- `python run_agent.py --root ../.. list-workflows`
  Показывает доступные runtime workflow, которые можно запускать через CLI. Setup-команда `bootstrap` в этот список не входит.
- `python run_agent.py --root ../.. ingest-vacancy --company "Example" --position "Engineering Manager" --source-channel "Manual" --source-text "Short vacancy text"`
  Создаёт карточку вакансии, заполняет `meta.yml`, `source.md`, `analysis.md`, `adoptions.md`, добавляет строку в `response-monitoring.xlsx` и обновляет runtime memory.
  Перед запуском в root workspace должен существовать валидный `response-monitoring.xlsx`; без него `ingest-vacancy` завершится ошибкой и не создаст vacancy scaffold.
  Публикация в git не выполняется автоматически: commit/push остаются отдельным ручным шагом по `tooling/git-workflow.md`.
- `python run_agent.py --root ../.. analyze-vacancy --vacancy-id 20260420-example-engineering-manager`
  Выполняет стартовый анализ уже созданной вакансии: подбирает ролевое резюме и формирует начальный fit-анализ.
- `python run_agent.py --root ../.. intake-adoptions --vacancy-id 20260420-example-engineering-manager`
  Нормализует vacancy-local `adoptions.md` в root review layer: рендерит `adoptions/inbox/<vacancy_id>.md` и синхронизирует initial unresolved items в `adoptions/questions/open.md`.
  Это deterministic intake stage, а не review/acceptance session: сама review-сессия остаётся agent-guided и опирается на helper APIs и runbook `agent_memory/workflows/adoptions-review.md`.
- `python run_agent.py --root ../.. prepare-screening --vacancy-id 20260420-example-engineering-manager`
  По уже ingest/analyze-подготовленной вакансии создаёт `vacancies/<vacancy_id>/screening.md`, обновляет `meta.yml` до статуса `screening_prepared` и пишет runtime memory без Excel или git side effects.
  Обязательные входы: существующий `vacancy_id`, уже собранные `meta.yml`, `source.md`, `analysis.md`; опционально можно передать `--selected-resume`, `--output-language` и `--preparation-depth`.
- `python run_agent.py --root ../.. rebuild-master`
  Читает current-state approved signals из `adoptions/accepted/MASTER.md`, детерминированно синхронизирует managed block в `resumes/MASTER.md` и обновляет runtime report `agent_memory/runtime/rebuild-master/latest.md`.
  Workflow не переписывает narrative sections целиком: baseline-версия управляет только секцией `Approved Permanent Signals`, чтобы downstream `rebuild-role-resume` и `build-linkedin` читали уже согласованный `MASTER`.
- `python run_agent.py --root ../.. rebuild-role-resume --target-role CTO`
  Читает managed approved-signals section из `resumes/MASTER.md`, optional shaping bullets из `knowledge/roles/CTO.md` и детерминированно синхронизирует managed block в `resumes/CTO.md`.
  Baseline-версия не делает full rewrite всего role resume: она обновляет только parseable managed block и пишет per-role runtime report в `agent_memory/runtime/rebuild-role-resume/CTO.md`.
- `python run_agent.py --root ../.. build-linkedin --target-role CTO`
  Читает canonical `resumes/MASTER.md`, выбранное `resumes/CTO.md` и optional `profile/contact-regions.yml`, затем детерминированно собирает bilingual draft pack в `profile/linkedin/CTO.md`.
  Артефакт содержит executive summary, RU и EN ready-to-paste blocks, filling guide и `GAP` list; private contacts не попадают автоматически в public-ready copy, а runtime report пишется в `agent_memory/runtime/build-linkedin/CTO.md`.
- `python run_agent.py --root ../.. export-resume-pdf --target-resume CTO --contact-region EU`
  Читает `resumes/MASTER.md` или выбранное `resumes/<role>.md`, применяет public contact overlay из `profile/contact-regions.yml` только к верхнему contact/location surface и рендерит PDF в `profile/pdf/CTO/ru-EU.pdf`.
  `--target-resume` обязателен; `--output-language` в baseline поддерживает только `ru`, `--contact-region` принимает `RU`, `KZ`, `EU` и по умолчанию берётся из `profile/contact-regions.yml` (иначе `EU`), `--template-id` сейчас поддерживает только `default`.
  Успешный run обязан сохранить `report.md` и preview PNG pages в `agent_memory/runtime/export-resume-pdf/CTO/ru-EU/`; если отсутствует `pdftoppm` из Poppler, workflow завершается явной ошибкой вместо partial success.
- `python run_agent.py --root ../.. show-memory`
  Показывает текущее содержимое файловой памяти агента: задачи, артефакты и журнал запусков workflow, а также reconciliation-сводку по отсутствующим vacancy artifacts.

`analyze-vacancy` также умеет стартовать без готового `vacancy_id`, если передать `--company`, `--position` и текст вакансии.

Текущий sequencing для adoptions workflow family:

1. `analyze-vacancy` создаёт vacancy-local draft `vacancies/<id>/adoptions.md`.
2. `intake-adoptions` переносит draft в root review stores `adoptions/inbox/` и `adoptions/questions/open.md`.
3. Agent-guided review stage читает context через helper APIs из `application_agent.adoptions_review` и применяет approved updates в `adoptions/accepted/MASTER.md`.
4. Только после этого downstream workflow `rebuild-master` должен обновлять `resumes/MASTER.md`.
5. Только после синхронизации `MASTER` workflow `rebuild-role-resume` должен обновлять конкретное `resumes/<role>.md` из canonical resume и optional `knowledge/roles/<role>.md`, а не из raw vacancy corpus или `adoptions/accepted/` напрямую.
6. Только после этого downstream workflow `build-linkedin` должен читать обновлённый canonical resume family и собирать `profile/linkedin/<target_role>.md`.
7. Только после этого downstream workflow `export-resume-pdf` должен читать уже стабилизированные resume/profile derivatives и собирать durable PDF artifact в `profile/pdf/<target_resume>/` вместе с verification trail в `agent_memory/runtime/export-resume-pdf/<target_resume>/`.

Подробный пошаговый сценарий первого рабочего прогона в private workspace лежит в [tooling/run-ingest-analyze.md](/C:/Users/avramko/OneDrive/Documents/Career/tooling/run-ingest-analyze.md).

## Архитектура ingest-vacancy

После рефакторинга `ingest-vacancy` разделён на несколько слоёв с разной ответственностью:

- `src/application_agent/workflows/ingest_vacancy.py`
  orchestration-слой workflow: принимает request, запускает enrichment, пишет артефакты вакансии, обновляет runtime memory и инициирует запись в Excel.
- `src/application_agent/workflows/vacancy_sources.py`
  source/provider-слой: загрузка страницы, парсинг HH и generic career sites, normalisation извлечённых данных, fallback на Playwright для JS-heavy страниц.
- `src/application_agent/workflows/vacancy_rendering.py`
  rendering-слой: генерация `meta.yml`, `source.md`, `analysis.md`, `adoptions.md`.
- `src/application_agent/integrations/response_monitoring.py`
  доменная интеграция с `response-monitoring.xlsx`: проверка mandatory workbook prerequisite, добавление строки ingest и возврат `excel_row`.
- `src/application_agent/integrations/playwright_renderer.py`
  isolated browser fallback для сайтов, где обычный HTML-fetch не даёт полного содержимого вакансии.
- `src/application_agent/normalization/`
  data-driven нормализация справочников и соответствий: страны, source channels, generic page rules.
- `src/application_agent/utils/placeholders.py`
  единая placeholder-policy для значений вроде `нет данных` и `Не указано`.

Ключевые принципы текущей архитектуры:

- workflow должен оперировать доменными сущностями, а не знать детали XLSX, HTML parser internals или справочников;
- справочные данные и соответствия выносятся в data-файлы и отдельные normalisation-модули;
- rendering, parsing и integration logic не должны смешиваться в одном файле;
- browser automation через Playwright включается только как fallback, а не как основной путь ingest.

## Следующие шаги

- более точный fit scoring;
- постоянная память по подтверждённым сигналам;
- orchestration для следующих workflow;
- дополнительная стабилизация generic-page extraction и критериев включения Playwright fallback.

Если агент запускается не из submodule, а из корня private repo, можно передать `--root .`.
