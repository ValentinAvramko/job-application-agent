# Улучшение качества `analyze-vacancy`

- Title: `улучшение качества analyze-vacancy`
- Slug: `2026-04-24-analyze-vacancy-quality-upgrade`
- Owner: `Codex`
- Created: `2026-04-24`
- Last updated: `2026-04-24 01:20`
- Overall status: `done`

## Цель

Перевести `analyze-vacancy` из слабого deterministic draft в качественный LLM-backed workflow анализа вакансии, который:

- выбирает лучшее ролевое резюме на основе data-driven профилей из `knowledge/roles/`;
- считает объяснимый fit score с русскоязычными терминами;
- пишет глубокий `analysis.md` с анализом соответствия, обоснованием выбора резюме, двумя вариантами сопроводительного письма и входами для адаптации;
- пишет расширенный `adoptions.md` с полноценными draft-правками резюме для downstream review;
- не меняет `resumes/*.md` напрямую, оставляя применение правок для `rebuild-master` / `rebuild-role-resume`.

## Контекст

Старый workflow использовал захардкоженный список ролей, извлекал небольшой набор строк, похожих на требования, считал простой keyword score и писал компактный `analysis.md` плюс тонкий `adoptions.md`. Такой результат уступал baseline prompt, особенно для senior IT leadership вакансий.

Целевое разделение workflow:

- `analyze-vacancy`: анализ соответствия, выбор резюме, сопроводительные письма, draft-входы для адаптации.
- `intake-adoptions`: перенос vacancy-local адаптаций в root review stores без принятия решений.
- `prepare-screening`: только подготовка к первичному интервью.
- `rebuild-master` / `rebuild-role-resume`: применение уже принятых изменений к резюме.

Текущий test runner проекта - `pytest`; новая валидация должна использовать `python -m pytest`.

## Scope

### Входит в scope

- Dedicated plan и обновление workflow contract.
- Data-driven role catalog на основе `knowledge/roles/*.md`.
- Начальные role profiles для существующих ролевых резюме.
- Объяснимая scoring-модель с русскоязычными output-терминами.
- LLM provider boundary и validation structured response.
- Новый contract для `analysis.md` и `adoptions.md`.
- Поддержка richer adaptation drafts в `intake-adoptions`.
- Совместимость `prepare-screening` с новым форматом analysis.
- Pytest coverage и smoke validation.

### Не входит в scope

- Прямая мутация `resumes/*.md` из `analyze-vacancy`.
- Отдельный артефакт `cover-letter.md`.
- Полный redesign review-процесса для adoptions.
- Замена `prepare-screening` логикой `analyze-vacancy`.

## Предположения

- `knowledge/roles/` является source of truth для доступных role profiles.
- Роли `CIO`, `CTO`, `HoE`, `HoD`, `EM` остаются начальными профилями, а не захардкоженным списком workflow.
- Real `analyze-vacancy` требует LLM runtime; тесты используют fake provider.
- Первая scoring implementation использует документированный гибрид baseline weighting и leadership-specific evidence checks.
- Для real OpenAI-compatible вызова нужны `OPENAI_API_KEY` и модель.

## Риски и неизвестные

- Real LLM boundary без OpenAI SDK требует небольшого stdlib HTTP adapter и аккуратной обработки ошибок.
- Role profiles являются новыми root-артефактами; отсутствующие или слабые профили могут ухудшить selection quality.
- LLM output нужно валидировать, чтобы не получать тихо сломанный markdown.
- Downstream tests и workflows могли предполагать старые headings и старую семантику coverage.

## Внешние точки касания

