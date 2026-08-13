# Task Context: ci_phase4_task42

Created: 2026-08-14 00:19:21
Objective: 内化最新版康哲站点规范并实现验收 Task 4.2 康哲门户壳层、正式 Logo、导航、搜索与多物理页
Task type: `html_ppt_visual_browser`
Risk: `high`
Selected agent route: `alibaba` / `qwen3.8-max` / `xhigh`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` 与批准计划 Phase 4 Task 4.2。
- 项目冻结设计合同 `contracts/kangzhe/design.md` → `design_specs/{ROUTER,core,project_profile,track_site}.md`；站点轨已于本任务开始时与最新版 `29961f...` 对齐，后续不再同步通用版。
- `docs/architecture/page-catalogs/{A,B,C}.yaml` 与 Task 4.1 `PageRegistry` 是页面责任真源。
- `assets/brand/cms-logo.svg` 是运行时正式 Logo 资产；不得远程加载或文字冒充。

## Scope

- In scope：门户 builder/page shell/global search；项目内 `assets/portal/{portal.css,portal.js}`；至少三个真实互通物理页；浅色 sticky 顶栏、Logo、简洁报告标题、当前页、全局搜索、单一全局页脚、响应式折叠、reduced-motion、file/static 两种运行。
- In scope：使用合成中文临床数据展示壳层结构，并建立 Chromium/WebKit 与 1280/1440/1920 的真实浏览器测试。
- Out of scope：业务图表/完整表（Task 4.4）、分层筛选与 URL 状态（Task 4.3）、证据抽屉（Task 4.5）、A/B/C 完整内容页、PDF/PPT、外部研究、安全测试。

## Success Criteria

- 页面受众文字不出现 A/B/C 报告定义、提示词、检索/证据/技术日志、`gate/signal/accepted/pending` 等后端词。
- 左上正式 Logo 可读；标题、导航、搜索在 1280/1440/1920 不重叠、不串行、不裁切；正文与导航达到字体下限。
- 至少 3 个物理 HTML 文件共享统一 `.site-header/.site-footer`，导航当前态正确、链接无死链；全局搜索可键盘使用并跳转目标页。
- 默认浅底面积与橙黄占比符合合同；橙底文字为深字；`prefers-reduced-motion` 和 1024px 以下折叠可用。
- `file://` 与静态服务器下 Chromium/WebKit 均无 console/page error；真实截图由 Codex 复看，生成者无验收权。
- 任务内测试、相关合同测试、Ruff、strict mypy、package verify、全量 pytest 通过。

## Risk Boundaries

- Do not write to production paths until Codex review gate passes and writable paths are explicit.
- The delegated agent is not final authority; Codex owns verification and acceptance.
- 不得把能打开页面、文件存在、测试退出码 0 当作视觉可用；任何 0 竞品/0 页面/空搜索结果必须深挖数据、生成或路由原因。

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, malformed output, or a stale/incomplete catalog must be recorded and followed by one real route attempt. Explicit user-selected routes are not blocked merely because the catalog does not list them; only a missing executable or native transport boundary may stop before that attempt.

## Loop Log

- 2026-08-14 00:19:21: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- 2026-08-14 00:20: 项目冻结 `track_site.md` 与最新版摘要 `29961f...` 对齐；17 项设计合同测试通过，后续不再同步通用版。
- 2026-08-14 00:22: Pi/Qwen 真实路线因周配额 429 终止；Harness 自动换成未声明 Mimo，执行记录被拒绝，未作为实现或验收依据。随后按声明路线使用 Cursor CLI `auto`，会话 `f0d3d350-90ac-4912-aee7-b06354d944e9` 完成实现与两次同会话视觉补修。
- 2026-08-14 01:20: Codex 真实截图发现三页样例假绿、页面空壳元语言和 21 页导航承载缺口；补充 B 类 21 页/5 组浏览器矩阵，清除占位与技术语言，加入明确分组、下拉提示、正式 Logo、搜索、响应式和键盘路径。
- 2026-08-14 01:47: CodeBuddy CLI `kimi-k2.6`、Pi `cms-router/minimax-m3`、Grok Build `grok-4.6` 均在原会话完成视觉复审并给出 PASS；Grok 前两次在浏览器工具边界取消，第三次同会话补齐完整判决，未把退出码 0 当验收。
- 2026-08-14 01:51: Codex 最终复核 6 张同源截图与 21 个物理页；浏览器 45 项通过，全量 582 项通过，Ruff、strict mypy、package verify、diff check 均通过。Task 4.2 accepted，下一步 Task 4.3。
