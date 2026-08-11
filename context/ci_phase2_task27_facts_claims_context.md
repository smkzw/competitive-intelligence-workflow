# Task Context: ci_phase2_task27_facts_claims

Created: 2026-08-12 00:55:50
Objective: 独立验收 Task 2.7 来源片段到版本化事实、冲突集合与可追溯声明链
Task type: `finite_code_task`
Risk: `medium`
Selected agent route: `opencode-go` / `deepseek-v4-flash` / `max`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` 的科学真源、事实、冲突与声明合同。
- `docs/decisions/0010-versioned-facts-conflicts-and-claims.md`。
- `.trellis/tasks/08-11-phase-2-universe-source-truth/{prd,design,implement}.md`。
- `src/ci_workflow/domain/{evidence,facts,claims}.py`。
- `src/ci_workflow/capabilities/{extraction_normalization,resolution}.py`。
- `schemas/{fact,claim}.schema.json` 与 `package-manifest.json`。
- `tests/integration/{test_source_to_claim_chain,test_conflicts_preserved}.py`。
- `docs/acceptance/runs/task-2.7/{red,green}.txt` 与当前工作树；不采信构建者自评。

## Scope

- In scope: 只读验收 ER01–ER04 的来源片段重开、原子事实字段全集、稳定版本身份、可逆规范化、字段级冲突集合，以及直接证据/确定性计算/AI 综合判断三类声明。
- Out of scope: 禁止修改文件；不提前验收 Phase 3 GateSpec、报告生成、真实网页/PDF 抽取质量和用户界面；不扩大安全测试。

## Success Criteria

- 独立重跑 4 项组合、182 项全库、Ruff、strict mypy、包校验和差异检查。
- 攻击未重开片段、片段原文/摘要/来源版本错配、次日重跑身份漂移、规范化覆写原值或不可逆、冲突先到先得、未接受事实进入声明、计算文字与结果不符、AI 综合判断未标识、状态语义混写及 schema/包清单漂移。
- 仅当机械检查真实通过且 P0=0、P1=0 时建议接受。

## Risk Boundaries

- 本轮只读，runner 只持久化其报告与原始流。
- 不把合成事实测试冒充真实临床数据抽取质量；但任何不能回到绑定原文、冲突被静默压平或声明无法回溯事实的路径都不得建议放行。
- The delegated agent is not final authority; Codex owns verification and acceptance.

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, or malformed probe output must be recorded and followed by one real route attempt. Only a missing executable or explicit invalid/retired/unlisted model may stop before that attempt.

## Loop Log

- 2026-08-12 00:55:50: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- 2026-08-12 00:56–01:03: 北京夜间 OpenCode Go session 完成首轮只读验收；健康目录检查超时后真实路线成功，无 fallback，报告 6 个 P2。
- 2026-08-12 01:04–01:12: Codex 将 schema 漂移、规范化幂等、计算文字矛盾、事实身份、声明链接和未报告状态全部转成反例并修复；原 session 复核发现 3 个残余 P2。
- 2026-08-12 01:13–01:18: Codex 修复零值类型、全角数字和中文下降幅度表述；原 session 最终复核 PASS，P0/P1/P2=0。
- 最终 4 项任务测试、182 项全库、Ruff、strict mypy、包校验、差异检查和真实 wheel 内容通过；Phase 2 真实来源到声明 fixture 仍留给正式阶段退出门。
