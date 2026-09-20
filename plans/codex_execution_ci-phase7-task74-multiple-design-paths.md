# Codex Execution Plan: ci-phase7-task74-multiple-design-paths

Objective: 实现并验证 C 类事实模式、差异、异常点和至少两条有证据候选设计路径，禁止唯一最佳方案

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 建立至少两条路径、前提、权衡和观察证据绑定的真实 RED | `runs/execution/ci-phase7-task74-multiple-design-paths/worker_01.md` |
| `worker_02` | 最小实现 synthesis.py 的事实模式与多路径综合并保持输入顺序不变 | `runs/execution/ci-phase7-task74-multiple-design-paths/worker_02.md` |
| `worker_03` | 独立攻击隐性排名、凑数路径、产品特异臆测、无原始值归一化和共享合同回归 | `runs/execution/ci-phase7-task74-multiple-design-paths/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

ACCEPTED：三名执行角色均在声明边界内完成；Codex 修复独立审阅发现的标点差异凑数缺陷，并通过 21 项聚焦测试、109 项 C 类测试、285 项关联回归及 Ruff 检查。Task 7.4 不含页面视觉验收，页面进入 Task 7.5 单独执行。
