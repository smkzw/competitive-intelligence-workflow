# Codex Execution Plan: ci-phase8-task87-ppt-master-job-contract

Objective: 建立可验证、可恢复、严格串行的 PPT Master 作业合同，使 A/B/C 可编辑 PPTX 在后续阶段可从同一报告快照安全启动、暂停、恢复和验收

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 设计并实现 PPT Master 作业状态、阶段收据、锁定快照和串行约束的类型化合同与 JSON Schema | `runs/execution/ci-phase8-task87-ppt-master-job-contract/worker_01.md` |
| `worker_02` | 实现可恢复中断的恢复指针、前置产物校验、过期/错序/跨报告污染拒绝逻辑 | `runs/execution/ci-phase8-task87-ppt-master-job-contract/worker_02.md` |
| `worker_03` | 补充中文用户指引、代表性正负测试、架构合同与 Trellis 验收记录 | `runs/execution/ci-phase8-task87-ppt-master-job-contract/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

TODO: verify artifacts, tests, source claims, rendered surfaces, blockers, and user-facing completeness.
