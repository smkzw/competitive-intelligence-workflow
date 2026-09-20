# Conference Context: ci-phase9-task91-correction-approval-review

Created: 2026-09-01 00:39:32 CST
Objective: 独立审查 Task 9.1 修订审批实现与测试：重点挑战稳定目标绑定、验证完整性、报告所有者批准边界、独立质控、快照项目与版本约束、追加历史、幂等恢复；只审查和报告，不修改文件，不把实现者自测视为验收。
Task type: `finite_code_task`
Risk: `medium`
Conference mode: `serial`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

- Ordinary tasks remain Codex-direct. Chinese labels or Chinese sentence work uses its declared execution route and does not start a conference.
  - This packet uses one Codex-led conference object (`general_single_object`) with no sub-venue chair. Its effective `CST` route chain is `codebuddy-cli/deepseek-v4-flash:max -> grok-build/grok-4.6:medium -> cursor/cursor-grok-4.6:medium -> openai-codex/gpt-5.6-luna:max`; the packet branch is recorded at creation and filtered against the actual execution route nodes recorded below. Before a new session, the runner rechecks the Beijing period; an already-started session is never rerouted.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Execution-Conference Model Deduplication

- Linked execution task: `ci-phase9-task91-correction-approval`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `zcode/glm-5.3-flash`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- `.trellis/tasks/08-31-phase-9-task-91-correction-approval/prd.md`
- `.trellis/tasks/08-31-phase-9-task-91-correction-approval/design.md`
- `schemas/correction-proposal.schema.json`
- `src/ci_workflow/application/correction_service.py`
- `src/ci_workflow/graph/definitions/correction.py`
- `src/ci_workflow/graph/transitions.py`
- `src/ci_workflow/graph/guards.py`
- `src/ci_workflow/storage/snapshot_store.py`
- `tests/contract/test_correction_proposal_contract.py`
- `tests/integration/test_correction_flow.py`
- `tests/integration/test_correction_service.py`
- 本轮独立运行测试结果；实现者报告只作为线索，不作为验收证据。

## Scope

- In scope: 只读审查 Task 9.1 合同、服务、状态迁移、快照发布和对应测试；可运行非破坏性测试并报告可复现问题。
- Out of scope: 修改源码、Phase 9.2 以后功能、前端与视觉、PDF/PPT、安全测试、联网调研、生产环境。

## Success Criteria

- Each selected primary route returns an auditable output or an explicit health/fallback reason.
- The prompt uses the correct Agent identity, provider/model, effort, tools-enabled policy, and same-session continuation policy.
- The runner records session, usage/tool observations, fallback decisions, and failure reasons without `--max-turns 1`.
- No production path is read or modified; Codex retains final acceptance.
- 明确给出接受或需修订意见；每项缺陷需指向具体文件/函数/测试缺口，并区分阻断问题与后续优化。

## Parallel Work Rule

For logic-heavy, rigor-sensitive, or artifact-heavy tasks, each participant independently runs the whole bounded workflow and writes a separate output. Leads compare after all available participant outputs are in or explicitly marked pending.

## Timeout Policy

- Participant soft wait: 60 minutes.
- Large-task participant wait: 120 minutes.
- Chair hard wait: 120 minutes.
- Failure rule: Do not fail a model for slow response alone; fail only on terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no useful progress after the high-budget same-session recovery loop. A catalog/auth/transport health preflight timeout or malformed response is diagnostic and must still allow one live route attempt; explicit user routes also proceed when the catalog is stale or incomplete, while a genuinely missing CLI or native transport boundary may block. If a resumable session exists after a step/size boundary, continue it before fallback; repeated identical output/tool evidence triggers the no-progress breaker.
- Pass/turn boundary: one conference prompt is one conference pass. The
  `--max-turns` value controls internal Agent tool-calling turns and is never
  set to 1 for substantive conference execution; generated participant and
  chair commands use the route budgets recorded by the guard.

## Risk Boundaries

- External Agents are advisory; Codex remains final authority.
- Codex owns visual/browser/PPT/PDF/rendered checks, live authority checks, final clinical/regulatory conclusions, and production writes.
- Do not mark a slow model failed solely due to latency.

## Loop Log

- 2026-09-01 00:39:32 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
