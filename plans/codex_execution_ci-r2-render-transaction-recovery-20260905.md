# Codex Execution Plan: ci-r2-render-transaction-recovery-20260905

Objective: 修复 A/B/C HTML 渲染在未发布目录中断后的可恢复事务边界，同时保持任何已发布或已绑定产物严格不可覆盖。

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 设计并实现共享的未发布渲染目录事务边界及 A 类接入；先写失败测试，拒绝覆盖任何已有 manifest 或完成绑定。 | `runs/execution/ci-r2-render-transaction-recovery-20260905/worker_01.md` |
| `worker_02` | 独立实现或评估 B/C 渲染接入与中断恢复测试，确保只清理当前项目内可证明未发布的精确目录。 | `runs/execution/ci-r2-render-transaction-recovery-20260905/worker_02.md` |
| `worker_03` | 只读审计当前 A/B/C 渲染、事件、manifest、科学复核绑定和恢复路径，给出最小失败关闭负向矩阵与对前两项的验收风险。 | `runs/execution/ci-r2-render-transaction-recovery-20260905/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

Codex verified the shared transaction, A/B/C adapters, current-run and scientific-review
binding guards, focused tests, full integration, strict quality gate and disposable bundle.
No rendered visual design changed, so this slice does not claim visual acceptance. Details are
recorded in the paired review and metrics documents.
