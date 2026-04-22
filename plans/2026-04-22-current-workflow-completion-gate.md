# Current Workflow Completion Gate

- Title: `Current workflow completion gate`
- Slug: `2026-04-22-current-workflow-completion-gate`
- Owner: `Codex`
- Created: `2026-04-22`
- Last updated: `2026-04-22 10:03`
- Overall status: `done`

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

## M1 Contradiction Ledger

| Area | Evidence | Current state | Gate impact | Candidate classification |
| --- | --- | --- | --- | --- |
| `bootstrap` vs workflow catalog | CLI exposes `bootstrap`; `list-workflows` uses registry with only `ingest-vacancy` and `analyze-vacancy`; `WORKFLOW_CATALOG` and `project_memory.workflow_catalog` still include `bootstrap` | `bootstrap` is simultaneously treated as setup command and catalog workflow | Creates contract drift between CLI, runtime memory and future workflow planning | `blocker` until M2 decides whether `bootstrap` belongs in the workflow catalog or must be removed from it |
| Resume root path | Real workspace has `resumes/` and no `CV/`; `analyze_vacancy.py`, `prepare_screening.py`, tests and runbook still read `CV/` | Current code path no longer matches the canonical root contract or the actual workspace layout | Real runtime can fail to find selected role resume even when the workspace is valid | `blocker` and likely implementation follow-up |
| Excel dependency policy | `ingest-vacancy` always calls `append_ingest_record(response-monitoring.xlsx, ...)`; `bootstrap` does not create workbook; docs describe Excel write as unconditional side effect | Workbook is treated as required external dependency, but failure policy is undocumented and not classified as hard precondition vs degradable mode | Leaves ambiguity around what “minimally done” means for ingest in a partially prepared workspace | `blocker` until M2 chooses either explicit hard prerequisite or degradable-mode expectation |
| Vacancy-local `adoptions.md` vs root `adoptions/` | Current code writes `vacancies/<id>/adoptions.md`; root-normalization plan already classifies it as generated staging artifact | Runtime still uses vacancy-local adoptions while long-lived canonical layer remains root `adoptions/` | Known architectural mismatch, but already documented as interim contract | `deferred_follow_up`, not a gate blocker by itself |
| Stale runtime historical trail | `show-memory` reports many stale runs and missing artifacts, but reconciliation is explicit and tested | Historical runtime noise remains, yet active diagnostics are honest and actionable | Quality and operator-noise concern, but no longer hidden corruption of current state | `deferred_follow_up`, acceptable if report-first policy is kept |

## M1 Draft Completion Matrix

| Command / workflow | Verified current behavior | Candidate minimal-done gate condition | Status after M1 |
| --- | --- | --- | --- |
| `bootstrap` | Creates workspace directories and memory files; callable from CLI; not returned by workflow registry | One model only: either `bootstrap` is an actual workflow everywhere, or it is a setup command removed from workflow catalogs and memory defaults | `needs_decision` |
| `ingest-vacancy` | Creates vacancy scaffold, writes runtime memory, appends to Excel, does not auto-publish | Side effects remain explicit and local-only; Excel dependency policy is fixed as either required precondition or graceful degradation rule | `needs_decision` |
| `analyze-vacancy` | Builds first-pass analysis, updates vacancy-local `analysis.md` and `adoptions.md`, writes runtime memory | Resume source path must align with canonical `resumes/`; vacancy-local `adoptions.md` must remain explicitly accepted as current staging artifact until future migration | `needs_fix_or_decision` |
| `show-memory` / reconciliation layer | Reports stale task state and stale historical runs explicitly; tested via `snapshot()` | Report-first reconciliation remains acceptable as the current baseline; stale history does not block feature expansion by itself | `acceptable_now` |

## M1 Gate Questions

- Should `bootstrap` stay in `WORKFLOW_CATALOG` and `project_memory.workflow_catalog`, or should it be reclassified as a setup-only CLI command outside the workflow registry?
- Is `response-monitoring.xlsx` a hard runtime prerequisite for `ingest-vacancy`, or should ingest succeed in a degraded mode when the workbook is missing or damaged?
- Must the current stack be considered blocked until all `CV/` references are migrated to `resumes/`, given that the real workspace no longer has a `CV/` directory?
- Is vacancy-local `adoptions.md` acceptable as the current runtime staging contract until a dedicated migration to root `adoptions/` happens?

## M2 Gate Decisions

| Topic | Decision | Impact on current stack |
| --- | --- | --- |
| `bootstrap` catalog boundary | `bootstrap` is a setup-only CLI command, not a runtime workflow and not a member of the workflow catalog | `WORKFLOW_CATALOG`, `project_memory.workflow_catalog`, tests and docs must stop treating `bootstrap` as a workflow entry |
| `CV/` vs `resumes/` path contract | `resumes/` is the only valid canonical resume root for current and future work | All code, tests and operator docs that still read `CV/` require remediation before the current stack can be considered minimally done |
| `response-monitoring.xlsx` dependency policy | For the current stack, workbook integration remains a hard prerequisite, not a degradable mode | `ingest-vacancy` should fail explicitly and predictably when the workbook is missing or broken; docs must state this precondition |
| Vacancy-local `adoptions.md` | Accept as the current staging/runtime artifact until a separate migration to root `adoptions/` is implemented | This does not block completion gate closure for the current stack |
| Stale runtime historical trail | Accept report-first reconciliation as sufficient current behavior | No remediation is required before feature expansion as long as diagnostics stay explicit |

