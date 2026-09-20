# Codex Main-Venue Plan: ci-phase9-task92-incremental-refresh-review

Date: 2026-09-01
Objective: 独立复核 Task 9.2 增量刷新最终实现：重点挑战真实门槛结果绑定、影响报告闭包、独立科学质控、不可变历史、快照中断恢复、站点优先范围与中文用户阻断说明；只审查，不修改文件。

## Task Decomposition

1. 独立挑战门槛规则、证据快照、质控输入、变化台账与影响闭包绑定。
2. Codex 修订可复现缺口并运行真实回归。
3. 沿用同一会话复核修订，直至无阻断性技术问题。

## Source Packet

设计 v1.2 §17.2、Task 9.2 Trellis 合同、三份执行报告、当前源码、集成测试、执行 metrics/review。

## Participant Assignments

| Role | Provider | Model | Output |
|---|---|---|---|
| `general_single_object` | `codebuddy-cli` | `deepseek-v4-flash` | `runs/conference/ci-phase9-task92-incremental-refresh-review/general_single_object.md` |

## Conference Panel Coordination

- No sub-venue chair. Codex leads the assigned panel directly.

## Main-Venue Review

- Codex performs the final synthesis and acceptance.
- This conference mode has no Reasonix second-review role.

## Timeout And Retry Tracking

CodeBuddy 首轮、第二轮、第三轮与最终针对性复核均在同一会话完成；无 fallback、无超时、无迟到输出。第三轮发现并行计划冲突后继续修订，最终轮给出 Pass。

## Codex Verification Checklist

- [x] 门槛规则指纹与子合同绑定。
- [x] 门槛、报告与证据快照同源。
- [x] 科学质控绑定真实审查包和已锁定证据引用。
- [x] 变化台账六类状态完整覆盖。
- [x] 页面到 HTML 格式投影及相邻层传播。
- [x] 截止日、联合刷新、否决/过期、并行计划与中断恢复回归。
- [x] Codex 真实执行测试、Ruff、mypy 与包完整性验证。
