# Task Context: ci_phase5_task51

Created: 2026-08-14 14:51:26
Objective: 实现 A 类完整竞品范围、按成熟度递增的关键字段合同与 result-bearing 证据阻断，确保不删药、不做 Top-N
Task type: `competitive_intelligence`
Risk: `high`
Selected agent route: `codex` / `codex-main` / `high`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §2、§3.2、§12.1–12.2。
- `../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` Task 5.1。
- `policies/ontology/innovation-therapy-v1.yaml` 与 Phase 2 已接受的创新治疗纳排结果。
- Phase 3 已接受的证据披露状态、GateSpec/阻断语义与不可变快照合同。
- 当前仓库 `1816e67`；不读取生产路径。


## Scope

- In scope：A 类项目规范身份、创新本体资格、机制/靶点、模态、企业、适应症关系、中国/境外阶段与状态；临床/申报上市终止/有数值结果成熟度递增字段；`result_bearing` 确定性触发；疗效与 TEAE/SAE 最低记录；全宇宙保留与阻断。
- Allowed outputs：`src/ci_workflow/reports/a/contracts.py`、`src/ci_workflow/reports/a/analysis.py`、必要的包 `__init__.py`、`tests/reports/a/test_maturity_gate.py`、`test_result_bearing_gate.py`、`test_no_top_n.py`、本任务记录与 Phase 5 Trellis 条目。
- Out of scope：Task 5.2 页面视图、Task 5.3 图表、HTML 模板/渲染、真实来源抓取、PDF/PPT、安全测试。


## Success Criteria

- 全部传入且已通过创新本体资格的项目保持稳定身份与顺序，不按成熟度、结果好坏、字段缺口或固定数量截断。
- 所有项目、临床项目、申报/上市/终止项目、`result_bearing` 项目逐层增加必需字段；不适用显式表达，不能用空值冒充。
- 官方登记结果、监管材料、主要试验报告、会议/公司数值披露及指定权威二手来源出现可归属数值即触发 `result_bearing`；只有 Results posted 标志但值不完整也进入恢复层。
- `result_bearing` 项目缺适格锚定试验、可解释核心疗效或 TEAE/SAE 数值摘要时，整个 A 报告失败并逐产品说明，不得删除该药继续。
- 疗效/安全记录保留定义、方向/单位、时间点/窗口、分析人群、治疗/对照组、分母和准确披露状态；0、未公开、阈值与空白不同。
- 三个计划测试文件、全库、Ruff 与 strict mypy 通过；独立审查确认没有 Top-N 和成熟项目降级假绿。


## Risk Boundaries

- 不生成报告或占位物，只实现与测试不可变业务合同。
- 不在本任务重新解释创新药政策；消费 Phase 2 已接受资格，纯传统药不得进入。
- 不把缺失成熟字段变成删除产品、降级为无结果、空字符串或默认零。
- 用户可见原因使用中文临床开发语言，不暴露 prompt/log/后端标签。
- 不做安全专项测试。

- Do not write to production paths until Codex review gate passes and writable paths are explicit.
- The delegated agent is not final authority; Codex owns verification and acceptance.

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, malformed output, or a stale/incomplete catalog must be recorded and followed by one real route attempt. Explicit user-selected routes are not blocked merely because the catalog does not list them; only a missing executable or native transport boundary may stop before that attempt.

## Loop Log

- 2026-08-14 14:51:26: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- 2026-08-14 14:52: 读取最新设计 §12.2、实施计划 Task 5.1、现有实体/状态/创新治疗政策；确认沿用既定架构与依赖，不需要重新开展外部选型扫描。
- 2026-08-14 15:09–15:36: 三个顺序 worker 在同一共享文件边界完成成熟度字段、结果承载触发和无 Top-N 整批分析；未使用备用路线。
- 2026-08-14 15:51: Luna 隔离审查首次否决弱布尔、无真实数值、跨试验拼接等科学假绿；原生子代理能力明确拒绝后，按全局 AGENTS 使用 `gpt-5.6-luna:max` CLI 兼容路线，session `019fff35-ffa5-7553-b4f8-24f4af3f2834`。
- 2026-08-14 16:18–16:53: 在原 worker/session 与原 Luna session 内完成两轮定向修复和复验；最终 91 项 A 专项测试与 30 个独立反例通过，Luna 结论 PASS，P0/P1/P2=0。
- 2026-08-14 17:00: 全仓 `1110 passed in 372.03s`；Ruff 与 strict mypy（87 个生产源文件）通过。Task 5.1 接受，下一步 Task 5.2。
- 2026-08-14 续跑恢复：清除共享证据模型的无关格式化差异，仅保留严格数值类型变更；当前工作树重新通过 A 专项 91 项、共享证据交叉回归 308 项及全仓 `1110 passed in 366.45s`。
