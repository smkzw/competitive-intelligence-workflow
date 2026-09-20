# Codex Execution Plan: ci_phase6_task64_execution

Objective: 按批准设计完成 Task 6.4 的 B 类疗效—安全性气泡图、比较矩阵状态与同步交互合同，不生成综合分数或排名。

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 实现并测试比较行、默认横纵轴语义、原始事实保留、气泡面积公式与未知样本量边界；仅修改 pages.py 与 test_bubble_area.py。 | `runs/execution/ci_phase6_task64_execution/worker_01.md` |
| `worker_02` | 实现并测试可比、不兼容、未报告、不适用、待核实矩阵状态，以及不可绘制组合不生成零坐标；仅修改 pages.py 与 test_matrix_states.py。 | `runs/execution/ci_phase6_task64_execution/worker_02.md` |
| `worker_03` | 实现并测试多维选择状态、图表/完整表/提示/证据/URL 同步、可逆重置和无排名；仅修改 pages.py 与 test_matrix_states.py。 | `runs/execution/ci_phase6_task64_execution/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

TODO: verify artifacts, tests, source claims, rendered surfaces, blockers, and user-facing completeness.
