# Workflow Contract Alignment And Safety

- Title: `Workflow contract alignment and safety`
- Slug: `2026-04-21-workflow-contract-alignment-and-safety`
- Owner: `Codex`
- Created: `2026-04-21`
- Last updated: `2026-04-22 08:55`
- Overall status: `done`

## Objective

Собрать единый, проверяемый контракт для уже реализованных workflow (`bootstrap`, `ingest-vacancy`, `analyze-vacancy`) и связанных side effects так, чтобы код, документация, runtime memory, Excel updates и git-публикация не противоречили друг другу и не создавали скрытых рисков для private workspace.

## Background and context

На момент старта workstream в `tooling/application-agent/src` уже существовали:

- CLI entrypoint и workflow registry;
- `JsonMemoryStore` для runtime-файлов;
- `ingest-vacancy` с vacancy scaffold, runtime updates и записью в `response-monitoring.xlsx`;
- `analyze-vacancy` с выбором role resume, fit-эвристикой и vacancy-local analysis/adoptions;
- extraction/parsing stack для HH и generic career pages;
- Playwright fallback.

Подтвержденное тестами состояние:

- `python -m unittest discover -s tests` проходит;
- тесты покрывают ingest/analyze workflow, memory store, channel normalization, country catalog, Playwright renderer и CLI publication boundary.

Ключевые проблемы, которые были подтверждены и закрывались этим workstream:

- скрытые git side effects после `ingest-vacancy`;
- несогласованность operator-facing docs и фактического поведения CLI;
- stale runtime references на уже отсутствующие vacancy artifacts;
- смешение CLI commands, workflow registry и workflow catalog.

Отдельно:

- содержательные результаты завершенного ingest refactor включены в этот plan как часть current state и completion summary, поэтому отдельный historical `ingest-refactor-plan.md` больше не нужен как активный источник истины;
- ordered backlog remaining workflows, собранный в M4, теперь служит входом для master-plan sequencing, а не немедленным trigger для feature expansion.

## Scope

### In scope

- contract matrix для `bootstrap`, `ingest-vacancy`, `analyze-vacancy`;
- правила мутаций root artifacts: `vacancies/`, `agent_memory/runtime/`, `response-monitoring.xlsx`;
- границы git-side effects и publication behavior;
- политика работы со stale runtime state и отсутствующими vacancy artifacts;
- ordered backlog remaining workflows после стабилизации safety boundary.

### Out of scope

- реализация новых feature workflows;
- наполнение `knowledge/`, `profile/`, `adoptions/` реальными данными;
- redesign PDF/LinkedIn output pipeline;
- repository cleanup и migration/removal superseded planning artifacts.

## Assumptions

- `unittest`, а не `pytest`, является текущим воспроизводимым validation baseline;
- `src/` и `tests/` описывают current behavior точнее, чем superseded planning docs;
- дальнейшее расширение workflow catalog безопасно только после стабилизации контрактов текущих трех команд.

## Risks and unknowns

- hidden publication behavior мог нарушать ожидания пользователя;
- contract drift между кодом и operator docs мог ломать повседневный flow;
- stale runtime history может требовать отдельной стратегии reconciliation в будущем;
- canonical Excel mapping contract и degradable-mode policy для `response-monitoring.xlsx` остаются follow-up задачами.

## External touchpoints

