# Codex Execution Plan: ci-phase8-task87b-pptx-confirmation-interrupt

Objective: 补齐原实施计划 Task 8.7 的 A/B/C 同快照 PPTX 来源包、八项中文确认中断与恢复，使 Task 8.8 能在明确确认结果上严格串行生成

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 实现 src/ci_workflow/renderers/pptx_master/source_pack.py 与对应 Schema/测试：从锁定报告数据为 A/B/C 生成中文 Markdown source pack 和摘要清单，不生成 SVG | `runs/execution/ci-phase8-task87b-pptx-confirmation-interrupt/worker_01.md` |
| `worker_02` | 实现 src/ci_workflow/renderers/pptx_master/confirmation.py 与对应 Schema/测试：八项推荐、确认结果验证、结果覆盖与一次性确认会话幂等关闭 | `runs/execution/ci-phase8-task87b-pptx-confirmation-interrupt/worker_02.md` |
| `worker_03` | 实现 adapter 与 fixture/project run 集成及图/CLI 测试：首次运行仅中断 PPTX，保存确认入口与清单，读取结果后恢复且不重复询问 | `runs/execution/ci-phase8-task87b-pptx-confirmation-interrupt/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

TODO: verify artifacts, tests, source claims, rendered surfaces, blockers, and user-facing completeness.
