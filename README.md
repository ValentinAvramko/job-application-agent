# Application Agent

Публичный код агента для сопровождения карьерного workflow.

## Что уже есть

- файловый `JsonMemoryStore` для трёх слоёв памяти и журнала запусков;
- registry workflow;
- CLI bootstrap для private workspace;
- стартовый workflow `ingest-vacancy`, который создаёт каркас вакансии и обновляет runtime-память.

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
python run_agent.py --root ../.. show-memory
```

## Следующие шаги

- анализ вакансии и fit scoring;
- обновление Excel;
- постоянная память по подтверждённым сигналам;
- orchestration для следующих workflow.

Если агент запускается не из submodule, а из корня private repo, можно передать `--root .`.

