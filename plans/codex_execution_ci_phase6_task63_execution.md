# Codex Execution Plan: ci_phase6_task63_execution

Objective: 按批准设计完成 Task 6.3 的 B 类安全性事实、披露状态、多维热图与完整 AE 视图合同，并以真实测试证明不误导、不排名、不丢失完整事件集。

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 实现并测试 SafetyFactRow、披露状态数值一致性、来源谱系、阈值/技术异常分离及保守术语映射；仅修改 safety.py 与 test_ae_state_semantics.py。 | `runs/execution/ci_phase6_task63_execution/worker_01.md` |
| `worker_02` | 实现并测试同事件可比语境、多维热图、治疗—对照并列、多试验分列、单元格数值和非数值状态不着色；仅修改 safety.py 与 test_safety_heatmap.py。 | `runs/execution/ci_phase6_task63_execution/worker_02.md` |
| `worker_03` | 实现并测试默认安全维度、约 10–15 行常见 AE 确定性选择、完整事件搜索展开及无安全性排名；仅修改 safety.py 与 test_safety_heatmap.py。 | `runs/execution/ci_phase6_task63_execution/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

TODO: verify artifacts, tests, source claims, rendered surfaces, blockers, and user-facing completeness.
