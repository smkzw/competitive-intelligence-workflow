# Task Context: ci_phase2_task24_foreign_connectors

Created: 2026-08-11 23:30:28
Objective: 独立验收 Task 2.4 境外登记、PubMed、监管资料和 FDA 指南连接器
Task type: `finite_code_task`
Risk: `medium`
Selected agent route: `opencode-go` / `deepseek-v4-flash` / `max`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` 的来源、登记、论文、监管和指南合同。
- `docs/decisions/0006-phase-2-universe-and-source-boundaries.md` 与 `0007-foreign-registry-publication-regulatory-connectors.md`。
- `.trellis/tasks/08-11-phase-2-universe-source-truth/{prd,design,implement}.md`。
- `src/ci_workflow/sources/connectors/{clinicaltrials_gov,pubmed,regulators}.py`。
- `schemas/guideline-basis.schema.json`、`package-manifest.json`。
- `tests/integration/sources/{test_ctgov,test_pubmed_cross_reference,test_regulators}.py`。
- `docs/acceptance/runs/task-2.4/{red,green}.txt` 与当前工作树；不采信构建者自评。

## Scope

- In scope: 只读验收 FG01–FG07 的登记分页/版本/字段定位、NCT—PMID 关系、论文角色、关键字段覆盖、监管文件声明域、FDA 指南生命周期，以及安装包闭合。
- Out of scope: 禁止修改文件；不提前验收 Task 2.5 中国连接器、Task 2.6–2.7 抽取/事实链、A/B/C 报告和视觉产物；不扩大安全测试。

## Success Criteria

- 独立重跑 7 项组合、166 项全库、Ruff、strict mypy、包校验和差异检查。
- 攻击 NCT 大小写/分页令牌、平台每日版本冒充科学版本、原文可变、字段定位丢失、嵌套 PMID 混入、试验方案/事后/综述冒充主要报告、论文替代登记方案字段、补充材料强制下载、监管声明越域、草案/撤回/已替代指南驱动当前默认、替代关系悬空或单向。
- 仅当机械检查真实通过且 P0=0、P1=0 时建议接受。

## Risk Boundaries

- 本轮只读，runner 只持久化其报告与原始流。
- 不以临时实时网络成功替代离线合同，也不把网络故障解释为科学“未公开”。
- The delegated agent is not final authority; Codex owns verification and acceptance.

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, or malformed probe output must be recorded and followed by one real route attempt. Only a missing executable or explicit invalid/retired/unlisted model may stop before that attempt.

## Loop Log

- 2026-08-11 23:30:28: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- 2026-08-11 23:34–23:42: 夜间 OpenCode Go session 完成首轮只读验收；健康目录检查超时后真实路线成功，无 fallback。
- 2026-08-11 23:42–23:46: Codex 修复首轮 3 个 P2 与缺引文过度阻断；同 session 第二轮复核 PASS，P0/P1/P2=0。
