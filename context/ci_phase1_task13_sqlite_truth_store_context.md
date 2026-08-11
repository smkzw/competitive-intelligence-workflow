# Task Context: ci_phase1_task13_sqlite_truth_store

Created: 2026-08-11 17:37:15
Objective: 实现六阶段 SQLite 迁移、科学真源核心表、状态族隔离与追加式版本记录
Task type: `finite_code_task`
Risk: `medium`
Selected agent route: `cms-smk` / `cms-model` / `high`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §§8.1–8.6。
- `/Users/smkzw/Documents/AI Products/.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` Task 1.3。
- `docs/decisions/0004-phase-1-contract-boundaries.md`。
- Task 1.1 已接受的九组状态与项目合同；Task 1.2 已接受的可移动项目和相对路径。

## Scope

- In scope: 0001–0006 顺序迁移、迁移摘要、科学真源核心表、状态族 CHECK 隔离、追加式版本/审计表、项目合同同步写入 SQLite。
- Out of scope: Task 1.4 内容寻址文件库和证据合同、Task 1.5 事件/检查点/快照、检索、分析和渲染。

## Success Criteria

- 六个迁移从 0001 连续执行且可幂等重放；已应用文件的名称/摘要漂移失败关闭。
- 实施计划指定的核心表齐全，`foreign_keys=1`、`integrity_check=ok`、`user_version=6`。
- 项目、事实披露/审查、报告证据、格式、下载、修订状态族不得串写。
- 项目合同、来源、证据片段、事实、声明、快照等不得原地更改/删除，修正只追加新版本。
- 精确 6 项、全库 108 项、Ruff、strict mypy、包校验和独立可执行审查通过。

## Risk Boundaries

- 只写当前新架构仓库与 pytest 临时项目；旧工程只读。
- 不做安全测试，不引入框架私有检查点或报告功能。
- The delegated agent is not final authority; Codex owns verification and acceptance.

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, or malformed probe output must be recorded and followed by one real route attempt. Only a missing executable or explicit invalid/retired/unlisted model may stop before that attempt.

## Loop Log

- 2026-08-11 17:37:15: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- 2026-08-11 17:41:00: Codex 完成 RED/GREEN；精确 6 项、全库 108 项及静态检查全绿，等待独立审查。
- 2026-08-11 17:43:00: 用户要求无损暂停。不强杀只读审查会话，不继续实施；详细恢复锚点见 `context/ci_workflow_pause_20260811_task13.md`。
