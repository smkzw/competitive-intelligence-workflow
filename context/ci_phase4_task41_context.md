# Task Context: ci_phase4_task41

Created: 2026-08-13 22:49:33
Objective: 实现并验收 Phase 4 Task 4.1 共用 ReportViewModel、coverage_set 与页面注册表合同
Task type: `finite_code_task`
Risk: `high`
Selected agent route: `opencode-go` / `deepseek-v4-flash` / `max`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §15.3–15.7、§16.1、附录 C。
- `../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` Task 4.1 与 Phase 4 出口。
- `docs/architecture/page-catalogs/{A,B,C}.yaml`、`filter-contracts/*.yaml`、`format-contracts/*.yaml` 是 Phase 0 已冻结机器合同，不重复发明页面或格式口径。
- Phase 3 accepted commits `8d50e13` / `1a8a2c2`；只消费锁定快照身份，不放松科学质控或无草稿不变量。

## Scope

- In scope: `reports/common/{coverage,view_state,page_registry,chart_specs}.py`、两份 coverage Schema、两个计划测试文件和必要的 `__init__.py`/包清单条目。
- In scope: 稳定 row ID、规范覆盖项、格式投影/例外/差异、页面静态与动态责任、一个模块的图表和完整表共享同一 filtered row set。
- Out of scope: 物理 HTML、CSS/JS、浏览器视觉、A/B/C 专属分析与页面、PDF/PPT、外部研究、安全测试、数据库迁移和 Phase 3 科学数据改写。

## Success Criteria

- `uv run pytest tests/unit/reports/test_view_model.py tests/contract/test_coverage_set.py -q` 全绿；每个关键不变量有负例，不以“文件存在”通过。
- coverage_set 与 projection 绑定同一项目/报告/版本/snapshot/claim snapshot；投影不得引入规范集合外项目，未覆盖差异必须由版本化结构化例外逐项解释。
- stable row ID 由事实身份字段确定，排序、筛选、中文标签或格式变化不改变；重复 ID/缺身份/跨快照混用失败关闭。
- 页面注册表逐项读取冻结 A/B/C page catalog，中文用户标签非空，静态责任与动态产品/试验路由类型分开。
- `ChartTableModule`/等价模型只接受一个 filtered row set，并确定性导出完全相同 row ID 集合给图和表；调用者不能分别提供两套行。
- Ruff、strict mypy、Schema validation、package verify、diff check、全量 pytest 通过；由独立新上下文验证者攻击 P0/P1。

## Risk Boundaries

- 只写上述 Task 4.1 文件；保留用户和已接受 Phase 3 改动，不改批准规格、计划和冻结页面/格式合同。
- 所有用户可见标签使用中文原生临床试验语境；内部字段名可以英文，但不得在后续报告中直接泄漏。
- 委派执行者不拥有验收权；Codex和独立验证者负责最终接受。

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, malformed output, or a stale/incomplete catalog must be recorded and followed by one real route attempt. Explicit user-selected routes are not blocked merely because the catalog does not list them; only a missing executable or native transport boundary may stop before that attempt.

## Loop Log

- 2026-08-13 22:49:33: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- 2026-08-13 22:53–23:33：Pi/OpenCode Go `deepseek-v4-flash:max` 会话 `019ffb9d-3ca6-7000-a8bd-65943cb98a11` 完成初始实现与首轮主代理纠偏；未启用 fallback。
- 2026-08-13 23:36：隔离 Luna CLI 兼容会话 `019ffbc4-a816-7f01-9b49-af1d4af6452d` 首轮发现 4 个 P1：单行页面责任绕过、公开任意目录加载、行集摘要未覆盖完整行、投影例外身份可篡改。
- 2026-08-13 23:48–2026-08-14 00:05：原 Pi 会话按 RED→GREEN 修复上述 4 项；Luna 同会话复审再发现生产加载仍经过测试辅助路径，原 Pi 会话继续拆分生产冻结加载器与测试目录辅助器。
- 2026-08-14 00:09：Luna 同会话最终裁决 `PASS; P0=0; P1=0; P2=0`。
- 2026-08-14 00:12：Codex 全量回归 `536 passed`；Ruff、strict mypy、package verify、diff check 均通过。隔离 wheel 由 uv 安装成功并确认 A/B/C 页面数 `11/21/12` 及两份 coverage schema 存在。系统旧 pip 因索引仅见 `jsonschema<=4.25.1` 无法解析锁定的 `4.26.0`，已区分为安装器/索引技术差异，并由项目标准 uv 路径复核通过。
- 2026-08-14 00:14：实现提交 `f44c06a feat: define canonical report view and coverage contracts`；Task 4.1 accepted，下一步 Task 4.2。
