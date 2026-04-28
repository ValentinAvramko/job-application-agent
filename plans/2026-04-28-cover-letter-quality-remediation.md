# План исправления качества сопроводительного письма `analyze-vacancy`

- Статус: `done`
- Текущий шаг: `completed`

## Этапы

| ID | Название | Статус |
| --- | --- | --- |
| M1 | Runtime-промпты и защита от mojibake | done |
| M2 | Подпись из `contact-regions.yml` | done |
| M3 | Отдельный humanizer-pass | done |
| M4 | LLM выбирает фактуру для письма | done |
| M5 | Quality-mode модели и meta | done |

## Валидация

- Targeted: `python -m pytest tests/test_analyze_workflow.py tests/test_cli.py` -> `24 passed`
- Full: `python -m pytest tests` -> `89 passed`
- Smoke: `job-application-agent --root ./ analyze-vacancy --vacancy-id 20260423-fintehrobot-head-of-development-rukovoditel-razrabotki` -> `completed`

## Заметки

- Подпись берется из `profile/contact-regions.yml`.
- Humanizer-pass оставлен отдельным postprocessor для OpenAI provider.
- `cover_letter_evidence` выбирает LLM; код только передает полный подтвержденный контекст и валидирует форму.
