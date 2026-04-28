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
  - `agent_memory/config/` — локальные runtime-настройки CLI, например defaults для LLM.

## Быстрый старт

```powershell
python job-application-agent.py --root ../.. bootstrap
python job-application-agent.py --root ../.. list-workflows
python job-application-agent.py --root ../.. ingest-vacancy --company "Example" --position "Engineering Manager" --source-channel "Manual" --source-text "Short vacancy text"
python job-application-agent.py --root ../.. analyze-vacancy --vacancy-id 20260420-example-engineering-manager
python job-application-agent.py --root ../.. intake-adoptions --vacancy-id 20260420-example-engineering-manager
python job-application-agent.py --root ../.. prepare-screening --vacancy-id 20260420-example-engineering-manager
python job-application-agent.py --root ../.. rebuild-master
python job-application-agent.py --root ../.. rebuild-role-resume --target-role CTO
python job-application-agent.py --root ../.. build-linkedin --target-role CTO
python job-application-agent.py --root ../.. export-resume-pdf --target-resume CTO --contact-region EU
python job-application-agent.py --root ../.. show-memory
```

После установки пакета в editable-режиме можно запускать без `python ...py`:

```powershell
python -m pip install -e .
job-application-agent --root ../.. list-workflows
```

На Windows `pip` может поставить `job-application-agent.exe` в user Scripts directory, который не добавлен в `PATH`. В этом случае PowerShell покажет warning вида:

```text
The scripts ... are installed in 'C:\Users\<user>\AppData\Roaming\Python\Python314\Scripts' which is not on PATH.
```

Проверить команду сразу можно по полному пути:

```powershell
& "$env:APPDATA\Python\Python314\Scripts\job-application-agent.exe" --root ../.. list-workflows
```

Чтобы команда работала в новых терминалах без полного пути, добавь Scripts directory в пользовательский `PATH`:

```powershell
$scripts = "$env:APPDATA\Python\Python314\Scripts"
[Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path", "User") + ";$scripts", "User")
```

После этого открой новый PowerShell и проверь:

```powershell
job-application-agent --root ../.. list-workflows
```

## Настройка LLM для `analyze-vacancy`

`analyze-vacancy` по умолчанию использует `llm_provider=openai` и OpenAI Responses API. Для реального запуска обязательны:

- `OPENAI_API_KEY` в окружении или в `agent_memory/config/secrets.json`;
- модель через `--llm-model`, `APPLICATION_AGENT_LLM_MODEL` или config-файл.

Несекретные defaults можно держать в workspace-файле `agent_memory/config/application-agent.json`:

```json
{
  "analyze-vacancy": {
    "llm_provider": "openai",
    "llm_model": "gpt-5.4",
    "llm_reasoning_effort": "high",
    "llm_reasoning_summary": "auto",
    "llm_text_verbosity": "medium",
    "target_mode": "balanced",
    "include_employer_channels": false
  }
}
```

Текущая версия `application-agent` поддерживает в `application-agent.json` только секцию `analyze-vacancy`.

| Ключ | Тип | Значение по умолчанию | Описание |
| --- | --- | --- | --- |
| `llm_provider` | string | `openai` | LLM-provider для анализа. Поддерживаются `openai` и `fake`; `fake` нужен для локального smoke-теста без сетевого вызова. |
| `llm_model` | string | `""` | Модель для реального LLM-запуска. Для `llm_provider=openai` обязательна: через config, `--llm-model` или `APPLICATION_AGENT_LLM_MODEL`. |
| `llm_temperature` | number/null | `null` | Опциональная температура. Для GPT-5.4 mini по умолчанию не задаётся; основной контроль качества идёт через reasoning settings. |
| `llm_reasoning_effort` | string | `""` | Усилие reasoning для Responses API: обычно `low`, `medium` или `high`. Для текущего агента рекомендуется `medium`. |
| `llm_reasoning_summary` | string | `""` | Настройка summary reasoning, если модель и аккаунт её поддерживают. Для отладки удобно `auto`. |
| `llm_text_verbosity` | string | `""` | Verbosity текстового ответа Responses API. Для этого workflow рекомендуется `medium`: достаточно подробно, но без лишней воды. |
| `target_mode` | string | `""` | Режим позиционирования: `conservative`, `balanced`, `aggressive`. Если не задан, workflow берёт значение из `meta.yml` или использует `balanced` при ingest. |
| `selected_resume` | string | `""` | Ручной override выбора резюме. Обычно лучше не задавать глобально, чтобы workflow сам выбирал роль под вакансию. |
| `russian_text_skill_path` | string | `""` | Путь к обязательному skill `humanize-russian-business-text` для русскоязычной генерации. Если не задан, используются `APPLICATION_AGENT_RUSSIAN_TEXT_SKILL_PATH`, `~/.agents/skills/...`, затем `~/.codex/skills/...`. |
| `include_employer_channels` | boolean | `false` | Включает employer-facing каналы в анализ там, где workflow это учитывает. Для обычного анализа вакансии рекомендуется `false`. |

