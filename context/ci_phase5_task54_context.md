# Task Context: ci_phase5_task54

Created: 2026-08-18 02:33:03
Objective: 按已批准设计与康哲站点规范实现 A 类完整多页面门户、真实 fixture 与双浏览器验收
Task type: `competitive_intelligence`
Risk: `high`
Selected agent route: `codex` / `codex-main` / `high`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md`。
- `../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` Task 5.4。
- `contracts/kangzhe/design_specs/{ROUTER,core,project_profile,track_site}.md`；本项目副本是唯一设计权威。
- `.trellis/tasks/08-14-phase-5-report-a/{prd,design,implement}.md`。
- Task 5.1–5.3 已验收的 A 数据合同和 `context/ci_phase5_task53_context.md`。

## Scope

- In scope: `a-complete` 案例、A 专用模板/渲染适配、12+P 物理页面、当前运行快照与清单、双浏览器真实验收和真实医学经理视觉试用。
- Out of scope: B/C、PDF、HTML-PPT、PPTX、真实外网特应性皮炎研究（Task 5.5）、安全测试、旧工程修改或删除。

## Success Criteria

- `fixture run` 真实产出 `reports/A/v-fixture-001/html/`，且站点、报告快照、产物清单、案例摘要和当前运行标识一致。
- 12 个静态页面和每个产品详情页全部存在、互通；首页四类摘要齐备，疗效/安全性/矩阵为独立页面。
- 图在前、完整表在后；治疗/对照并列；安全性热图与气泡多维设置可用；筛选在图表、表格和 URL 间一致。
- 双浏览器三视口全部路由无断链、控制台错误、水平溢出或用户可见工程标签。

## Risk Boundaries

- 只写当前新仓和项目内 `.artifacts/a-complete`；旧工程绝不修改或删除。
- 不做安全性扩项；不以空壳、测试退出码或截图存在冒充完成。
- 生成者不写 accepted；Codex 和隔离视觉审查者拥有验收结论。

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, malformed output, or a stale/incomplete catalog must be recorded and followed by one real route attempt. Explicit user-selected routes are not blocked merely because the catalog does not list them; only a missing executable or native transport boundary may stop before that attempt.

## Loop Log

- 2026-08-18 02:33:03: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- 2026-08-18 02:40:00: 重新读取全局 AGENTS、Trellis、项目 design spec 与 Task 5.4 精确节点；决定复用 Phase 4 纯静态门户内核，不引入新依赖。
- 2026-08-18: 完成 `a-complete` 数据案例、12 个专题页和 4 个产品详情页；首页、疗效、安全性与矩阵均为图在前、表在后，筛选与网址状态同步。
- 2026-08-18: Minimax 会话 `01a0112d-c807-7000-a5b2-e7a6a1ecd974` 真实浏览并操作页面；Grok Build 会话 `6cf69d62-7f2e-4c23-bb89-732a6b57246c` 在两次工具取消后沿原会话恢复，以原分辨率截图完成批判性复核。两者提出的历史状态语义、矩阵尺度、安全色阶、数据依据、产品范围和用户可见占位语均已修复；最后两项非阻断建议（产品页依据按钮、历史筛选中文）也已纳入。
- 2026-08-18: 删除未实际派发的默认 K3 占位记录；保留两条用户指定路线的运行与恢复证据，不把技术取消当成视觉验收。
- 2026-08-18: 最终重新生成 `run_af81f5bfd14df47171cddc32`。案例摘要 `e21d4413…`，输入摘要 `295a6dff…`，站点摘要 `8bb3838c…`，清单摘要 `51d117ca…`。
- 2026-08-18: `verify_portal.py` 对 16 路由执行 Chromium/WebKit × 1280×800、1440×900、1920×1080 验收，96 张截图及 2 份交互 trace 全部通过。Codex 复看首页、产品详情、矩阵和历史页原图。
- 2026-08-18: 门户联合 86 项、Task 5.4/A 类定向 183 项、全工程 1425 项测试全部通过；Ruff、strict mypy、`git diff --check` 通过。

## Pause Checkpoint

- 已完成：Task 5.4 A 类完整多页面门户及验收。
- 尚未开始：Task 5.5 真实适应症外网研究与刷新演练。
- 恢复入口：先读取本文件、`.trellis/tasks/08-14-phase-5-report-a/implement.md` 和 `docs/acceptance/runs/ci_phase5_task54/verdict.md`；不得重做 Task 5.4，也不得修改或删除旧工程。
- 下一安全动作：按实施计划进入 Task 5.5，先核对外部资料采集与数据截止日合同，再发起真实研究。
