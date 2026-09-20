# Codex Execution Plan: ci-phase9-task92-incremental-refresh

Objective: 实现 Task 9.2 增量刷新与影响传播：扩大截止日只晋级新适格候选，GateSpec 收紧只重算受影响对象，父合同和历史快照不可变，首版只处理站点式 HTML。

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 实现 graph/impact.py 和 graph/definitions/refresh.py：稳定影响闭包、复用集合、重大合同变化再基线分支；不得复制既有 GateSpec 规则。 | `runs/execution/ci-phase9-task92-incremental-refresh/worker_01.md` |
| `worker_02` | 实现 application/refresh_service.py：父版本绑定、截止日扩展、候选晋级、GateSpec 收紧、局部重建回执、不可变历史和幂等恢复。 | `runs/execution/ci-phase9-task92-incremental-refresh/worker_02.md` |
| `worker_03` | 新增 tests/integration/test_incremental_refresh.py 并补必要的契约/回归断言：两个批准节点、父版本不变、错误截止日、重大合同变化、影响范围和中断恢复。 | `runs/execution/ci-phase9-task92-incremental-refresh/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

已核验当前源码、三份工人报告、事件/快照绑定、中文失败说明与站点优先范围。聚焦验收 58 项、完整集成 290 项、目标 Ruff/mypy、包完整性均通过；本任务不含用户可见页面变化，无需视觉复核。
