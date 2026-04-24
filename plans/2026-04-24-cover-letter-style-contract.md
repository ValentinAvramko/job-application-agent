# Контракт стиля сопроводительного письма

- Название: `контракт стиля сопроводительного письма`
- Slug: `2026-04-24-cover-letter-style-contract`
- Ответственный: `Codex`
- Создан: `2026-04-24`
- Обновлен: `2026-04-24 15:45`
- Общий статус: `done`

## Цель

Закрепить в `analyze-vacancy` правила качества сопроводительного письма так, чтобы реальный LLM-запуск получал явный стилевой контракт, а оба варианта письма всегда завершались фиксированной подписью кандидата.

## Контекст

Текущий workflow `analyze-vacancy` уже LLM-backed, но системный prompt в `src/application_agent/workflows/analyze_vacancy.py` слишком общий. Legacy prompt `promts/promt-analyze-vacancies-and-respond.md` содержит более точные правила для сопроводительного письма и указывает на обязательное применение humanizer-правил, но этот файл отмечен как исторический reference и не является runtime-контрактом.

Пользователь указал, что качество письма после анализа вакансии неубедительное, и попросил зафиксировать подпись:

```text
Валентин Аврамко
Telegram: @ValentinAvramko
```

## Границы

### Входит в scope

- Добавить явный runtime contract для сопроводительного письма в LLM input.
- Зафиксировать подпись для `cover_letter_standard` и `cover_letter_short` постобработкой.
- Улучшить deterministic fake provider, чтобы он не писал внутренние фразы про выбор файла резюме.
- Добавить pytest coverage для подписи и LLM payload contract.
- Обновить operator-facing документацию workflow.

### Не входит в scope

- Полный redesign `analysis.md`.
- Отдельный `cover-letter.md`.
- Переписывание уже созданных vacancy artifacts.
- Изменение root legacy prompt как source of truth.

## Допущения

- Подпись нужна в обоих вариантах письма.
- Runtime tool не должен зависеть от локального Codex skill-файла; нужные humanizer-правила фиксируются в явном контракте.
- Legacy prompt можно использовать как reference, но действующий источник поведения должен быть в коде и workflow docs.

## Риски и неизвестные

- Стилевой contract снижает риск шаблонного текста, но не гарантирует идеальное качество каждого real LLM-output без human review.
- Слишком жёсткий prompt может сделать письма осторожнее; это приемлемо, потому что factual boundary важнее рекламного тона.

## Внешние точки касания

- `C:\Users\avramko\OneDrive\Documents\Career\agent_memory\workflows\analyze-vacancy.md` - обновление - описать действующий contract письма и подпись.
- `C:\Users\avramko\OneDrive\Documents\Career\promts\promt-analyze-vacancies-and-respond.md` - чтение - сверить legacy-правила письма и подписи.

## Этапы

### M1. Runtime contract и подпись

- Статус: `done`
- Цель:
  - Закрепить стиль письма и подпись в runtime-поведении `analyze-vacancy`.
- Артефакты:
  - `src/application_agent/workflows/analyze_vacancy.py`
  - `tests/test_analyze_workflow.py`
  - `agent_memory/workflows/analyze-vacancy.md`
- Критерии приемки:
  - LLM payload содержит `cover_letter_contract`.
  - Оба варианта письма в `analysis.md` содержат фиксированную подпись.
  - Deterministic fake provider не использует внутренние фразы про выбранный файл резюме в письмах.
- Команды валидации:
  - `python -m pytest tests/test_analyze_workflow.py`
- Заметки:
  - добавлен `cover_letter_contract` в OpenAI-compatible request payload;
  - подпись добавляется в `validate_llm_package` для обоих вариантов письма;
  - deterministic fake provider больше не пишет в письмах внутренние формулировки про выбор версии резюме;
  - full validation: `python -m pytest tests` -> `87 passed`.

## Журнал решений

- `2026-04-24 15:30` - Runtime contract должен жить в коде и workflow docs, а не в legacy prompt. - Иначе real LLM-запуск не получает правил письма и humanizer-ограничений.
- `2026-04-24 15:30` - Подпись добавляется постобработкой. - Это надёжнее, чем просить модель каждый раз не забывать подпись.

## Журнал прогресса

- `2026-04-24 15:30` - План создан, M1 начат. - Валидация pending. - Статус: `in_progress`.
- `2026-04-24 15:45` - M1 завершён: runtime contract письма, постобработка подписи, тесты и workflow docs обновлены. - Валидация: `python -m pytest tests/test_analyze_workflow.py` -> `9 passed`; `python -m pytest tests` -> `87 passed`. - Статус: `done`.

## Текущее состояние

- Текущий milestone: `M1`
- Текущий статус: `done`
- Следующий шаг: `Следующих implementation steps по этому плану нет.`
- Активные блокеры:
  - нет
- Открытые вопросы:
  - нет

## Итог завершения

- Поставлен явный runtime contract для сопроводительного письма в LLM payload.
- Оба варианта письма гарантированно получают подпись:

```text
Валентин Аврамко
Telegram: @ValentinAvramko
```

- Workflow docs синхронизированы в `agent_memory/workflows/analyze-vacancy.md`.
- Валидация завершена: targeted analyze tests и full pytest suite проходят.
