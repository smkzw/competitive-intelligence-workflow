# Task Context: ci_phase3_task32

Created: 2026-08-12 18:20:36
Objective: 实现并独立验收 Task 3.2 双重穷尽、中文证据不足说明和全路径无草稿约束，关闭科学与用户体验假绿后提交
Task type: `finite_code_task`
Risk: `high`
Selected agent route: `cms-smk` / `deepseek-v4-flash` / `max`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §10.3–10.5。
- `/Users/smkzw/Documents/AI Products/.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` Task 3.2。
- `.trellis/tasks/08-12-phase-3-evidence-gates-recovery/{prd,design,implement}.md`。
- Task 3.1 已接受提交 `99877f9` 及 `docs/acceptance/runs/task-3.1/`，作为不可变输入。
- 当前 Task 3.2 实现、四份指定集成测试和 `schemas/blocker-audit.schema.json`。

## Scope

- In scope: Task 3.2 双角色逐缺口穷尽、科学缺失与技术失败分离、证据不足 JSON/中文说明、A/B/C 每个适用关键单元与空/冲突/科学质控否决场景的无草稿及零下游约束。
- In scope: 关闭测试自证、记录未绑定、真实 GateSpec 未被执行、用户说明泄露英文/内部标签等假绿。
- Out of scope: Task 3.3+、报告渲染、视觉报告、连接器扩展、安全性测试、Phase 0–2 与已接受 Task 3.1 语义修改。

## Success Criteria

- 每个非空关键单元用真实 Task 3.1 原子评估结果证明“其他适用关键单元均满足，仅目标对象/单元阻断”，并与阻断说明逐对象精确绑定。
- A/B/C 科学质控否决都从真实 GateSpec 已通过结果出发；恢复/穷尽判断绑定同报告、同快照与双重穷尽记录。
- 路线回执、恢复轮次、独立复核和技术诊断在摘要与内容层不可被调包；所有适用路线与回执逐缺口可追溯。
- `audit.md` 面向中文临床试验医学人员，只呈现对象、缺失/冲突、已查范围、原因、用户最小动作、原文链接和清晰续接位置，不显示路线 ID、状态值、节点名、日志或程序表达。
- 四份精确测试、Task 3.1 三套回归、全库、Ruff、strict mypy、schema、包校验和差异检查均通过；独立新鲜上下文复核 P0/P1=0 后才接受。

## Risk Boundaries

- 只修改 Task 3.2 允许的模块、schema、四份测试及必要导出/包清单；不写生产路径。
- The delegated agent is not final authority; Codex owns verification and acceptance.
- 不以测试数量或能生成 Markdown 代替科学合同与真实用户体验验收。

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, or malformed probe output must be recorded and followed by one real route attempt. Only a missing executable or explicit invalid/retired/unlisted model may stop before that attempt.

## Loop Log

- 2026-08-12 18:20:36: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- 2026-08-12 18:21: Task 3.2 初版在原 Pi session `019ff262-8ff4-7000-8709-4589a92be55c` 经显式模型切换后完成，精确套件 56 passed；Codex 审阅发现真实 GateSpec/科学质控绑定与中文用户说明仍有假绿风险，暂不接受。
- 2026-08-12 20:10: 修复后首轮隔离会商仍发现路线摘要、空宇宙锚点与路线最终类别三类可复现 P1；Task 3.2 保持未接受。
- 2026-08-12 20:35: 原实现会话完成第六轮窄修复；主会场复测 98/143/429，全部关键攻击失败关闭。
- 2026-08-12 20:48: Pi/OpenCode Go 与 Cursor Grok 原验收会话修复后均为 PASS；Codex 接受 Task 3.2，下一项 Task 3.3。恢复锚点见 `context/ci_phase3_task32_acceptance_2026-08-12.md`。
