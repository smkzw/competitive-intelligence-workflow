# Codex Main-Venue Plan: ci-phase9-task91-correction-approval-review

Date: 2026-09-01
Objective: 独立审查 Task 9.1 修订审批实现与测试：重点挑战稳定目标绑定、验证完整性、报告所有者批准边界、独立质控、快照项目与版本约束、追加历史、幂等恢复；只审查和报告，不修改文件，不把实现者自测视为验收。

## Task Decomposition

1. 独立读取合同、服务、图定义、快照与测试，不读取执行者推理作为结论。
2. 挑战最新快照、批准、质控、幂等与中断恢复边界。
3. Codex 复现问题、修正并运行任务测试与共享回归。
4. 同一会话复核修订，Codex 完成最终判断。

## Source Packet

权威来源为 Task 9.1 PRD/design、修订 Schema、应用服务、冻结迁移与守卫、快照
存储、数据库迁移和三组测试；执行者报告只作线索。

## Participant Assignments

| Role | Provider | Model | Output |
|---|---|---|---|
| `general_single_object` | `codebuddy-cli` | `deepseek-v4-flash` | `runs/conference/ci-phase9-task91-correction-approval-review/general_single_object.md` |

## Conference Panel Coordination

- No sub-venue chair. Codex leads the assigned panel directly.

## Main-Venue Review

- Codex performs the final synthesis and acceptance.
- This conference mode has no Reasonix second-review role.

## Timeout And Retry Tracking

首轮与第二轮均在 2026-09-01 完成；第二轮因首轮提出可操作缺陷而在同一 session
继续。无超时、无失败、无晚到输出、无回退。

## Codex Verification Checklist

- [x] 角色边界与路由隔离。
- [x] 源码与合同逐项核验。
- [x] 31 项 Task 9.1 测试。
- [x] 16 项共享回归。
- [x] Ruff、mypy 与 Schema 副本一致性。
- [x] 同会话独立复核修订结果。
