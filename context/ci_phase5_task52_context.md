# Task Context: ci_phase5_task52

Created: 2026-08-14 17:14:07
Objective: 实现 A 类竞争格局、产品档案、临床组合、监管、企业交易、专利及历史边缘八类完整视图模型
Task type: `competitive_intelligence`
Risk: `high`
Selected agent route: `codex` / `codex-main` / `high`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §12.1–12.3。
- `../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` Task 5.2 / AV01–AV08。
- Task 5.1 已接受的 `src/ci_workflow/reports/a/{contracts,analysis}.py` 与提交 `8b02185`。
- Phase 3 已锁定的 `ApplicableUniverseSnapshot`、`GateEvidenceBinding` 和版本化事实合同。
- Phase 4 已接受的页面责任目录 `src/ci_workflow/reports/common/page-catalogs/A.yaml`。

## Scope

- In scope：只读视图模型；竞争格局、产品总览、逐产品档案、临床开发组合、中国/全球监管、企业关系与交易、专利/监管独占、历史与边缘观察。
- Allowed outputs：`src/ci_workflow/reports/a/pages.py`、`src/ci_workflow/reports/a/__init__.py`、`tests/unit/reports/a/test_*.py`、本任务记录和 Phase 5 Trellis 文件。
- Out of scope：模板、HTML/PDF/PPT、图表、真实来源抓取、B/C 报告、安全专项测试。

## Success Criteria

- 八个计划节点 AV01–AV08 均先证伪后通过；整套 `tests/unit/reports/a` 通过。
- 视图只消费当前锁定快照和已接受 A 合同，不能接收自由的产品列表后补写快照身份。
- 所有合格创新治疗完整保留、顺序稳定、无 Top-N；每个产品有稳定路由且档案责任齐全。
- 产品—试验—地区—阶段—状态关系闭合；中国和境外监管事件分轨且版本可追溯。
- 原研/开发/许可/合作/并购/地域权益与交易条款不混为一个字段；未合作可显式无记录而不失败。
- 专利族、法域、保护范围、期限与监管独占分开；不把未知或推断写成法律事实。
- 暂停、终止、撤回、放弃及邻近机制观察层始终可见，不因当前开发状态被过滤。
- A 专项、共享证据交叉、全仓回归、Ruff、strict mypy和独立审查通过后才接受。

## Risk Boundaries

- 不允许视图层补造证据、重算竞品纳排、静默合并不同法域或将缺失变成零。
- 用户可见标签使用中国临床开发与竞争情报环境的中文，不暴露工程状态或提示词。
- 本任务是数据视图合同，不生成报告产物；真实用户视觉试用留在 Task 5.4/5.5。
- Do not write to production paths until Codex review gate passes and writable paths are explicit.
- The delegated agent is not final authority; Codex owns verification and acceptance.

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, malformed output, or a stale/incomplete catalog must be recorded and followed by one real route attempt. Explicit user-selected routes are not blocked merely because the catalog does not list them; only a missing executable or native transport boundary may stop before that attempt.

## Loop Log

- 2026-08-14 17:14:07: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- 2026-08-14 17:15: 重读设计 §12.3 与计划 AV01–AV08；现有架构与已批准方案一致，本任务不引入外部运行依赖，新的外部选型扫描不会改变视图合同，故沿用已接受的 Pydantic 不可变模型路线。
- 2026-08-14 22:43: AV01–AV08 完成。执行者五轮同会话修复关闭 no-draft、锁定证据内容摘要、外部权威项目合同、结果字段/实体/来源闭合、扩展 DTO 重验证、事实唯一消费和中文显示问题；未进入模板或产物层。
- 2026-08-14 22:43: Codex 实测 `tests/unit/reports/a` 219 passed；A 联合 310 passed；共享 gate/no-draft/A 527 passed；非 browser/acceptance 全库 1047 passed；Ruff 与 strict mypy（89 个源文件）通过。
- 2026-08-14 22:43: 独立 Luna 在同一 `gpt-5.6-luna:max` 会话进行五轮攻击，最终 `PASS`，P0/P1/P2 均为 0。原生能力探测此前明确不支持，使用 AGENTS 规定的 Codex CLI 兼容续跑；未替换模型、未新建会话。
- 2026-08-14 22:43: 用户要求完成当前步骤后无损暂停。当前安全恢复点为 Task 5.2 已接受、Task 5.3 尚未开始；下一动作是读取最新 AGENTS/设计/计划/Trellis 后初始化 5.3 疗效、安全热图和疗效—安全气泡矩阵，不重做 5.2。
