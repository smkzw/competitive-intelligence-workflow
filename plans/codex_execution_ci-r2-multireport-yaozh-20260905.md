# Codex Execution Plan: ci-r2-multireport-yaozh-20260905

Objective: 闭合 v1.3 多报告 A/B/C 联合产品执行与每项目一次 Yaozh 选择持久化，不放宽严格 research submission、科学复核或 HTML-only 边界。

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 实现并测试已提交 A/B/C 多报告载荷逐报告独立执行、状态聚合与幂等 resume；不得建立融合门户。 | `runs/execution/ci-r2-multireport-yaozh-20260905/worker_01.md` |
| `worker_02` | 实现并测试 Yaozh 访问选择的项目级持久化、一次回答、幂等重放和无凭据 CLI 边界。 | `runs/execution/ci-r2-multireport-yaozh-20260905/worker_02.md` |
| `worker_03` | 独立审计多报告与 Yaozh 方案的失败关闭、现有单报告兼容、bundle/Skill 命令和最小负向矩阵，提出最小集成建议。 | `runs/execution/ci-r2-multireport-yaozh-20260905/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

TODO: verify artifacts, tests, source claims, rendered surfaces, blockers, and user-facing completeness.
