# Codex Execution Plan: ci_phase6_task68_execution

Objective: 建立 B 类试验完成情况页面族的强类型视图模型，使图表、状态矩阵、完整表格、证据和网址状态由同一事实行同步生成，并以中文医学语义处理人数/事件、原因资格和非阻断披露。

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 基于 Task 6.8 PRD 与设计建立真实 RED 测试，覆盖单试验流转、跨试验面板、原因图形资格、无数值状态矩阵、多选筛选、网址、证据焦点、重置和同步失败关闭。 | `runs/execution/ci_phase6_task68_execution/worker_01.md` |
| `worker_02` | 实现 disposition_views.py 的选择状态、表行、图表面板、状态矩阵、证据链接、筛选适用性和不可变同步视图合同，使 RED 测试通过。 | `runs/execution/ci_phase6_task68_execution/worker_02.md` |
| `worker_03` | 运行定向与广泛回归并进行只读医学语义对抗审阅，重点排查原因堆叠图误用、人数事件混淆、缺失转零、筛选失配、网址漂移和图表/表格/证据不同步。 | `runs/execution/ci_phase6_task68_execution/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

TODO: verify artifacts, tests, source claims, rendered surfaces, blockers, and user-facing completeness.
