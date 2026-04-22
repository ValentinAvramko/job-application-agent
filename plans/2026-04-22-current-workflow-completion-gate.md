# Current Workflow Completion Gate

- Title: `Current workflow completion gate`
- Slug: `2026-04-22-current-workflow-completion-gate`
- Owner: `Codex`
- Created: `2026-04-22`
- Last updated: `2026-04-22 09:10`
- Overall status: `in_progress`

## Objective

Явно определить, что именно считается минимально завершённым состоянием для текущего workflow-стека (`bootstrap`, `ingest-vacancy`, `analyze-vacancy`) до старта следующей feature wave, чтобы:

- не смешивать доработку текущего контура с planning remaining workflows;
- превратить safety findings и cleanup findings в конкретный completion gate;
- зафиксировать, какие расхождения являются blocker-ами, а какие допустимыми follow-up после старта новых workflow.

## Background and context

На входе в этот workstream уже подтверждено:

- `python -m unittest discover -s tests` проходит (`39 tests, OK`);
- CLI поддерживает команды `bootstrap`, `list-workflows`, `show-memory`, `ingest-vacancy`, `analyze-vacancy`;
- `list-workflows` фактически возвращает только `ingest-vacancy` и `analyze-vacancy`;
- `project_memory.workflow_catalog` всё ещё содержит `bootstrap`, `ingest-vacancy`, `analyze-vacancy`;
- runtime memory по-прежнему содержит большой historical trail со stale/missing vacancy artifacts;
- root-normalization cleanup завершён, поэтому следующим активным этапом больше не является cleanup или migration legacy docs.

Текущее product ambiguity:

- не до конца ясно, считать ли `bootstrap` полноценным workflow, который должен отображаться в workflow catalog, или отдельной setup-командой вне каталога;
- не зафиксировано, какой уровень качества достаточен для `response-monitoring.xlsx` integration и нужен ли degradable mode при отсутствии workbook;
- не решено, должен ли vacancy-local `adoptions.md` считаться допустимым interim output текущего стека до подключения root `adoptions/`;
- не отделены обязательные исправления current stack от допустимых future follow-ups.

## Scope

### In scope

- определение completion criteria для `bootstrap`, `ingest-vacancy`, `analyze-vacancy`;
- contradiction ledger по registry/CLI/docs/runtime memory;
- gate-решения по stale runtime, Excel dependency и vacancy-local adoptions;
- решение, нужен ли отдельный remediation plan после gate review.

### Out of scope

- реализация remaining workflows (`prepare-screening`, `rebuild-master`, `rebuild-role-resume`, `build-linkedin`, `export-resume-pdf`);
- новый root cleanup и migration legacy corpus;
- глубокая переработка resume/profile/adoptions data model без отдельного workstream-а.

## Assumptions

- safety plan и root-normalization plan уже считаются завершёнными входами, а не активными workstreams;
- `src/`, `tests/`, `README.md`, `show-memory` и CLI output описывают current state точнее, чем старые устные договорённости;
- completion gate может закончиться как фиксацией blocker-ов для отдельного implementation plan, так и признанием части вопросов допустимыми follow-up.

## Risks and unknowns

- если gate будет слишком мягким, feature expansion снова начнётся на фоне неустойчивых текущих контрактов;
- если gate будет слишком жёстким, backlog новых workflow искусственно заблокируется вопросами, которые не влияют на реальную эксплуатацию;
- registry/catalog mismatch вокруг `bootstrap` может путать operator docs, runtime memory и будущие workflow contracts;
- Excel integration остаётся внешней зависимостью с не до конца зафиксированным failure policy.

## External touchpoints

