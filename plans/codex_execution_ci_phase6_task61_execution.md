# Codex Execution Plan: ci_phase6_task61_execution

Objective: 实现并验证 Task 6.1：B/C 可审计研究角色以及 B 类终点与时间窗版本化兼容合同，严格按三份指定测试先 RED 后 GREEN，不创建页面，不改变 A 类语义。

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | 实现 reports/common/study_roles.py、研究角色策略 YAML 及 tests/reports/test_study_role_policy.py 的五类排除、支持层、特殊核心和 C 决策域合同。 | `runs/execution/ci_phase6_task61_execution/worker_01.md` |
| `worker_02` | 实现 reports/b/contracts.py 的研究角色输出、study_role/publication_role 永久分列及 tests/reports/b/test_trial_roles.py。 | `runs/execution/ci_phase6_task61_execution/worker_02.md` |
| `worker_03` | 实现终点与时间窗兼容 YAML、严格加载和确定性匹配及 tests/reports/b/test_endpoint_compatibility.py，保留原值、规则 ID 和差异标签。 | `runs/execution/ci_phase6_task61_execution/worker_03.md` |

## Manager

No execution manager is dispatched for this route; Codex reviews the worker outputs directly.

## Codex Acceptance

TODO: verify artifacts, tests, source claims, rendered surfaces, blockers, and user-facing completeness.
