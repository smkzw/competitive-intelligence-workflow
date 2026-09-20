# Codex Execution Plan: ci_phase6_task65_execution

Objective: 完成 Task 6.5：建立 B 类基线观察事实合同、科学兼容键、JSON Schema 与现有逐试验逐组 GateSpec 的严格绑定，并以真实 RED/GREEN、回归和独立医学语义复核证明不会跨组借值或放宽草稿阻断。

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 先读取活动 Trellis 任务、批准设计、B-v1 GateSpec 和既有 gate API，编写并运行失败测试，保存真实 RED 证据。 | `runs/execution/ci_phase6_task65_execution/worker_01.md` |
| `worker_02` | 实现最小 BaselineObservation 合同、科学兼容键、稳定身份、JSON Schema 及到既有 GateEvidenceBinding 的严格转换，不新增门槛引擎。 | `runs/execution/ci_phase6_task65_execution/worker_02.md` |
| `worker_03` | 运行定向与相关回归、静态检查和对抗性用例，核对来源未公开与技术路径未解决的区分，输出紧凑交接供 Codex 验收。 | `runs/execution/ci_phase6_task65_execution/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

TODO: verify artifacts, tests, source claims, rendered surfaces, blockers, and user-facing completeness.
