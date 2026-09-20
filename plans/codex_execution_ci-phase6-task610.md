# Codex Execution Plan: ci-phase6-task610

Objective: 完成 Phase 6 Task 6.10：建立 fresh PNH 与三个独立 D70 案例，修复当前运行绑定和 B 报告边界，完成确定性验收；不得发布 Phase 6。

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 实现并验证 fixtures/positive/b-pnh 与三个 D70 独立输入包、catalog 摘要及 RED/GREEN 案例合同。 | `runs/execution/ci-phase6-task610/worker_01.md` |
| `worker_02` | 实现并验证 fresh PNH 与三个 D70 项目的当前 run_id/snapshot_id/manifest_sha256/mtime 绑定、基线阻断恢复和处置非阻断语义。 | `runs/execution/ci-phase6-task610/worker_02.md` |
| `worker_03` | 运行 Phase 6 精确确定性测试与 A 类回归，深挖任何零竞品、零试验、字段缺失或状态异常并形成紧凑交接。 | `runs/execution/ci-phase6-task610/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

TODO: verify artifacts, tests, source claims, rendered surfaces, blockers, and user-facing completeness.