Рекомендованный текущий набор `llm_*`:

```json
{
  "llm_provider": "openai",
  "llm_model": "gpt-5.4",
  "llm_reasoning_effort": "high",
  "llm_reasoning_summary": "auto",
  "llm_text_verbosity": "medium",
  "russian_text_skill_path": "C:\\Users\\avramko\\.agents\\skills\\humanize-russian-business-text\\SKILL.md"
}
```

Почему так:

- `analyze-vacancy` строит evidence pack, выбирает ролевое резюме, проверяет требования и просит модель вернуть строгий JSON. Responses API с structured output лучше соответствует этому контракту, чем legacy Chat Completions.
- `gpt-5.4-mini` выбран как стартовый баланс качества, стоимости и скорости для регулярного анализа вакансий.
- `llm_reasoning_effort=medium` даёт модели достаточно reasoning для сопоставления требований и фактов, но не делает каждый запуск максимально дорогим.
- `llm_text_verbosity=medium` подходит для `analysis.md` и `adoptions.md`: результат должен быть содержательным, но не расползаться.
- Для русского результата `analyze-vacancy` обязательно загружает skill `humanize-russian-business-text` и передаёт его текст модели. Без доступного skill workflow должен завершиться ошибкой.

Для финальных запусков сопроводительного письма нужно использовать `gpt-5.4` или более сильную модель с `llm_reasoning_effort=high` и `llm_text_verbosity=medium`. Режим `gpt-5.4-mini` с `medium` reasoning допустим для smoke-проверок и черновиков, но не является рекомендуемым финальным режимом для писем под конкретную вакансию.

Для русскоязычного результата `analyze-vacancy` выполняет отдельный humanizer-pass для `cover_letter_standard` и `cover_letter_short`. Этот проход является обязательным quality gate для OpenAI provider и не должен добавлять новые факты; итоговая подпись добавляется кодом из `profile/contact-regions.yml`.

Prompt-тексты `analyze-vacancy` лежат вне Python-кода. Приоритет:

1. `agent_memory/prompts/analyze-vacancy/system.ru.md`
2. `agent_memory/prompts/analyze-vacancy/task.ru.md`
3. `agent_memory/prompts/analyze-vacancy/cover-letter-contract.ru.md`

Если root-файла нет, используется packaged default из `src/application_agent/data/prompts/analyze-vacancy/`.

Секреты в `application-agent.json` не записываются. Для локального API key используется `agent_memory/config/secrets.json`, который должен быть в `.gitignore`:

```json
{
  "OPENAI_API_KEY": "sk-...",
  "OPENAI_BASE_URL": "https://api.openai.com/v1"
}
```

Окружение имеет приоритет над `secrets.json`, поэтому временно переопределить ключ можно так:

```powershell
$env:OPENAI_API_KEY = "sk-..."
python job-application-agent.py --root ../.. analyze-vacancy --vacancy-id 20260420-example-engineering-manager
```

Приоритет настроек: явные CLI-аргументы выше config-файла, config-файл выше встроенных defaults. Альтернативный путь к config можно передать глобальным параметром до имени команды:

```powershell
python job-application-agent.py --root ../.. --config ..\..\agent_memory\config\application-agent.json analyze-vacancy --vacancy-id 20260420-example-engineering-manager
```

Для smoke-запуска без сетевого LLM можно использовать fake provider:

```powershell
python job-application-agent.py --root ../.. analyze-vacancy --vacancy-id 20260420-example-engineering-manager --llm-provider fake --llm-model test
```

## Тесты

```powershell
python -m pytest tests
```

Что делает каждая команда:

- `python job-application-agent.py --root ../.. bootstrap`
  Проверяет и создаёт базовую структуру рабочего каталога агента в указанном root. Это setup-команда, а не runtime workflow.
- `python job-application-agent.py --root ../.. list-workflows`
  Показывает доступные runtime workflow, которые можно запускать через CLI. Setup-команда `bootstrap` в этот список не входит.
