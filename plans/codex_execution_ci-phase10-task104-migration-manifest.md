# Codex Execution Plan: ci-phase10-task104-migration-manifest

Objective: 完成 Task 10.4 批准迁移清单闭环：精确保留白名单、显式排除旧实现与敏感运行状态、提供 schema/测试/中文验收证据，但不执行真实旧根切换或删除。

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 只读核对批准规格、D01-D70、项目内化设计合同、Logo、授权 fixture 与回归断言的来源链、摘要和最终目标，输出白名单建议与缺口。 | `runs/execution/ci-phase10-task104-migration-manifest/worker_01.md` |
| `worker_02` | 审查并提出 legacy manifest schema 与闭环测试的不变量、负例和失败关闭要求，不修改任务范围。 | `runs/execution/ci-phase10-task104-migration-manifest/worker_02.md` |
| `worker_03` | 只读核对旧代码/schema/模板/QC、全局事实库、会话/缓存/明文凭据、绝对路径和兼容包装器的排除覆盖，并审阅中文迁移说明应披露的边界。 | `runs/execution/ci-phase10-task104-migration-manifest/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

TODO: verify artifacts, tests, source claims, rendered surfaces, blockers, and user-facing completeness.
