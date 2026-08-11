# Task Context: ci_phase1_task14_evidence_chain

Created: 2026-08-11 20:32:01
Objective: 实现内容寻址来源版本、审计回执、证据缺口与可定位证据片段合同
Task type: `finite_code_task`
Risk: `medium`
Selected agent route: `cms-smk` / `deepseek-v4-flash` / `max`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §§7、8.1–8.6、10.3。
- `/Users/smkzw/Documents/AI Products/.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` Task 1.4。
- `docs/decisions/0004-phase-1-contract-boundaries.md`。
- Task 1.3 已接受的 0001–0006 迁移及 SQLite 追加式真源；新迁移只能追加，不得修改已接受摘要。

## Scope

- In scope: 项目内内容寻址原文、来源版本四类日期及定位、证据片段原文与 locator、来源回执与证据缺口 JSON/Pydantic 合同、追加式 0007 扩展。
- Out of scope: Task 1.5 事件/检查点/报告快照、来源检索连接器、路线重试策略、分析和渲染。

## Success Criteria

- 相同原文只保存一份，不同内容版本并存；路径始终相对项目目录，读取时复核摘要。
- 来源版本分存 `acquired_at/published_at/effective_at/first_disclosed_at`；时间带偏移，未公开/不适用用类型化状态，不能拿获取时间冒充。
- 同一文档稍后再次下载不改写原始获取与首次披露；内容变化产生新来源版本。
- locator 可回到来源字段、页、表或段落；空原文不能形成证据片段或支持事实。
- 来源回执和证据缺口缺任一 v1.2 必填审计字段均失败关闭；不保存凭据字段；未取得内容时允许摘要为空但必须有错误分类。
- 精确测试、全库回归、Ruff、strict mypy、包校验和独立可执行审查通过。

## Risk Boundaries

- 只写当前新架构仓库与 pytest 临时目录；旧工程只读。
- 不做安全测试扩展，不实现 Task 1.5+。
- 独立审查者只读；Codex 保留最终接受权。

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, or malformed probe output must be recorded and followed by one real route attempt. Only a missing executable or explicit invalid/retired/unlisted model may stop before that attempt.

## Loop Log

- 2026-08-11 20:32:01: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- 2026-08-11 20:35: 首轮精确测试得到 3 个 collection errors，仅因目标模块不存在。
- 2026-08-11 20:46: 实现内容寻址库、证据模型、四份 schema 与 0007 追加迁移；精确 10 项、相关 16 项、全库 118 项、Ruff、strict mypy 和包校验通过，等待独立审查。
