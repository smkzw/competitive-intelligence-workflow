# Codex Main-Venue Plan: ci-phase9-task93-optional-monitoring-review

Date: 2026-09-01
Objective: 独立审查 Task 9.3 当前实现：候选是否可能越权成为事实或触发发布，去重与 model_copy 防漂移是否可靠，技术失败/未发现/未公开是否真实区分，用户处置和刷新交接是否只读且可恢复，监测是否可卸载，中文提示是否面向医学经理。只给出可复现问题与通过条件，不修改代码。

## Task Decomposition

1. 独立挑战候选越权、去重漂移、处置锁定、技术诊断真实性与可卸载性。
2. Codex 修复可复现缺口并运行真实回归。
3. 沿用同一会话复核当前树，直到无剩余 P0/P1/P2。

## Source Packet

设计 v1.2 §17.3、Task 9.3 Trellis 合同、三份执行报告、当前源码、合同/集成/图测试与执行验证记录。

## Participant Assignments

| Role | Provider | Model | Output |
|---|---|---|---|
| `general_single_object` | `codebuddy-cli` | `deepseek-v4-flash` | `runs/conference/ci-phase9-task93-optional-monitoring-review/general_single_object.md` |

## Conference Panel Coordination

- No sub-venue chair. Codex leads the assigned panel directly.

## Main-Venue Review

- Codex performs the final synthesis and acceptance.
- This conference mode has no Reasonix second-review role.

## Timeout And Retry Tracking

CodeBuddy 四轮均沿用会话 `1227fc2a-3190-435d-a29e-ad5a776b4ece`；无 fallback、无超时、无迟到输出。每轮发现均在当前树修订后由同一会话重新核验。

## Codex Verification Checklist

- [x] 候选不能直接成为事实、声明、正式快照或报告发布输入。
- [x] 去重摘要、候选 ID 与交接单跨对象绑定可重新推导。
- [x] 交接后处置锁定，精确重放可自愈投影。
- [x] 无变化、未公开、可恢复技术失败与需用户协助严格区分。
- [x] 用户可见诊断说明为中文，恢复方法不重复。
- [x] 移除监测后核心项目、刷新、修订与图执行仍可运行。
- [x] Codex 真实执行测试、Ruff、mypy 与包完整性验证。