- `python job-application-agent.py --root ../.. ingest-vacancy --company "Example" --position "Engineering Manager" --source-channel "Manual" --source-text "Short vacancy text"`
  Создаёт карточку вакансии, заполняет `meta.yml`, `source.md`, `analysis.md`, `adoptions.md`, добавляет строку в `response-monitoring.xlsx` и обновляет runtime memory.
  Перед запуском в root workspace должен существовать валидный `response-monitoring.xlsx`; без него `ingest-vacancy` завершится ошибкой и не создаст vacancy scaffold.
  Публикация в git не выполняется автоматически: commit/push остаются отдельным ручным шагом по `tooling/git-workflow.md`.
- `python job-application-agent.py --root ../.. analyze-vacancy --vacancy-id 20260420-example-engineering-manager`
  Выполняет стартовый анализ уже созданной вакансии: подбирает ролевое резюме и формирует начальный fit-анализ.
  Для реального LLM-запуска нужны `OPENAI_API_KEY` и модель. Ключ можно положить в `agent_memory/config/secrets.json`, а модель — передать через `--llm-model`, `APPLICATION_AGENT_LLM_MODEL` или `agent_memory/config/application-agent.json`.
- `python job-application-agent.py --root ../.. intake-adoptions --vacancy-id 20260420-example-engineering-manager`
  Нормализует vacancy-local `adoptions.md` в root review layer: рендерит `adoptions/inbox/<vacancy_id>.md` и синхронизирует initial unresolved items в `adoptions/questions/open.md`.
  Это deterministic intake stage, а не review/acceptance session: сама review-сессия остаётся agent-guided и опирается на helper APIs и runbook `agent_memory/workflows/adoptions-review.md`.
- `python job-application-agent.py --root ../.. prepare-screening --vacancy-id 20260420-example-engineering-manager`
  По уже ingest/analyze-подготовленной вакансии создаёт `vacancies/<vacancy_id>/screening.md`, обновляет `meta.yml` до статуса `screening_prepared` и пишет runtime memory без Excel или git side effects.
  Обязательные входы: существующий `vacancy_id`, уже собранные `meta.yml`, `source.md`, `analysis.md`; опционально можно передать `--selected-resume`, `--output-language` и `--preparation-depth`.
- `python job-application-agent.py --root ../.. rebuild-master`
  Читает current-state approved signals из `adoptions/accepted/MASTER.md`, детерминированно синхронизирует managed block в `resumes/MASTER.md` и обновляет runtime report `agent_memory/runtime/rebuild-master/latest.md`.
  Workflow не переписывает narrative sections целиком: baseline-версия управляет только секцией `Approved Permanent Signals`, чтобы downstream `rebuild-role-resume` и `build-linkedin` читали уже согласованный `MASTER`.
- `python job-application-agent.py --root ../.. rebuild-role-resume --target-role CTO`
  Читает managed approved-signals section из `resumes/MASTER.md`, optional shaping bullets из `knowledge/roles/CTO.md` и детерминированно синхронизирует managed block в `resumes/CTO.md`.
  Baseline-версия не делает full rewrite всего role resume: она обновляет только parseable managed block и пишет per-role runtime report в `agent_memory/runtime/rebuild-role-resume/CTO.md`.
- `python job-application-agent.py --root ../.. build-linkedin --target-role CTO`
  Читает canonical `resumes/MASTER.md`, выбранное `resumes/CTO.md` и optional `profile/contact-regions.yml`, затем детерминированно собирает bilingual draft pack в `profile/linkedin/CTO.md`.
  Артефакт содержит executive summary, RU и EN ready-to-paste blocks, filling guide и `GAP` list; private contacts не попадают автоматически в public-ready copy, а runtime report пишется в `agent_memory/runtime/build-linkedin/CTO.md`.
- `python job-application-agent.py --root ../.. export-resume-pdf --target-resume CTO --contact-region EU`
  Читает `resumes/MASTER.md` или выбранное `resumes/<role>.md`, применяет public contact overlay из `profile/contact-regions.yml` только к верхнему contact/location surface и рендерит PDF в `profile/pdf/CTO/ru-EU.pdf`.
  `--target-resume` обязателен; `--output-language` в baseline поддерживает только `ru`, `--contact-region` принимает `RU`, `KZ`, `EU` и по умолчанию берётся из `profile/contact-regions.yml` (иначе `EU`), `--template-id` сейчас поддерживает только `default`.
  Успешный run обязан сохранить `report.md` и preview PNG pages в `agent_memory/runtime/export-resume-pdf/CTO/ru-EU/`; если отсутствует `pdftoppm` из Poppler, workflow завершается явной ошибкой вместо partial success.
- `python job-application-agent.py --root ../.. show-memory`
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
