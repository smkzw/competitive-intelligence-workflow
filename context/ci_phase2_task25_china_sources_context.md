# Task Context: ci_phase2_task25_china_sources

Created: 2026-08-11 23:56:13
Objective: 独立验收 Task 2.5 中国登记、监管、企业与指定公众号来源路由
Task type: `finite_code_task`
Risk: `medium`
Selected agent route: `opencode-go` / `deepseek-v4-flash` / `max`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` 的国内来源、来源角色、指南与证据版本合同。
- `docs/decisions/0006-phase-2-universe-and-source-boundaries.md` 与 `0008-china-registry-industry-source-boundaries.md`。
- `policies/sources/source-policy-v1.yaml` 与 `schemas/guideline-basis.schema.json`。
- `.trellis/tasks/08-11-phase-2-universe-source-truth/{prd,design,implement}.md`。
- `src/ci_workflow/sources/connectors/{china_registries,company,authoritative_wechat,regulators}.py` 与 `src/ci_workflow/sources/policy.py`。
- `tests/integration/sources/{test_china_routes,test_company_sources,test_authoritative_wechat,test_regulators}.py`。
- `docs/acceptance/runs/task-2.5/{red,green}.txt` 与当前工作树；不采信构建者自评。

## Scope

- In scope: 只读验收 CN01–CN07：中国监管事件、国内试验登记版本与字段定位、丁香园用药助手和官方页面角色、企业/topline/会议披露成熟度、五个指定公众号的批准声明范围及 CDE 指南生命周期。
- Out of scope: 禁止修改文件；不提前验收 Task 2.6–2.7 文档摄取/事实链、真实多路线编排、A/B/C 报告和视觉产物；不扩大安全测试。

## Success Criteria

- 独立重跑 7 项组合、173 项全库、Ruff、strict mypy、包校验和差异检查。
- 对抗验证 CDE 受理/审评不会冒充 NMPA 批准；中国登记版本和 locator 不丢失；DXY 不冒充官方；企业、topline、会议、管线不冒充登记或论文；五个公众号只在批准四域直接支持且不能冒充同行评议；CDE 草案/替代/撤回不会驱动默认。
- 仅当机械检查真实通过且 P0=0、P1=0 时建议接受。

## Risk Boundaries

- 本轮只读，runner 只持久化其报告与原始流。
- 不以来源页面存在替代字段语义检查，也不把网络/技术失败解释成科学“未公开”。
- The delegated agent is not final authority; Codex owns verification and acceptance.

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, or malformed probe output must be recorded and followed by one real route attempt. Only a missing executable or explicit invalid/retired/unlisted model may stop before that attempt.

## Loop Log

- 2026-08-11 23:56:13: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- 2026-08-11 23:58–2026-08-12 00:08: 北京夜间 OpenCode Go session 完成首轮只读验收；模型目录健康检查超时后真实路线成功，无 fallback。
- 2026-08-12 00:09–00:15: Codex 将首轮 2 个 P2 转为反例测试并修复；原 session 第二轮复核 PASS，P0/P1/P2=0。
- 本任务只接受 CN01–CN07 连接器合同；Task 2.6–2.7 及真实路线编排仍待独立验收。
