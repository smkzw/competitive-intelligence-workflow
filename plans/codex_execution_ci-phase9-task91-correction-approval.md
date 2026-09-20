# Codex Execution Plan: ci-phase9-task91-correction-approval

Objective: 实现 Task 9.1 来源关联修订合同、追加式应用服务和明确用户批准后的幂等发布，并保持首版站点式 HTML 范围与科学真源边界

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 实现 correction-proposal schema、包清单登记与合同测试，禁止用户可见工程化标签 | `runs/execution/ci-phase9-task91-correction-approval/worker_01.md` |
| `worker_02` | 实现追加式 correction service、事件与幂等发布，复用现有 SQLite/内容摘要约定 | `runs/execution/ci-phase9-task91-correction-approval/worker_02.md` |
| `worker_03` | 实现 correction graph definitions 与集成测试，复用现有 transitions/guards 并验证所有合法迁移和发布前置条件 | `runs/execution/ci-phase9-task91-correction-approval/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

Codex will verify schema/source copies and package manifest hashes; all transition branches; explicit owner approval; fail-closed publish prerequisites; append-only/idempotent replay; targeted pytest, mypy and Ruff; and preservation of the current dirty worktree. This backend task does not require a visual conference.
