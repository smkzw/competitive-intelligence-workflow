# Codex Execution Plan: ci-phase9-task93-optional-monitoring

Objective: 依据已批准 Task 9.3 合同，实现可选监测与去重变更候选；只生成正常刷新交接，不自动接纳事实、建立正式快照或发布报告，并保持核心工作流可在移除监测后运行。

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 实现并测试变更候选 JSON Schema、Python 合同、稳定去重摘要和 package-manifest 双布局登记。 | `runs/execution/ci-phase9-task93-optional-monitoring/worker_01.md` |
| `worker_02` | 实现并测试 monitoring_service 的追加事件、候选投影恢复、技术诊断、用户处置和只读刷新交接。 | `runs/execution/ci-phase9-task93-optional-monitoring/worker_02.md` |
| `worker_03` | 实现并测试监测图节点合同、内部 Skill 中文边界、可卸载性及项目/刷新回归。 | `runs/execution/ci-phase9-task93-optional-monitoring/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

Codex 已复核三份执行报告与当前源码，并运行 66 项聚焦测试、320 项完整集成测试、目标 Ruff、目标 mypy 和包完整性验证。独立会商发现的处置锁定、跨候选绑定、来源版本语义、跨项目写入、交接投影恢复及观察入口中文/去重缺口均已修复并由反例覆盖。Task 9.3 不新增用户可见页面，视觉验收不适用。
