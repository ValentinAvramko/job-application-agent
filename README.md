# Application Agent

Публичный код агента для сопровождения карьерного workflow.

## Что уже есть

- файловый `JsonMemoryStore` для трёх слоёв памяти и журнала запусков;
- registry workflow;
- CLI setup-команда `bootstrap` для private workspace;
- workflow `ingest-vacancy`, который создаёт каркас вакансии и обновляет runtime-память;
- стартовый workflow `analyze-vacancy`, который выбирает ролевое резюме и собирает первый fit-анализ.

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
- `python run_agent.py --root ../.. show-memory`
  Показывает текущее содержимое файловой памяти агента: задачи, артефакты и журнал запусков workflow, а также reconciliation-сводку по отсутствующим vacancy artifacts.

`analyze-vacancy` также умеет стартовать без готового `vacancy_id`, если передать `--company`, `--position` и текст вакансии.

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