- `C:\Users\avramko\OneDrive\Documents\Career\vacancies\` — чтение / обновление / проверка — scaffold и analysis artifacts;
- `C:\Users\avramko\OneDrive\Documents\Career\agent_memory\runtime\` — чтение / обновление / проверка — task/project/user memory и run history;
- `C:\Users\avramko\OneDrive\Documents\Career\agent_memory\workflows\` — чтение / обновление / проверка — workflow contracts;
- `C:\Users\avramko\OneDrive\Documents\Career\response-monitoring.xlsx` — чтение / обновление / проверка — ingest side effect и внешний Excel contract;
- `C:\Users\avramko\OneDrive\Documents\Career\resumes\` — чтение / проверка — role resumes для `analyze-vacancy`;
- `C:\Users\avramko\OneDrive\Documents\Career\tooling\git\` — чтение / обновление / проверка — intended git flow;
- `C:\Users\avramko\OneDrive\Documents\Career\tooling\run-ingest-analyze.md` и `tooling\git-workflow.md` — чтение / обновление / проверка — operator-facing contract.

## Milestones

### M1. Current Contract Matrix And Contradiction Ledger

- Status: `done`
- Goal:
  - описать current state для CLI-команд, workflow artifacts, memory updates, Excel writes и git-side effects;
  - зафиксировать подтвержденные противоречия между кодом, тестами и документацией.
- Deliverables:
  - matrix `command -> inputs -> outputs -> side effects -> validation -> contradictions`;
  - prioritized contradiction ledger;
  - список решений, требующих product/owner confirmation.
- Acceptance criteria:
  - для `bootstrap`, `ingest-vacancy`, `analyze-vacancy` перечислены все подтвержденные side effects;
  - явно отмечены конфликты по auto-publish, Excel contract, stale runtime и workflow catalog;
  - можно продолжать работу без повторного чтения всего репозитория.
- Validation commands:
  - `python run_agent.py --root ../.. list-workflows`
  - `python run_agent.py --root ../.. show-memory`
  - `python -m unittest discover -s tests`
- Notes / discoveries:
  - source of truth для current behavior собирался из кода и тестов, а docs трактовались как expected operator contract.

### M2. Local-Only Publication Boundary

- Status: `done`
- Goal:
  - убрать скрытые git side effects и выровнять operator-facing contract.
- Deliverables:
  - CLI contract без auto-publish после `ingest-vacancy`;
  - синхронизированные docs/runbooks/private workflow docs.
- Acceptance criteria:
  - `ingest-vacancy` больше не делает скрытый publish;
  - документация описывает фактическую локальную mutation boundary;
  - validation baseline остается зеленым.
- Validation commands:
  - `python -m unittest tests.test_cli tests.test_ingest_workflow tests.test_analyze_workflow`
  - `Get-Content -Raw ..\git-workflow.md`
  - `Get-Content -Raw ..\run-ingest-analyze.md`
- Notes / discoveries:
  - publication закреплена как отдельный manual step, а не workflow side effect.

### M3. Report-First Reconciliation For Runtime State

- Status: `done`
- Goal:
  - добавить безопасную диагностику stale runtime state без автоочистки истории.
- Deliverables:
  - reconciliation layer в `show-memory`;
  - guardrails для missing vacancy artifacts;
  - tests на stale runtime references.
- Acceptance criteria:
  - stale references явно показываются как stale/missing;
  - `analyze-vacancy` возвращает точную ошибку при отсутствии vacancy folder;
  - полный `unittest` baseline проходит.
- Validation commands:
  - `python run_agent.py --root ../.. show-memory`
  - `python -m unittest discover -s tests`
- Notes / discoveries:
  - выбрана report-first strategy вместо автоочистки, чтобы не потерять audit trail.

### M4. Ordered Backlog After Safety Stabilization

- Status: `done`
- Goal:
  - превратить migrated target workflow catalog в ordered backlog с dependency gates и validation baseline.
- Deliverables:
  - ordered backlog для `prepare-screening`, `rebuild-master`, `rebuild-role-resume`, `build-linkedin`, `export-resume-pdf`;
  - dependency map между remaining workflows и уже существующим кодом.
- Acceptance criteria:
  - каждая будущая операция имеет минимальный input/output contract, external touchpoints и validation baseline;
  - очередь расширения не смешивает feature work с unresolved safety fixes.
- Validation commands:
  - `Get-Content -Raw C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\plans\2026-04-21-repository-reconstruction-and-backlog.md`
  - `Get-Content -Raw C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\plans\2026-04-21-prepare-screening-workflow.md`
  - `Get-Content -Raw C:\Users\avramko\OneDrive\Documents\Career\tooling\application-agent\plans\2026-04-21-workflow-contract-alignment-and-safety.md`
- Notes / discoveries:
  - Ordered backlog after safety stabilization:

    | Priority | Workflow | Proposed minimal contract | External touchpoints | Dependency gate | Validation baseline |
    | --- | --- | --- | --- | --- | --- |
    | `1` | `prepare-screening` | Input: `vacancy_id`, optional `selected_resume`, `output_language`, `preparation_depth`. Output: `vacancies/<vacancy_id>/screening.md` со storyline, self-intro и screening questions. | `vacancies/<id>/meta.yml`, `analysis.md`, `adoptions.md`, `resumes/<role>.md` | Опирается на existing vacancy-local contour. | `python run_agent.py --root ../.. prepare-screening --vacancy-id <id>` |
    | `2` | `rebuild-master` | Input: `resumes/MASTER.md`, accepted permanent signals, confirmed new user facts, processed vacancy history. Output: updated `resumes/MASTER.md` + change report. | `resumes/MASTER.md`, `adoptions/accepted/MASTER.md`, `agent_memory/runtime/`, `knowledge/` | Требует explicit permanent-signal store. | targeted unittest + smoke diff |
    | `3` | `rebuild-role-resume` | Input: `resumes/MASTER.md`, role signal base, target role. Output: updated `resumes/<role>.md` + diff summary. | `resumes/MASTER.md`, role resume files, `knowledge/roles/`, `adoptions/accepted/` | Зависит от `rebuild-master`. | targeted CLI/test validation |
    | `4` | `build-linkedin` | Input: `resumes/MASTER.md`, optional role/language. Output: draft `profile/linkedin.md` или аналогичный artifact. | `resumes/MASTER.md`, `profile/`, optional `knowledge/roles/` | Зависит от стабильного `MASTER`. | smoke-check draft |
    | `5` | `export-resume-pdf` | Input: target resume, `output_language`, `contact_region`, optional template. Output: PDF + render verification artifact. | `resumes/<role>.md` или `resumes/MASTER.md`, `profile/contact-regions.yml`, `templates/` | Не стартует до фиксации rendering/contact contract. | CLI export + render verification |

  - Explicit hold points before feature expansion:
    - для `rebuild-master` / `rebuild-role-resume` нужно закрепить destination для permanent adoptions и accepted signals;
    - для `export-resume-pdf` нужен отдельный rendering contract;
    - для всех новых workflows `bootstrap`/catalog boundary должен быть переосмыслен так, чтобы `list-workflows`, registry и `project_memory.workflow_catalog` описывали один и тот же набор операций.

## Decision log

- `2026-04-21 16:43` — Текущий workflow stack рассматривается как отдельный workstream, а не как часть общего artifact cleanup. — Основные риски связаны с side effects и behavioral contracts. — Это позволяет сначала стабилизировать безопасную основу, а потом расширять функциональность.
- `2026-04-21 16:43` — `unittest` принят как текущий validation baseline. — Он реально запускается в данном окружении, в отличие от `pytest`. — Все milestones этого плана используют воспроизводимые команды.
- `2026-04-21 16:43` — Содержательные итоги завершенного ingest refactor перенесены в этот safety workstream, а не остаются отдельным активным планом. — Historical refactor-plan не покрывает runtime safety, publication flow и contract drift. — Этот план берет более широкий operational scope.
- `2026-04-21 17:27` — Auto-publish после `ingest-vacancy` удален из CLI-контракта. — Это соответствует manual git flow и ожиданию явного подтверждения перед публикацией private artifacts. — Publication остается внешним операторским действием.
- `2026-04-21 17:46` — Для stale runtime выбран report-first reconciliation вместо автоочистки. — История запусков может быть нужна для аудита. — Safety boundary переносится в явную диагностику через `show-memory`.
- `2026-04-21 18:03` — M4 превратил migrated target workflow catalog в ordered backlog с dependency gates и validation baseline. — Remaining workflows получили минимальные contracts и hold points. — Это закрыло safety workstream, но не сделало feature expansion обязательным следующим шагом.
- `2026-04-21 19:51` — После пересмотра master plan этот workstream больше не диктует немедленный старт `prepare-screening`. — Feature expansion отложена до repository cleanup и current workflow completion gate. — Следующий шаг по этому плану теперь reference-only и служит входом для master-plan sequencing.

## Progress log

- `2026-04-21 16:43` — По коду, тестам и runbook подтверждено текущее поведение `bootstrap`, `ingest-vacancy`, `analyze-vacancy`, включая Excel integration и git-side effects в CLI. — `python -m unittest discover -s tests` -> `36 tests, OK`. — Status: `planned`.
- `2026-04-21 17:08` — M1 собрал contract matrix, contradiction ledger и список owner-level решений. — `python run_agent.py --root ../.. list-workflows`, `python run_agent.py --root ../.. show-memory` и `python -m unittest discover -s tests` завершились успешно. — Status: `done`.
- `2026-04-21 17:27` — M2 зафиксировал local-only publication boundary и синхронизировал operator docs с manual publish flow. — `python -m unittest tests.test_cli tests.test_ingest_workflow tests.test_analyze_workflow` -> `24 tests, OK`. — Status: `done`.
- `2026-04-21 17:46` — M3 добавил reconciliation-слой в `show-memory`, новые tests на stale runtime references и более точные ошибки `analyze-vacancy`. — Полный `unittest` baseline остается зеленым. — Status: `done`.
- `2026-04-21 18:03` — M4 зафиксировал ordered backlog remaining workflows и dependency gates. — Backlog теперь является planning input, а не командой к немедленному старту новой реализации. — Status: `done`.
- `2026-04-21 19:51` — План синхронизирован с обновленным master plan и migration/removal superseded planning artifacts. — Дополнительной кодовой валидации не требовалось, так как обновлялась только плановая последовательность. — Status: `done`.

## Current state

- Current milestone: `M4`
- Current status: `done`
- Next step: `Использовать findings этого плана как вход в master-plan sequence: сначала repository cleanup и migration/removal superseded plan artifacts, затем completion gate по текущему workflow-стеку, и только потом planning remaining workflows.`
- Active blockers:
  - Feature expansion сознательно отложена master plan до завершения repository cleanup и current workflow completion gate.
  - Не согласован канонический Excel mapping contract и degradable-mode policy.
- Open questions:
  - Должен ли `ingest-vacancy` уметь работать без `response-monitoring.xlsx`, если файла нет или он поврежден?
  - Должен ли `analyze-vacancy` по-прежнему писать vacancy-local `adoptions.md`, если проект перейдет к корневому `adoptions/inbox/<vacancy_id>.md`?
  - Какой набор existing workflows нужно считать "минимально готовым" до начала feature expansion?

## Completion summary

- Поставлено:
  - M1: contract matrix и contradiction ledger для `bootstrap`, `ingest-vacancy`, `analyze-vacancy`;
  - M2: local-only publication boundary без hidden git side effects;
  - M3: report-first reconciliation для stale runtime state;
  - M4: ordered backlog remaining workflows с dependency gates.
- Провалидировано:
  - `python run_agent.py --root ../.. list-workflows`
  - `python run_agent.py --root ../.. show-memory`
  - `python -m unittest discover -s tests`
  - `python -m unittest tests.test_cli tests.test_ingest_workflow tests.test_analyze_workflow`
- Оставшиеся follow-up задачи:
  - закрепить canonical Excel mapping contract и degradable-mode policy;
  - решить migration path от vacancy-local `adoptions.md` к корневому `adoptions/` pipeline;
  - определить completion gate по текущему workflow-стеку до feature expansion.
- Остаточные риски:
  - stale runtime history по-прежнему требует аккуратной дальнейшей работы;
  - без master-plan gate feature expansion может снова разъехаться с root contracts и cleanup workstream.
