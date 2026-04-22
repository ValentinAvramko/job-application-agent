# Current Stack Contract Remediation

- Title: `Current stack contract remediation`
- Slug: `2026-04-22-current-stack-contract-remediation`
- Owner: `Codex`
- Created: `2026-04-22`
- Last updated: `2026-04-22 10:26`
- Overall status: `done`

## Objective

Снять blocker-ы, найденные completion gate, и привести текущий workflow-стек к одной рабочей модели, в которой:

- `bootstrap` остаётся setup-only CLI командой и больше не конкурирует с runtime workflow catalog;
- текущие и ближайшие workflow читают резюме только из `resumes/`, а не из устаревшего `CV/`;
- `response-monitoring.xlsx` остаётся обязательной внешней зависимостью для ingest, но это правило зафиксировано явно в коде, тестах и operator docs.

## Background and context

Completion gate из `2026-04-22-current-workflow-completion-gate.md` зафиксировал три blocker-а:

- `bootstrap` catalog drift между CLI/registry и `WORKFLOW_CATALOG`/runtime memory;
- path drift между canonical root contract (`resumes/`) и фактическими ссылками на `CV/` в коде, тестах и runbook;
- неявная policy around `response-monitoring.xlsx`: код трактует workbook как mandatory, но это не оформлено как явное правило с предсказуемым failure mode.

Неблокирующие факты, которые не нужно решать в этом workstream:

- vacancy-local `vacancies/<id>/adoptions.md` остаётся допустимым staging artifact текущего runtime;
- stale historical trail в runtime memory допустим при сохранении report-first reconciliation.

## Scope

### In scope

- убрать `bootstrap` из runtime workflow catalog и синхронизировать связанные тесты/документацию;
- заменить текущие ссылки `CV/` на `resumes/` в code paths, tests и operator-facing docs, относящихся к текущему стеку;
- сделать policy для `response-monitoring.xlsx` явной: дружелюбная ошибка/предсказуемый failure contract + синхронизированные docs/tests;
- обновить active plans после remediation.

### Out of scope

- redesign `adoptions/` pipeline;
- переход к degradable Excel mode;
- planning или реализация новых workflows beyond current stack;
- cleanup historical runtime runs.

## Assumptions

- `resumes/` является единственным валидным canonical path для resume layer;
- `response-monitoring.xlsx` продолжает существовать как обязательный операторский артефакт текущего ingest path;
- root runbook `tooling/run-ingest-analyze.md` можно обновлять как сопутствующий external touchpoint ради устранения drift.

## Risks and unknowns

- path migration может затронуть не только active workflows, но и adjacent future code (`prepare_screening.py`);
- если Excel failure policy будет сформулирована слишком расплывчато, ambiguity останется даже после кодовых правок;
- operator docs outside submodule могут остаться несинхронизированными, если не включить их в remediation.

## External touchpoints