- `C:\Users\avramko\OneDrive\Documents\Career\knowledge\roles\` - обновление: добавлены начальные role profiles, workflow читает их при выборе резюме.
- `C:\Users\avramko\OneDrive\Documents\Career\templates\knowledge\role-signal.template.md` - чтение: форматная опора для role profiles.
- `C:\Users\avramko\OneDrive\Documents\Career\agent_memory\workflows\analyze-vacancy.md` - обновление: operator-facing workflow contract.
- `C:\Users\avramko\OneDrive\Documents\Career\vacancies\` - генерация/обновление: richer `analysis.md` и `adoptions.md`.

## Milestones

### M1. План, role catalog и baseline contract

- Status: `done`
- Goal:
  - Создать план, добавить начальные role profiles и обновить contract `analyze-vacancy`.
- Deliverables:
  - `knowledge/roles/CIO.md`, `CTO.md`, `HoE.md`, `HoD.md`, `EM.md`
  - обновлённый `agent_memory/workflows/analyze-vacancy.md`
  - этот план
- Acceptance criteria:
  - role profiles существуют для текущих ролевых резюме;
  - plan и workflow docs описывают data-driven role selection и rich output contract;
  - production code changes не начинаются до фиксации baseline.
- Validation commands:
  - `Get-ChildItem ..\..\knowledge\roles -File`
  - `Get-Content -Raw ..\..\agent_memory\workflows\analyze-vacancy.md`
- Notes / discoveries:
  - добавлены начальные profiles для пяти существующих role resumes;
  - `agent_memory/workflows/analyze-vacancy.md` теперь описывает rich analysis и role catalog contract.

### M2. Evidence, scoring, LLM boundary и rendering анализа

- Status: `done`
- Goal:
  - Заменить shallow heuristic analysis на role-profile evidence, explainable scoring и LLM-backed package rendering.
- Deliverables:
  - обновлённый `analyze_vacancy.py`
  - LLM provider boundary
  - CLI options для LLM settings
  - pytest coverage для role catalog, scoring, selection и LLM boundary
- Acceptance criteria:
  - роли загружаются из `knowledge/roles/*.md`;
  - роль без matching resume исключается и попадает в diagnostic notes;
  - отсутствие валидных role profiles даёт explicit error;
  - real OpenAI-compatible provider требует API key/model;
  - fake provider детерминированно создаёт structured analysis для tests;
  - `analysis.md` содержит три больших блока.
- Validation commands:
  - `python -m pytest tests/test_analyze_workflow.py`
- Notes / discoveries:
  - implemented role catalog loading from `knowledge/roles/*.md`, `README.md` игнорируется;
  - real provider OpenAI-compatible через stdlib HTTP и явно падает без `OPENAI_API_KEY` / model;
  - fake provider создаёт deterministic structured packages для tests и smoke runs;
  - selection теперь сочетает requirement fit, role profile match, senior scope alignment, слабый title signal и risky-claim penalty.

### M3. Rich adoptions intake и совместимость screening

- Status: `done`
- Goal:
  - Сохранить richer `adoptions.md` через intake и оставить `prepare-screening` совместимым с новым analysis contract.
- Deliverables:
  - обновлённый `intake_adoptions.py`
  - обновлённый `prepare_screening.py`
  - pytest coverage для richer adoptions и screening compatibility
- Acceptance criteria:
  - `intake-adoptions` сохраняет draft edits для summary, skills и experience;
  - `NEW DATA NEEDED` продолжает синхронизироваться в questions ledger;
  - `prepare-screening` читает полезные signals из нового analysis format.
- Validation commands:
  - `python -m pytest tests/test_adoptions_intake_workflow.py tests/test_prepare_screening_workflow.py`
- Notes / discoveries:
  - `intake-adoptions` импортирует bullet lists и richer markdown table rows из vacancy-local `adoptions.md`;
  - `prepare-screening` читает новые `###` subsections и использует coverage semantics `full/partial/none/unclear`.

### M4. Full validation и real scenario check

- Status: `done`
- Goal:
  - Проверить upgraded workflow на full pytest suite и реальной вакансии с fake или configured LLM provider.
- Deliverables:
  - обновлённый plan status и completion summary
  - финальная синхронизация docs/tests при необходимости
- Acceptance criteria:
  - full pytest suite проходит;
  - real vacancy smoke run создаёт rich `analysis.md` и `adoptions.md` с configured provider;
  - остаточные риски задокументированы.
- Validation commands:
  - `python -m pytest tests`
  - `python run_agent.py --root ../.. analyze-vacancy --vacancy-id 20260423-fintehrobot-head-of-development-rukovoditel-razrabotki --llm-provider fake --llm-model test`
- Notes / discoveries:
  - full pytest suite passed: `80 passed`;
  - real Fintehrobot smoke run с fake provider выбрал `HoE` после добавления scope-alignment scoring;
  - intake и prepare-screening smoke runs завершились на той же реальной вакансии.

## Decision log

- `2026-04-24 00:00` - `knowledge/roles/*.md` является source of truth для role catalog. - Пользователь уточнил, что список ролей не фиксирован и должен браться из role profiles. - Реализация должна убрать hardcoded role selection как источник истины.
- `2026-04-24 00:00` - Scoring должен использовать русскоязычные output-термины и быть зафиксирован в реализации. - Пользователь запросил дополнительный анализ методики, а не слепое копирование baseline formula. - Выбранная модель закреплена в tests и output labels.
- `2026-04-24 00:00` - Новая validation использует pytest. - Проект уже мигрировал с unittest на pytest. - Все новые test commands используют `python -m pytest`.
- `2026-04-24 01:00` - Scoring для senior IT leadership использует гибридную модель: requirement fit является главным, role profile и scope alignment вторичны, title является слабым сигналом. - Это не даёт формулировке `Head of Development` перебить engineering-organization роль вроде Fintehrobot. - Selection остаётся data-driven через role profile signals, а не через фиксированный список ролей.
- `2026-04-24 01:20` - Plan должен быть русскоязычным. - Предыдущая версия была написана на английском из-за ошибки оформления. - План переведён на русский без изменения technical scope.
- `2026-04-24 01:35` - Role profiles и role template должны быть русскоязычными. - Knowledge-артефакты являются пользовательским слоем, а не внутренним кодовым контрактом. - Parser поддерживает русские и английские headings для обратной совместимости.

## Progress log

- `2026-04-24 00:00` - План создан по approved implementation request. - Validation pending. - Status: `in_progress`.
- `2026-04-24 00:10` - M1 завершён: добавлены начальные root role profiles и обновлён analyze-vacancy workflow contract. - Validation: `Get-ChildItem ..\..\knowledge\roles -File`; `Get-Content -Raw ..\..\agent_memory\workflows\analyze-vacancy.md`. - Status: `in_progress`.
- `2026-04-24 01:05` - M2-M4 завершены: реализованы LLM-backed analyze pipeline, rich adoptions intake, screening compatibility и CLI LLM options. - Validation: `python -m pytest tests/test_analyze_workflow.py`; `python -m pytest tests/test_adoptions_intake_workflow.py tests/test_prepare_screening_workflow.py tests/test_cli.py`; `python -m pytest tests`; real smoke for analyze/intake/prepare-screening on Fintehrobot. - Status: `done`.
- `2026-04-24 01:20` - План переведён на русский язык. - Scope и validation results не изменены. - Status: `done`.
- `2026-04-24 01:35` - Ролевые профили и template переведены на русский; `analyze_vacancy.py` получил bilingual role-profile parser. - Validation: `python -m pytest tests/test_analyze_workflow.py`. - Status: `done`.

## Current state

- Current milestone: `M4`
- Current status: `done`
- Next step: `Implementation steps по этому плану не осталось; следующий non-fake analyze-vacancy run нужно просмотреть на качество тона и factual boundaries.`
- Active blockers:
  - none
- Open questions:
  - none

## Completion summary

- Поставлены data-driven role catalog selection, explainable scoring, LLM provider boundary, rich `analysis.md`, full draft `adoptions.md`, intake table preservation и screening compatibility.
- Валидация выполнена только через pytest: targeted analyze/intake/prepare/CLI tests и full `python -m pytest tests` (`80 passed`).
- Real scenario smoke на `20260423-fintehrobot-head-of-development-rukovoditel-razrabotki` теперь выбирает `HoE`, пишет three-block analysis, импортирует adoptions и готовит screening.
- Остаточный риск: fake provider детерминированный и полезен для contract validation, но первый real OpenAI-compatible run нужно проверить на tone quality и factual-boundary quality.
