# Application Agent

Публичный код агента для сопровождения карьерного workflow.

## Что уже есть

- файловый `JsonMemoryStore` для трёх слоёв памяти и журнала запусков;
- registry workflow;
- CLI bootstrap для private workspace;
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

`analyze-vacancy` также умеет стартовать без готового `vacancy_id`, если передать `--company`, `--position` и текст вакансии.

Подробный пошаговый сценарий первого рабочего прогона в private workspace лежит в [tooling/run-ingest-analyze.md](/C:/Users/avramko/OneDrive/Documents/Career/tooling/run-ingest-analyze.md).

## Следующие шаги

- более точный fit scoring;
- обновление Excel;
- постоянная память по подтверждённым сигналам;
- orchestration для следующих workflow.

Если агент запускается не из submodule, а из корня private repo, можно передать `--root .`.
