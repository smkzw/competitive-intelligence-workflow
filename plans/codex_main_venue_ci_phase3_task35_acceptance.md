# Codex Main-Venue Plan: ci_phase3_task35_acceptance

Date: 2026-08-13
Objective: 独立验收 Task 3.5 部分交付协调器是否真实满足 v1.2：选择合同不可漂移、报告/格式独立、终态区分、重复阻断可恢复、报告版本重绑和共享事件库读路径不可伪造

## Task Decomposition

1. 两名参与者在彼此隔离的上下文中读取 v1.2、协调器、图内核与两份计划场景测试，不读取执行者报告或对方结论。
2. 运行 Task 3.5 精确节点，并在系统临时目录重建真实状态顺序，攻击合同漂移、交付/阻断并发、连续重开、格式版本恢复和报告版本重绑。
3. 只读输出 PASS/FAIL 与 P0/P1/P2；P0/P1 修复后沿用原参与者 session 复验。
4. Codex 决定是否需要最小状态表勘误，独立执行全库、静态、打包和差异验收，最后更新 Trellis。

## Source Packet

- `AGENTS.md`
- `context/ci_phase3_task35_acceptance_conference_context.md`
- `context/ci_phase3_task35_context.md`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md`
- `src/ci_workflow/graph/{recovery,executor,reducer,transitions,guards}.py`
- `tests/graph/{test_transition_matrix,test_partial_delivery,test_partial_delivery_blocked}.py`

## Participant Assignments

| Role | Provider | Model | Output |
|---|---|---|---|
| `general_pi_qwen38` | `alibaba` | `qwen3.8-max` | `runs/conference/ci_phase3_task35_acceptance/general_pi_qwen38.md` |
| `general_grok45` | `grok-build` | `grok-4.6` | `runs/conference/ci_phase3_task35_acceptance/general_grok45.md` |

## Conference Panel Coordination

- No sub-venue chair. Codex leads the assigned panel directly.

## Main-Venue Review

- Codex performs the final synthesis and acceptance.
- This conference mode has no Reasonix second-review role.

## Timeout And Retry Tracking

- Pi/Qwen、Grok Build 均在首次验收时建立真实 session；修复后继续原 session，无 fallback。
- Pi/Qwen 修复复核等待约 30 分钟后完成；Grok 两次只返回过程句，归类为不完整输出而非路线失败，在原 session 补发最终报告。
- 未因延迟或空窗重派；最终采用 Pi 完整临时探针报告和 Grok 最终补全报告。Grok 未取得修复后 pytest 退出码的声明未纳入机械通过证据。

## Codex Verification Checklist

- [x] 两名参与者身份与声明路线一致，无 fallback。
- [x] 首次交付与其余对象同时穷尽时，`running`/`awaiting_user` 可直接到达部分交付受阻。
- [x] 陈旧合同、未绑定版本、同版本选择漂移全部失败关闭。
- [x] 连续项目/格式阻断重开、报告版本重绑、重放与原因漂移有独立反例。
- [x] 三个精确节点、图测试、全库、Ruff、strict mypy、compileall、wheel 和差异检查由 Codex 实际执行。
- [x] P0/P1=0 后才接受；Task 3.6/3.7 和用户报告视觉未提前接受。
