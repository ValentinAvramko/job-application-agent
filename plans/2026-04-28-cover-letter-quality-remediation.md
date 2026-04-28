# Исправление качества сопроводительного письма `analyze-vacancy`

- Название: `исправление качества сопроводительного письма analyze-vacancy`
- Slug: `2026-04-28-cover-letter-quality-remediation`
- Ответственный: `Codex`
- Создан: `2026-04-28`
- Обновлен: `2026-04-28 23:40`
- Общий статус: `done`

## Цель

Сделать генерацию сопроводительного письма в `analyze-vacancy` управляемой, проверяемой и пригодной для финального отклика:

- runtime prompt overrides должны читаться как нормальный UTF-8 и не пропускать mojibake в LLM-вызов;
- подпись должна формироваться из `profile/contact-regions.yml`, а не из hardcoded строки в коде;
- письмо должно проходить отдельный humanizer-pass;
- LLM должна видеть полный подтвержденный контекст и возвращать проверяемый список фактов для письма;
- финальный режим модели должен быть зафиксирован как quality-mode, а не smoke/draft-mode.

## Контекст

Проблема была обнаружена на вакансии `20260423-fintehrobot-head-of-development-rukovoditel-razrabotki`.

До исправления `analyze-vacancy` создавал письмо, которое:

- было технически валидным, но слабее эталонного письма по релевантности к вакансии;
- теряло сильную фактуру из выбранного ролевого резюме и `MASTER.md`;
- добавляло дублирующую подпись и могло оставлять placeholders вида `[Имя]` / `[Telegram]`;
- полагалось на один LLM-pass, где humanizer-инструкции были только частью общего prompt context;
- использовало runtime prompt overrides, в которых был риск mojibake.

Архитектурно задача находится в `./tooling/application-agent`, потому что основная логика реализована в workflow `analyze-vacancy`. При этом задача затрагивает корневой workspace, потому что реальные prompt overrides, config, contact metadata и результаты анализа лежат в корне суперпроекта.

## Границы

### Входит в scope

- Проверка runtime prompt/skill text на признаки mojibake до LLM-вызова.
- Формирование подписи из `profile/contact-regions.yml`.
- Удаление placeholder-подписей и гарантия ровно одной финальной подписи в каждой версии письма.
- Отдельный humanizer-pass для `cover_letter_standard` и `cover_letter_short`.
- Добавление `cover_letter_evidence` в JSON-контракт ответа.
- Расширение evidence pack полным выбранным ролевым резюме и `MASTER.md`.
- Пересмотр `forbidden_claims` и добавление `careful_claims`.
- Обновление quality-mode config и сохранение новых meta-полей.
- Обновление тестов под новый контракт.
- Smoke run на реальной вакансии Fintehrobot.

### Не входит в scope

- Полная переработка prompt layer на основе `promt-analyze-vacancies-and-respond.md`.
- Оценка качества итогового письма как финальной версии для отправки кандидатом.
- Изменение workflow адаптации резюме за пределами `analyze-vacancy`.
- Массовое исправление исторического mojibake в старых планах, документации и тестовых fixtures.

## Допущения

- Все факты из выбранного ролевого резюме и `MASTER.md` считаются подтвержденной фактурой.
- Для вакансии Fintehrobot регион контактов должен быть `RU`, потому что страна вакансии - Россия.
- `gpt-5.4-mini` с `medium` reasoning допустим только для smoke/draft, а финальный режим письма требует `gpt-5.4` или сильнее и `high` reasoning.
- OpenAI Skills не заменяют отдельный deterministic postprocessor: humanizer-pass должен оставаться отдельным вызовом.
- Код валидирует форму результата и подпись, но не должен жестко ограничивать LLM коротким evidence shortlist на стороне Python.

## Риски и неизвестные

- Отдельный humanizer-pass увеличивает стоимость и длительность реального запуска.
- Quality-mode `gpt-5.4` + `high` может требовать большего timeout, чем smoke-mode.
- Если runtime prompt layer будет слишком коротким, технически исправленный workflow все равно может давать слабое письмо.
- Если root prompt overrides снова будут сохранены с mojibake, workflow должен завершиться ошибкой до LLM-вызова.
- Текущий план закрывает инфраструктурную часть, но не закрывает последующую содержательную переработку prompt layer.

## Внешние точки касания

- `agent_memory/prompts/analyze-vacancy/system.ru.md` - обновление - runtime system prompt override.
- `agent_memory/prompts/analyze-vacancy/task.ru.md` - обновление - runtime task prompt override.
- `agent_memory/prompts/analyze-vacancy/cover-letter-contract.ru.md` - обновление - runtime contract письма.
- `agent_memory/config/application-agent.json` - обновление - quality-mode defaults.
- `profile/contact-regions.yml` - обновление - источник подписи и контактного региона.
- `vacancies/20260423-fintehrobot-head-of-development-rukovoditel-razrabotki/analysis.md` - генерация - smoke result.
- `vacancies/20260423-fintehrobot-head-of-development-rukovoditel-razrabotki/adoptions.md` - генерация - smoke result.
- `vacancies/20260423-fintehrobot-head-of-development-rukovoditel-razrabotki/meta.yml` - генерация - smoke result и meta markers.

