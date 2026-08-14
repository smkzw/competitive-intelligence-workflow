# Task Context: ci_phase4_task46

Created: 2026-08-14 12:30:34
Objective: 实现 Task 4.6 全页面站点地图与 Chromium/WebKit 多视口验收工具，验证静态责任页和锁定快照内每个产品/试验动态详情页
Task type: `html_ppt_visual_browser`
Risk: `high`
Selected agent route: `cursor-cli` / `auto` / ``

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §15.1–15.6。
- `../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` Task 4.6。
- `.trellis/tasks/08-13-phase-4-common-report-portal/{prd.md,task.json}`。
- Task 4.1–4.5 已接受的页面注册表、ReportViewModel、门户构建器、筛选、图表和数据依据合同。
- 当前仓库与 `c8decdc` 为实现基线；不读取生产路径。

## Scope

- In scope：站点地图集合合同、只读门户验收器、CLI、Chromium/WebKit 1280/1440/1920、原分辨率截图、交互 trace、失败关闭测试。
- Allowed outputs：`src/ci_workflow/qc/browser.py`（必要时同包 `__init__.py`）、`tools/verify_portal.py`、`tests/acceptance/test_portal_runtime.py`、Task 4.6 合成夹具和本任务记录/验收产物。
- Out of scope：A/B/C 完整业务页、PDF/PPT、真实医学结论、自动修复产物、远程发布、安全测试。

## Success Criteria

- 从页面注册表与锁定快照生成精确 sitemap：每个静态责任页、每个产品详情页、每个试验详情页一一对应；缺页、多页、Top-N、额外 slug 均失败。
- 验证每页死链、控制台错误、页面错误、非本地请求、横向溢出、固定页眉/面板遮挡、重复 footer；验收器只能报告和否决，不能改产物。
- Chromium/WebKit 在 1280/1440/1920 遍历全部路由，保存每页原分辨率截图与带 run/site digest 的交互 trace。
- CLI 对缺失输入和失败项给出中文、明确、可操作说明；全库、Ruff、strict mypy 与独立视觉验收通过。

## Risk Boundaries

- Do not write to production paths until Codex review gate passes and writable paths are explicit.
- The delegated agent is not final authority; Codex owns verification and acceptance.
- 不做安全测试；聚焦用户功能、视觉、信息完整性和假绿防护。

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, malformed output, or a stale/incomplete catalog must be recorded and followed by one real route attempt. Explicit user-selected routes are not blocked merely because the catalog does not list them; only a missing executable or native transport boundary may stop before that attempt.

## Loop Log

- 2026-08-14 12:30:34: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- 2026-08-14 12:35: 读取最新全局/项目 AGENTS、设计、实施计划和 Trellis；沿用已冻结页面注册、门户壳层与康哲设计合同，不重新选型。
- 2026-08-14 13:20: 三个顺序 worker 完成站点地图、页面缺陷与双浏览器 CLI；Codex 否决手工 `--product/--trial` 范围，原 worker 会话补产物清单和不可变报告快照绑定。
- 2026-08-14 13:45: 真实执行计划相对路径命令失败，定位为 `Path.as_uri()` 接收相对路径；补黑盒节点并修复绝对解析。
- 2026-08-14 14:00: 首轮三路医学经理验收中 Grok 发现 5 个动态详情页是孤儿页且 H1 暴露机器 slug；按否决优先进入修订。
- 2026-08-14 14:25: 原 worker 会话补入口可达性 BFS、中文名称、可见产品/试验入口；Codex 继续发现跨目录搜索相对路径错误，补真实浏览器根页→产品、产品页→试验测试并修复三份相对索引。
- 2026-08-14 14:38: CodeBuddy/kimi-k2.6、Pi/minimax-m3、Grok Build/grok-4.6 均在原会话 R2 实跑 16 路由/96 截图/2 trace 并 PASS，无 P0/P1；Codex 查看当前原图。
- 2026-08-14 14:45: Task 4.6 63 项、相邻 69 项、全库 1019 项通过；Ruff、格式、strict mypy 通过。Task 4.6 与 Phase 4 接受，下一步 Phase 5 Task 5.1。
