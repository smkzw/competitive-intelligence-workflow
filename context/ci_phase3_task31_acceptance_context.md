# Task Context: ci_phase3_task31_acceptance

Created: 2026-08-12 04:20:28
Objective: 独立验收 Task 3.1 版本化 A/B/C 证据规则、报告特异评估与只收紧覆盖，重点识别会导致关键证据不足仍通过的科学 false-green
Task type: `high_risk_contradiction_review`
Risk: `high`
Selected agent route: `codex` / `gpt-5.6-luna` / `max`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- `2026-08-10-competitive-intelligence-multiskill-workflow-design.md` 中与 Task 3.1 相关的 §8.7、§11.4、§12.2、§13.2、§13.6、§13.7、§14.2。
- `2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` 的 Task 3.1 与 Phase 3 验收要求。
- `docs/decisions/0011-phase-3-evidence-gates-and-recovery.md`。
- `.trellis/tasks/08-12-phase-3-evidence-gates-recovery/{prd,design,implement}.md`。
- 当前工作树的 `policies/gates/`、`schemas/gate-*.schema.json`、`src/ci_workflow/gates/`、三个 Task 3.1 测试文件及包清单。
- 三位实现者与执行经理的 `runs/execution/ci_phase3_task31_implementation/` 报告只作为待核验证据，不作为通过依据。

## Scope

- In scope: 只读、全新上下文验收 Task 3.1；攻击关键证据不足仍通过、对象/作用域错配、缺失转零、A 触发降级、B 多试验/多臂/单臂错配、C 登记充分边界、项目覆盖放松、旧结果被覆盖、受影响报告漏算、中文用户说明泄露内部状态。
- 特别验证 B 核心疗效“治疗组与适用对照组两组数值”是否被机器合同真正证明，而不只是保存两个组名；验证 flat universe IDs 是否允许跨试验/跨比较拼接证据。
- In scope: 运行现有测试、只读探针和临时目录中的一次性验证；不得修改项目文件。
- Out of scope: Task 3.2–3.7、门户/四格式、真实医学结论、网络研究、安全测试、任何实现修复。

## Success Criteria

- 完整阅读指定合同与实现，不采信 worker/manager 自报。
- 至少执行 Task 3.1 精确套件，并用最小反例攻击上列 false-green。
- 按 P0/P1/P2 输出每个缺陷的文件与行号、可复现输入/命令、实际与期望结果、为何影响“关键证据不足不可生成草稿”、最小修复边界和建议 exact test 名称。
- P0/P1 均为 0 时才可给 PASS；否则给 FAIL。不得以测试全绿代替科学合同验收。

## Risk Boundaries

- 全程只读项目文件；不得写入源代码、测试、Trellis 状态或验收结论文件。
- The delegated agent is not final authority; Codex owns verification and acceptance.

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, or malformed probe output must be recorded and followed by one real route attempt. Only a missing executable or explicit invalid/retired/unlisted model may stop before that attempt.

## Loop Log

- 2026-08-12 04:20:28: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- 2026-08-12 04:22:00: 本 Codex App 会话此前已对 `gpt-5.6-luna/max` 做过显式原生创建探测并被后端拒绝；依全局同会话规则不重复探测，使用标记为 `cli_compatibility_fallback` 的 Codex CLI 路径，不替换为其他 Codex 模型，也不经 Hermes。