## Этапы

### M1. Runtime-промпты и защита от mojibake

- Статус: `done`
- Цель:
  - Не допускать LLM-вызовов с runtime prompt/skill text, где есть признаки битой кодировки.
  - Восстановить root prompt overrides в нормальном UTF-8.
- Артефакты:
  - `src/application_agent/workflows/analyze_vacancy.py`
  - `agent_memory/prompts/analyze-vacancy/system.ru.md`
  - `agent_memory/prompts/analyze-vacancy/task.ru.md`
  - `agent_memory/prompts/analyze-vacancy/cover-letter-contract.ru.md`
- Критерии приемки:
  - Prompt overrides читаются из root workspace.
  - Runtime text с mojibake приводит к понятной ошибке до LLM-вызова.
  - Реальные prompt overrides в корне не содержат mojibake.
- Команды валидации:
  - `python -m pytest tests/test_analyze_workflow.py tests/test_cli.py -q`
  - `python -m pytest tests -q`
- Заметки:
  - Исторический mojibake в старых планах и test fixtures не входил в scope.

### M2. Подпись из `contact-regions.yml`

- Статус: `done`
- Цель:
  - Убрать hardcoded подпись из workflow.
  - Формировать имя, Telegram и contact region из `profile/contact-regions.yml`.
- Артефакты:
  - `src/application_agent/workflows/analyze_vacancy.py`
  - `profile/contact-regions.yml`
  - `tests/test_analyze_workflow.py`
  - `tests/test_adoptions_intake_workflow.py`
  - `tests/test_prepare_screening_workflow.py`
- Критерии приемки:
  - Для вакансии с Россией выбирается `RU`.
  - Placeholder-подписи удаляются.
  - В `analysis.md` ровно две подписи: одна в standard version и одна в short version.
- Команды валидации:
  - `python -m pytest tests/test_analyze_workflow.py -q`
  - `python -m pytest tests -q`
- Заметки:
  - Тестовые workspace получили минимальный `contact-regions.yml`, чтобы downstream tests не падали на новом обязательном контракте.

### M3. Отдельный humanizer-pass

- Статус: `done`
- Цель:
  - Разделить основной анализ и финальное редактирование письма.
  - Не считать наличие skill в prompt context гарантией финальной редакторской обработки.
- Артефакты:
  - `src/application_agent/workflows/analyze_vacancy.py`
  - `tests/test_analyze_workflow.py`
- Критерии приемки:
  - OpenAI provider выполняет отдельный humanizer-pass для `cover_letter_standard` и `cover_letter_short`.
  - Humanizer-pass не добавляет подпись.
  - Empty/invalid humanizer response прерывает workflow.
  - `meta.yml` сохраняет `humanizer_pass_applied`.
- Команды валидации:
  - `python -m pytest tests/test_analyze_workflow.py tests/test_cli.py -q`
- Заметки:
  - Fake provider не выполняет humanizer-pass и остается быстрым deterministic режимом для тестов.

### M4. LLM выбирает фактуру для письма

- Статус: `done`
- Цель:
  - Дать LLM полный подтвержденный контекст вместо жесткого короткого shortlist со стороны кода.
  - Сделать выбранную фактуру видимой и проверяемой в `analysis.md`.
- Артефакты:
  - `src/application_agent/workflows/analyze_vacancy.py`
  - `tests/test_analyze_workflow.py`
- Критерии приемки:
  - JSON schema требует `cover_letter_evidence`.
  - Evidence pack содержит `selected_resume_text` и `master_text`.
  - `forbidden_claims` не запрещает смежную подтвержденную фактуру только из-за неполного совпадения с вакансией.
  - `careful_claims` используется для аккуратных формулировок разрывов.
  - В `analysis.md` есть раздел `Cover letter evidence`.
- Команды валидации:
  - `python -m pytest tests/test_analyze_workflow.py -q`
- Заметки:
  - Код валидирует форму результата; смысловой выбор фактуры остается на стороне LLM.

### M5. Quality-mode модели и meta

- Статус: `done`
- Цель:
  - Зафиксировать финальный режим модели отдельно от smoke/draft режима.
  - Сохранить параметры запуска в `meta.yml`.
- Артефакты:
  - `agent_memory/config/application-agent.json`
  - `src/application_agent/workflows/analyze_vacancy.py`
  - `README.md`
  - `vacancies/20260423-fintehrobot-head-of-development-rukovoditel-razrabotki/meta.yml`
- Критерии приемки:
  - Root config использует `gpt-5.4`, `llm_reasoning_effort=high`, `llm_text_verbosity=medium`.
  - `meta.yml` сохраняет модель, reasoning, text verbosity, contact region и факт применения humanizer-pass.
  - Timeout OpenAI-вызовов достаточен для quality-mode.