- `C:\Users\avramko\OneDrive\Documents\Career\vacancies\` — чтение / проверка — реальное состояние vacancy artifacts и stale trails;
- `C:\Users\avramko\OneDrive\Documents\Career\agent_memory\` — чтение / проверка — runtime memory, workflow catalog и historical runs;
- `C:\Users\avramko\OneDrive\Documents\Career\response-monitoring.xlsx` — чтение / проверка — current Excel dependency contract;
- `C:\Users\avramko\OneDrive\Documents\Career\resumes\` — чтение / проверка — required input layer для `analyze-vacancy`;
- `C:\Users\avramko\OneDrive\Documents\Career\tooling\run-ingest-analyze.md` и `C:\Users\avramko\OneDrive\Documents\Career\tooling\git-workflow.md` — чтение / проверка — operator-facing contract outside submodule.

## Milestones

### M1. Completion Gate Evidence Baseline

- Status: `in_progress`
- Goal:
  - собрать короткий, проверяемый baseline по текущему стеку и всем открытым contradictions;
  - определить candidate completion criteria для `bootstrap`, `ingest-vacancy`, `analyze-vacancy`.
- Deliverables:
  - contradiction ledger по CLI, registry, runtime memory, docs и external side effects;
  - draft matrix `workflow/command -> current state -> required gate condition -> deferred follow-up`;
  - список gate questions, которые нужно закрыть до M2.
- Acceptance criteria:
  - все открытые проблемы current stack сведены в один документ без повторной разведки;
  - отдельно отмечены blocker-ы и non-blocking follow-ups;
  - понятно, какие команды и файлы используются как evidence baseline.
- Validation commands:
  - `python run_agent.py --root ../.. list-workflows`
  - `python run_agent.py --root ../.. show-memory`
  - `python -m unittest discover -s tests`
  - `Get-Content -Raw README.md`
- Notes / discoveries:
  - На старте workstream-а `list-workflows` показывает только `ingest-vacancy` и `analyze-vacancy`, тогда как `project_memory.workflow_catalog` всё ещё включает `bootstrap`.
  - `show-memory` продолжает репортить большой stale historical trail, но это уже диагностируется явно, а не скрыто.

### M2. Gate Decisions And Minimal-Done Criteria

- Status: `planned`
- Goal:
  - принять решения по тому, что именно считается достаточным состоянием current stack перед feature expansion.
- Deliverables:
  - completion gate checklist;
  - решения по bootstrap/catalog boundary, Excel dependency policy, vacancy-local adoptions и stale runtime expectations;
  - updated master-plan dependency rule for starting M5.
- Acceptance criteria:
  - для каждого из трёх workflow/command контуров есть чёткий статус: done now / requires fix / explicitly deferred;
  - не остаётся двусмысленности, что блокирует feature planning, а что нет;
  - gate можно пересказать без обращения к нескольким старым планам сразу.
- Validation commands:
  - `Get-Content -Raw plans\2026-04-22-current-workflow-completion-gate.md`
  - `Get-Content -Raw plans\2026-04-21-repository-reconstruction-and-backlog.md`
  - `python run_agent.py --root ../.. list-workflows`
- Notes / discoveries:
  - Заполняется после M1.

### M3. Follow-Up Packaging

- Status: `planned`
- Goal:
  - упаковать результат gate review в следующий конкретный execution step.
- Deliverables:
  - либо завершённый gate с переводом master plan на M5;
  - либо отдельный remediation plan, если найдутся blocker-ы, требующие implementation work.
- Acceptance criteria:
  - master plan знает один конкретный следующий шаг;
  - у текущего стека нет неразобранных ambiguity, маскирующихся под follow-up.
- Validation commands:
  - `Get-Content -Raw plans\2026-04-22-current-workflow-completion-gate.md`
  - `Get-Content -Raw plans\2026-04-21-repository-reconstruction-and-backlog.md`
- Notes / discoveries:
  - Заполняется после M2.

## Decision log

- `2026-04-22 09:10` — Completion gate вынесен в отдельный plan, а не оставлен абзацем внутри master plan. — Здесь нужен самостоятельный contradiction ledger и gate checklist по текущему стеку. — Это снижает риск снова смешать cleanup, safety findings и future feature planning.

## Progress log

- `2026-04-22 09:10` — Workstream открыт на основании master M4 и первичного baseline по CLI, runtime memory и tests. — `python run_agent.py --root ../.. list-workflows` показывает 2 workflow, `show-memory` показывает registry/catalog mismatch и stale historical trail, `python -m unittest discover -s tests` -> `39 tests, OK`. — Status: `in_progress`.

## Current state

- Current milestone: `M1`
- Current status: `in_progress`
- Next step: `Собрать contradiction ledger и candidate completion criteria для `bootstrap`, `ingest-vacancy` и `analyze-vacancy` на основе CLI, runtime memory, docs и tests.`
- Active blockers:
  - Не зафиксировано, является ли `bootstrap` частью workflow catalog или отдельной setup-командой.
  - Не определено, считать ли Excel dependency и vacancy-local `adoptions.md` blocker-ами для feature expansion.
- Open questions:
  - Какой набор текущих расхождений реально блокирует M5, а какой можно оставить follow-up после старта новых workflow?
  - Нужен ли отдельный remediation implementation plan после gate review?

## Completion summary

Заполняется после завершения workstream-а.