## M2 Completion Checklist

| Area | Final gate status | Resolution path |
| --- | --- | --- |
| `bootstrap` catalog drift | `requires_fix` | Remove `bootstrap` from workflow catalog defaults and align memory/tests/docs to setup-only semantics |
| `CV/` -> `resumes/` drift | `requires_fix` | Remediate code/tests/docs to use `resumes/` consistently |
| Excel dependency ambiguity | `requires_fix` | Keep workbook mandatory, but encode the rule explicitly in code/tests/docs |
| Vacancy-local `adoptions.md` | `explicitly_deferred` | Keep as accepted interim contract until a later adoptions-pipeline workstream |
| Stale runtime history | `done_now` | Current reconciliation behavior is sufficient for gate purposes |

## Milestones

### M1. Completion Gate Evidence Baseline

- Status: `done`
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
  - Подтверждён реальный runtime blocker: в workspace существует `resumes/` и отсутствует `CV/`, тогда как `analyze-vacancy`, `prepare-screening`, tests и runbook всё ещё используют `CV/`.
  - Excel integration по-прежнему выглядит как unconditional hard dependency, но это ещё не зафиксировано как явное product decision.

### M2. Gate Decisions And Minimal-Done Criteria

- Status: `done`
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
  - `bootstrap` reclassified as setup-only CLI command outside workflow catalog.
  - `resumes/` confirmed as the only valid runtime resume root; `CV/` drift remains a real blocker until fixed.
  - `response-monitoring.xlsx` kept as a hard prerequisite for the current stack; remediation should make this rule explicit and operator-visible.

### M3. Follow-Up Packaging

- Status: `done`
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
  - Blockers from M2 are packaged into `2026-04-22-current-stack-contract-remediation.md`.
  - Feature planning remains gated behind execution of that remediation plan.

## Decision log

- `2026-04-22 09:10` — Completion gate вынесен в отдельный plan, а не оставлен абзацем внутри master plan. — Здесь нужен самостоятельный contradiction ledger и gate checklist по текущему стеку. — Это снижает риск снова смешать cleanup, safety findings и future feature planning.
- `2026-04-22 09:17` — Для completion gate собран первый contradiction ledger и draft completion matrix. — Это перевело workstream из стадии baseline collection в стадию gate decisions: теперь спор идёт не о том, где доказательства, а о том, что считать blocker-ом для feature expansion. — M1 можно считать завершённым.
- `2026-04-22 10:03` — Gate decisions приняты и упакованы в отдельный remediation plan. — Это снимает двусмысленность по текущему стеку: `bootstrap` больше не должен жить в workflow catalog, `resumes/` признан единственным валидным resume root, а `response-monitoring.xlsx` закреплён как обязательный prerequisite текущего ingest path. — Completion gate как planning/workstream можно считать завершённым.

## Progress log

- `2026-04-22 09:10` — Workstream открыт на основании master M4 и первичного baseline по CLI, runtime memory и tests. — `python run_agent.py --root ../.. list-workflows` показывает 2 workflow, `show-memory` показывает registry/catalog mismatch и stale historical trail, `python -m unittest discover -s tests` -> `39 tests, OK`. — Status: `in_progress`.
- `2026-04-22 09:17` — M1 закрыт: в план добавлены contradiction ledger, draft completion matrix и gate questions по текущему стеку. — Дополнительная верификация показала, что `bootstrap` расходится между registry и memory catalog, `ingest-vacancy` не имеет зафиксированной Excel failure policy, а `analyze-vacancy` всё ещё читает `CV/`, хотя реальный workspace уже использует `resumes/`. — Status: `done`.
- `2026-04-22 10:03` — M2 и M3 закрыты: gate decisions зафиксированы, а remediation path вынесен в отдельный execution plan. — Non-blocking items (`vacancy-local adoptions.md`, stale runtime history) оформлены как допустимые interim contracts/follow-ups; blocking items (`bootstrap` catalog drift, `CV/` -> `resumes/`, explicit Excel prerequisite) переданы в remediation plan. — Status: `done`.

## Current state

- Current milestone: `M2`
- Current status: `done`
- Next step: `Исполнить remediation plan `2026-04-22-current-stack-contract-remediation.md` и снять blocker-ы current workflow stack перед возвратом в master plan.` 
- Active blockers:
  - none
- Open questions:
  - none

## Completion summary

- Собран и закрыт completion gate для текущего workflow-стека: contradictions сведены в один ledger, по ним приняты явные решения и отделены blocker-ы от допустимых follow-up.
- Подтверждено, что blocking remediation сейчас касается трёх зон: `bootstrap` catalog drift, `CV/` -> `resumes/` path drift и explicit Excel prerequisite policy.
- Подтверждено, что vacancy-local `adoptions.md` и report-first stale runtime reconciliation не блокируют следующий этап.
- Следующий execution step вынесен в `2026-04-22-current-stack-contract-remediation.md`.