- Команды валидации:
  - `python -m pytest tests/test_analyze_workflow.py tests/test_cli.py -q`
  - `job-application-agent --root ./ analyze-vacancy --vacancy-id 20260423-fintehrobot-head-of-development-rukovoditel-razrabotki`
- Заметки:
  - Первый smoke run с 90s timeout упал по timeout; после увеличения timeout основной вызов и humanizer-pass завершились успешно.

### M6. Документационная и процессная ремедиация

- Статус: `done`
- Цель:
  - Исправить нарушения, найденные после реализации M1-M5: английский блок в README и примитивный plan-файл.
  - Усилить автоматические проверки, чтобы похожие нарушения ловились тестами.
- Артефакты:
  - `README.md`
  - `plans/2026-04-28-cover-letter-quality-remediation.md`
  - `tests/test_plan_language_policy.py`
- Критерии приемки:
  - README не содержит англоязычного служебного блока, добавленного в M5.
  - План соответствует обязательной структуре `plans/_template.md`.
  - Тесты проверяют обязательные разделы планов.
  - Тесты проверяют отсутствие известных англоязычных служебных вставок в README.
- Команды валидации:
  - `python -m pytest tests/test_plan_language_policy.py -q`
  - `python -m pytest tests -q`
- Заметки:
  - Этот milestone добавлен как corrective action перед переработкой prompt layer.

## Журнал решений

- `2026-04-28 20:00` - Решено сохранять отдельный humanizer-pass даже при наличии skill в OpenAI Skills, потому что skill не является deterministic postprocessor.
- `2026-04-28 20:15` - Решено брать подпись только из `profile/contact-regions.yml`, чтобы убрать дублирование и hardcoded значение.
- `2026-04-28 20:30` - Решено считать подтвержденной фактурой все, что есть в выбранном ролевом резюме или `MASTER.md`.
- `2026-04-28 21:00` - Решено не строить жесткий `cover_letter_evidence` shortlist на стороне кода; LLM возвращает список выбранных фактов сама.
- `2026-04-28 22:30` - После timeout реального smoke run увеличены timeout OpenAI-вызовов: основной pass до 240 секунд, humanizer-pass до 180 секунд.
- `2026-04-28 23:30` - Зафиксировано, что prompt-content часть была недостаточно проработана и должна быть вынесена в следующий отдельный workstream на основе `promt-analyze-vacancies-and-respond.md`.
- `2026-04-28 23:40` - Добавлен M6 для исправления документационных и процессных нарушений перед переработкой prompt layer.

## Журнал прогресса

- `2026-04-28 20:00` - План создан и работа начата. Статус: `in_progress`.
- `2026-04-28 21:10` - Реализованы runtime mojibake guard, contact signature, humanizer-pass и `cover_letter_evidence`. Targeted tests: `11 passed`.
- `2026-04-28 21:45` - Обновлены root prompt overrides, `contact-regions.yml` и config. Targeted tests: `24 passed`.
- `2026-04-28 22:10` - Full suite сначала выявил отсутствие `contact-regions.yml` в downstream fixtures и нарушение plan language policy.
- `2026-04-28 22:20` - Исправлены fixtures и структура plan headings. Full suite: `89 passed`.
- `2026-04-28 22:35` - Реальный smoke run сначала упал по timeout, затем после увеличения timeout завершился успешно.
- `2026-04-28 22:50` - Проверен результат smoke: placeholders отсутствуют, подпись ровно две, `cover_letter_evidence` есть, mojibake в `analysis.md` нет, `humanizer_pass_applied: true`.
- `2026-04-28 23:05` - Изменения опубликованы: submodule commit `f917266`, root commit `c7ac1e5`.
- `2026-04-28 23:40` - Исправлен план до полной структуры и заменен англоязычный блок README; добавлены предложения по усилению правил через тесты.

## Текущее состояние

- Текущий milestone: `M6`
- Текущий статус: `done`
- Следующий шаг: `Перейти к отдельному плану переработки prompt layer на основе promt-analyze-vacancies-and-respond.md`
- Активные блокеры:
  - нет
- Открытые вопросы:
  - Какой объем мастер-промпта должен быть перенесен в `system.ru.md`, `task.ru.md`, `cover-letter-contract.ru.md` и humanizer-pass instructions без потери качества и без дублирования?
  - Нужен ли отдельный golden quality test для письма по Fintehrobot, который будет сравнивать результат с эталонными критериями, а не только с техническими acceptance checks?

## Итог завершения

Поставлена инфраструктурная часть remediation:

- runtime prompts и skill text защищены от mojibake;
- подпись формируется из `profile/contact-regions.yml`;
- OpenAI provider выполняет отдельный humanizer-pass;
- LLM возвращает `cover_letter_evidence`;
- evidence pack расширен полным подтвержденным контекстом;
- quality-mode config и meta markers зафиксированы;
- реальный smoke run по Fintehrobot завершился успешно.

Остаточный риск: качество prompt layer все еще требует отдельной переработки на основе `promt-analyze-vacancies-and-respond.md`. Текущий план не должен считаться содержательным закрытием проблемы качества письма; он закрывает техническую и процессную часть, необходимую перед следующей итерацией.