- `C:\Users\avramko\OneDrive\Documents\Career\resumes\` — чтение / проверка — canonical resume path;
- `C:\Users\avramko\OneDrive\Documents\Career\response-monitoring.xlsx` — чтение / проверка — mandatory ingest dependency;
- `C:\Users\avramko\OneDrive\Documents\Career\tooling\run-ingest-analyze.md` — обновление / проверка — operator-facing runbook;
- `C:\Users\avramko\OneDrive\Documents\Career\tooling\git-workflow.md` — чтение / проверка — confirm no conflicting workflow-catalog language.

## Milestones

### M1. Bootstrap Catalog Boundary Cleanup

- Status: `done`
- Goal:
  - привести CLI, runtime memory defaults и tests к одной модели, где `bootstrap` не является runtime workflow.
- Deliverables:
  - updated `WORKFLOW_CATALOG`/memory defaults;
  - updated tests for memory/catalog expectations;
  - synced docs where workflow catalog is described.
- Acceptance criteria:
  - `list-workflows` и runtime workflow catalog больше не расходятся по `bootstrap`;
  - `bootstrap` остаётся доступной CLI-командой, но не фигурирует как workflow item.
- Validation commands:
  - `python run_agent.py --root ../.. list-workflows`
  - `python -m unittest tests.test_memory_store tests.test_cli`
- Notes / discoveries:
  - `WORKFLOW_CATALOG` сокращён до runtime workflows (`ingest-vacancy`, `analyze-vacancy`), а `project_memory.workflow_catalog` теперь синхронизируется как exact list, чтобы legacy `bootstrap` не оставался в runtime memory.
  - `README.md` уточнён: `bootstrap` описан как setup-only CLI команда вне runtime workflow catalog.

### M2. Resume Path Alignment

- Status: `done`
- Goal:
  - убрать runtime/path drift между `CV/` и `resumes/`.
- Deliverables:
  - updated code paths in active and adjacent workflows;
  - updated tests and docs using `resumes/`;
  - search-based verification for live `CV/` references in the remediated surface.
- Acceptance criteria:
  - current stack does not require `CV/` to exist;
  - tests and runbook reflect `resumes/` as the only supported path.
- Validation commands:
  - `rg -n -e 'CV/' -e 'CV\\\\' -e '"CV"' src/application_agent/workflows tests/test_analyze_workflow.py tests/test_prepare_screening_workflow.py README.md "C:\Users\avramko\OneDrive\Documents\Career\tooling\run-ingest-analyze.md"`
  - `python -m unittest tests.test_analyze_workflow tests.test_prepare_screening_workflow`
- Notes / discoveries:
  - `analyze-vacancy` и adjacent `prepare-screening` разделяют один и тот же contract выбора ролевого резюме, поэтому path remediation выполнен для обеих точек, а не только для active workflow.
  - Для устранения повторяющегося drift добавлен `WorkspaceLayout.resumes_dir`, чтобы выбор resume-root больше не дублировался строковыми литералами.

### M3. Explicit Excel Prerequisite Contract

- Status: `done`
- Goal:
  - зафиксировать и реализовать понятный hard-prerequisite contract для `response-monitoring.xlsx`.
- Deliverables:
  - explicit failure behavior when workbook is missing or invalid;
  - synced README/runbook wording about workbook precondition;
  - tests covering expected failure contract or precondition behavior.
- Acceptance criteria:
  - ambiguity around workbook dependency removed;
  - operator can понять из docs и CLI behavior, что требуется для успешного ingest.
- Validation commands:
  - `python -m unittest tests.test_ingest_workflow`
  - `Get-Content -Raw README.md`
  - `Get-Content -Raw "C:\Users\avramko\OneDrive\Documents\Career\tooling\run-ingest-analyze.md"`
- Notes / discoveries:
  - `ingest-vacancy` теперь валидирует workbook до создания vacancy scaffold, поэтому mandatory Excel prerequisite стал не только документированным, но и fail-fast boundary.
  - Existing tests, которые раньше патчили только `append_ingest_record`, синхронизированы с новым preflight-check через patch `validate_response_monitoring_workbook`.

### M4. Validation And Handback To Completion Gate

- Status: `done`
- Goal:
  - подтвердить, что remediation снял gate blocker-ы и можно вернуться к master sequencing.
- Deliverables:
  - updated completion-gate plan and master plan;
  - validation evidence for catalog, resume path and Excel contract alignment.
- Acceptance criteria:
  - current blocker-ы из completion gate сняты или явно downgraded;
  - следующий шаг в master plan больше не ambiguously points back to the same drift issues.
- Validation commands:
  - `python run_agent.py --root ../.. list-workflows`
  - `python run_agent.py --root ../.. show-memory`
  - `python -m unittest discover -s tests`
  - `Get-Content -Raw plans\2026-04-22-current-workflow-completion-gate.md`
- Notes / discoveries:
  - `show-memory` по-прежнему репортит большой stale historical trail, но это уже соответствует принятому report-first reconciliation contract и не блокирует handback.
  - После remediation master sequencing можно безопасно вернуть к M5 ordered planning без повторного gate-review по тем же drift-темам.

## Decision log

- `2026-04-22 10:03` — Remediation выделен в отдельный execution plan после завершения completion gate. — Gate уже определил blocker-ы и не должен смешиваться с их реализацией. — Это делает следующий шаг конкретным и проверяемым.
- `2026-04-22 10:03` — `bootstrap` трактуется как setup-only command, `resumes/` как единственный resume root, а `response-monitoring.xlsx` как mandatory dependency текущего ingest path. — Эти решения уже приняты gate-планом и теперь требуют кодовой/документационной реализации. — Scope remediation ограничен только этим.
- `2026-04-22 10:17` — Для M2 path remediation в scope включён и adjacent `prepare-screening.py`. — Он использует тот же contract выбора resume-root, что и `analyze-vacancy`, поэтому частичная правка оставила бы новый drift в соседнем workflow surface. — Это расширяет remediation не по feature scope, а по границе одного и того же path contract.
- `2026-04-22 10:23` — Для M3 выбран fail-fast contract: отсутствие или невалидность `response-monitoring.xlsx` должны останавливать `ingest-vacancy` до создания vacancy artifacts. — Это лучше соответствует hard-prerequisite semantics, чем позднее падение после частичной записи scaffold. — Docs и tests синхронизируются под этот же operator-visible failure mode.

## Progress log

- `2026-04-22 10:03` — Plan создан как follow-up после завершения completion gate. — На старте workstream-а blockers уже локализованы: catalog drift, resume path drift и implicit Excel prerequisite. — Status: `in_progress`.
- `2026-04-22 10:14` — M1 закрыт: `bootstrap` удалён из canonical workflow catalog, а sync project memory теперь переписывает legacy catalog к точному runtime-списку. — `python run_agent.py --root ../.. list-workflows` показывает только `analyze-vacancy` и `ingest-vacancy`; `python -m unittest tests.test_memory_store tests.test_cli` -> `5 tests, OK`. — Status: `done`.
- `2026-04-22 10:17` — M2 закрыт: active и adjacent resume code paths переведены с `CV/` на `resumes/`, operator-facing runbook синхронизирован, а тестовые fixtures теперь создают ролевые резюме только в `resumes/`. — Targeted search по workflow/tests/runbook не находит `CV` path references, `python -m unittest tests.test_analyze_workflow tests.test_prepare_screening_workflow` -> `5 tests, OK`. — Status: `done`.
- `2026-04-22 10:23` — M3 закрыт: `response-monitoring.xlsx` оформлен как явный mandatory prerequisite с fail-fast validation до создания vacancy scaffold, добавлены tests на missing/invalid workbook и обновлены README/runbook. — `python -m unittest tests.test_ingest_workflow tests.test_analyze_workflow tests.test_prepare_screening_workflow` -> `29 tests, OK`; operator-facing docs явно описывают prerequisite и failure mode. — Status: `done`.
- `2026-04-22 10:26` — M4 закрыт: финальная remediation validation подтверждает, что `list-workflows` и `project_memory.workflow_catalog` согласованы, `show-memory` оставляет только допустимый stale historical trail, а `python -m unittest discover -s tests` -> `42 tests, OK`. — Completion-gate и master plan синхронизированы, workstream можно считать завершённым. — Status: `done`.

## Current state

- Current milestone: `M4`
- Current status: `done`
- Next step: `Вернуться в master plan и начать M5 ordered planning for remaining workflows, начиная с revalidation плана `2026-04-21-prepare-screening-workflow.md`.`
- Active blockers:
  - none
- Open questions:
  - none

## Completion summary

- Публичный current stack приведён к одной модели: `bootstrap` остался setup-only command вне workflow catalog, runtime resume root унифицирован на `resumes/`, а `response-monitoring.xlsx` оформлен как явный hard prerequisite ingest path.
- Валидация подтверждена реальными CLI checks и полным test baseline: `list-workflows` согласован с runtime memory, `show-memory` честно диагностирует только допустимый historical trail, `python -m unittest discover -s tests` проходит (`42 tests, OK`).
- Operator-facing docs синхронизированы через public `README.md` и private runbook `tooling/run-ingest-analyze.md`.
- Следующий этап возвращается в master sequencing: ordered planning remaining workflows (`M5`) больше не заблокирован drift-темами current stack.
