# Codex Execution Plan: ci_phase6_task66_execution

Objective: 完成 Task 6.6：从已验收 BaselineObservation 构建人口学、疾病语境和严重程度的确定性视图模型，实现图前表后同源投影、科学兼容分桶、完整筛选/URL/证据焦点同步与真实空状态，并用 RED、回归和医学语义对抗复核证明不补造或混画数据。

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 读取活动 Trellis Task 6.6、批准设计和既有 baseline 合同，编写图形资格、兼容分桶、完整表格、默认顺序、筛选/URL/证据/空状态失败测试并保存真实 RED。 | `runs/execution/ci_phase6_task66_execution/worker_01.md` |
| `worker_02` | 实现最小 baseline_views 模块：强类型视图、图表面板、无损表格、确定性默认选择、筛选适用性、证据焦点和标准库 URL 往返；不创建物理 HTML。 | `runs/execution/ci_phase6_task66_execution/worker_02.md` |
| `worker_03` | 运行目标与相关回归、Ruff、strict mypy 和对抗性医学语义检查，深挖任何空图、丢行、错误混桶、筛选自动放宽或工程化中文问题并给 Codex 交接。 | `runs/execution/ci_phase6_task66_execution/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

TODO: verify artifacts, tests, source claims, rendered surfaces, blockers, and user-facing completeness.
