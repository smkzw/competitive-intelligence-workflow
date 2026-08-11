# Task Context: ci_phase2_task26_ingestion_locators

Created: 2026-08-12 00:23:21
Objective: 独立验收 Task 2.6 异构临床来源分类、片段化与精确可重开定位
Task type: `finite_code_task`
Risk: `medium`
Selected agent route: `opencode-go` / `deepseek-v4-flash` / `max`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` 的科学真源、证据片段与用户文件合同。
- `docs/decisions/0009-version-bound-clinical-source-locators.md`。
- `.trellis/tasks/08-11-phase-2-universe-source-truth/{prd,design,implement}.md`。
- `src/ci_workflow/ingestion/{classifier,fragmenter,locators}.py` 与 `src/ci_workflow/domain/evidence.py`。
- `schemas/{source-version,evidence-fragment,guideline-basis}.schema.json`。
- `tests/unit/test_source_classifier.py`、`tests/integration/test_fragment_locators.py` 与 `tests/integration/test_source_version_chain.py`。
- `docs/acceptance/runs/task-2.6/{red,green}.txt` 与当前工作树；不采信构建者自评。

## Scope

- In scope: 只读验收 IF01–IF05 的七类文档角色、未知分类、登记/网页/PDF 精确可重开定位、跨版本拒绝、用户原文件名/自动规范名、内容摘要及父子文档身份。
- Out of scope: 禁止修改文件；不提前验收 Task 2.7 事实/声明链、真实网页/PDF 解析器质量、用户下载恢复控制图和报告层；不扩大安全测试。

## Success Criteria

- 独立重跑 5 项组合、178 项全库、Ruff、strict mypy、包校验和差异检查。
- 攻击未知文档误分类、孤立 supplement、外部结构篡改、重复网页标题错定位、PDF 同页/同表数值错引、跨版本重开、用户文件原名丢失、摘要/父文档/规范名漂移及 schema 不同步。
- 仅当机械检查真实通过且 P0=0、P1=0 时建议接受。

## Risk Boundaries

- 本轮只读，runner 只持久化其报告与原始流。
- 不把结构快照测试冒充真实 PDF/网页抽取质量；但任何不能精确重开的定位器都不得建议放行。
- The delegated agent is not final authority; Codex owns verification and acceptance.

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, or malformed probe output must be recorded and followed by one real route attempt. Only a missing executable or explicit invalid/retired/unlisted model may stop before that attempt.

## Loop Log

- 2026-08-12 00:23:21: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- 2026-08-12 00:24–00:34: 北京夜间 OpenCode Go session 完成首轮只读验收；健康目录检查超时后真实路线成功，无 fallback。
- 2026-08-12 00:35–00:41: Codex 修复 locator 坐标未全部进入身份、PDF 同页重复表名迟拒；原 session 复核发现 PDF 顶层表名/列名仍未进入身份。
- 2026-08-12 00:42–00:45: Codex 修复最后一个读取字段/承诺字段不一致；原 session 最终复核 PASS，P0/P1/P2=0。
- 本任务只接受结构分类与定位合同；Task 2.7 的“重开值等于片段原文”事实入口仍待独立验收。
