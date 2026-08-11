# Task Context: ci_phase2_task23_sources

Created: 2026-08-11 23:02:15
Objective: 独立验收 Task 2.3 来源权威、恢复穷尽与历史截止日合同
Task type: `finite_code_task`
Risk: `medium`
Selected agent route: `opencode-go` / `deepseek-v4-flash` / `max`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §10.3–10.5、§11.1–11.4 与历史截止日合同。
- `docs/decisions/0006-phase-2-universe-and-source-boundaries.md`。
- `.trellis/tasks/08-11-phase-2-universe-source-truth/{prd,design,implement}.md`。
- `policies/sources/source-policy-v1.yaml`、`policies/recovery/source-strategies-v1.yaml`。
- `schemas/{source-receipt,source-eligibility,evidence-gap,source-version}.schema.json`。
- `src/ci_workflow/domain/evidence.py` 与 `src/ci_workflow/sources/{policy,planner,receipts,retries}.py`。
- `fixtures/synthetic/historical-cutoff/`。
- `tests/unit/test_source_policy.py`、`tests/contract/test_evidence_audit_contracts.py`、`tests/integration/test_route_recovery.py`、`tests/integration/test_historical_cutoff.py`。
- `docs/acceptance/runs/task-2.3/{red,green}.txt` 与当前工作树；不采信构建者自评。

## Scope

- In scope: 只读验收 SP01–SP11 的来源声明域、尝试/路线/事实状态分离、恢复计数、审计包、历史截止日与安装包闭合。
- Out of scope: 不修改文件；不验收 Task 2.4 连接器或任何 A/B/C 报告、视觉、PDF/PPT；不扩大安全测试。

## Success Criteria

- 独立重跑 18 项组合、159 项全库、Ruff、strict mypy、包校验与差异检查。
- 攻击五个指定中文来源越权、技术故障伪装未公开、重复策略冒充新轮次、少于三次重试/少于两条替代、伪造退避、缺少审计字段或适用性决定、访问阻断使用成功/未找到回执、cutoff 后证据泄漏。
- 仅当 P0=0、P1=0 且机械检查真实通过时建议接受。

## Risk Boundaries

- 本轮只读，禁止编辑项目文件；runner 只持久化报告与原始流。
- Reviewer 不能用已有测试通过替代代码攻击，也不能把内部状态文案当用户可见报告语言验收。
- The delegated agent is not final authority; Codex owns verification and acceptance.

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, or malformed probe output must be recorded and followed by one real route attempt. Only a missing executable or explicit invalid/retired/unlisted model may stop before that attempt.

## Loop Log

- 2026-08-11 23:02:15: Task initialized by `tools/hermes_workflow_guard.py init-task`.
