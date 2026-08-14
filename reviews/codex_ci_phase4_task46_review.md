# Codex Review: ci_phase4_task46

Date: 2026-08-14

## Verdict

**PASS after two false-green repair loops.** Task 4.6 已实现并通过完整站点地图、入口可达性、双浏览器三视口、全库回归与三路真实医学经理视觉验收。

## Boundary Check

- 产品代码变更仅限 `src/ci_workflow/qc/browser.py`、`src/ci_workflow/qc/__init__.py`、`tools/verify_portal.py` 与 `tests/acceptance/test_portal_runtime.py`。
- 其他变更均为本任务 context、prompt、run、review、metrics、Trellis 与受忽略的验收产物；未改通用康哲设计文件、生产路径或外部系统。
- 不做安全专项测试；所有检查聚焦用户功能、完整性、视觉与假绿。

## Hermes Routing Review

执行与会商均由 workflow guard 和 session runner 留存 provider、model、session 与同会话恢复记录；没有因超时重派，也没有静默 fallback。

## Codex Verification

- Task 4.6 验收文件：`63 passed in 109.55s`。
- 相邻共用视图/覆盖集/HTML-PPT 冒烟：`69 passed in 3.28s`。
- 全库：`1019 passed in 365.09s`。
- Ruff、格式检查、strict mypy（84 个生产源码文件）全部通过。
- 计划原始相对路径命令真实运行：16 路由 × Chromium/WebKit × 1280/1440/1920，96 张原分辨率截图、2 份 trace，退出 0。
- Codex 独立查看产品总览、产品详情和试验详情三张当前截图，确认中文标题、入口、Logo、导航、页脚与布局无 P0/P1。
- CodeBuddy/kimi-k2.6、Pi/cms-router/minimax-m3、Grok Build/grok-4.6 均复用 Task 4.5 原会话完成 R2，并一致 PASS，无 P0/P1。

## Delegated-Agent Output Review

- 首轮实现被 Codex 否决：CLI 可由调用者手填产品/试验清单，可能漏实体假绿。现只从 `html.manifest.json` 及其绑定的不可变报告快照读取，并核对站点摘要/字节数。
- 真实计划命令暴露相对 `--project` 无法生成 `file://`；补相对路径黑盒测试并修复为绝对解析。
- 首轮视觉验收再次否决：动态详情文件齐全但门户不可达，且 H1 暴露 `product-01`/`trial-02`。现从总览做确定性链接遍历，孤儿页在浏览器启动前失败；夹具提供中文名称、列表入口与跨目录搜索。
- 外部执行者自报通过未作为完成证据；所有关键结论均由确定性检查、真实浏览器产物和独立复核锚定。

## Residual Risk

Phase 5–7 接入真实 A/B/C 数据后仍须重新运行本工具；当前合成详情正文不代表完整业务页。Logo 回到总览、1280 搜索占位轻微截断与详情页返回入口列为 Phase 5 门户打磨 P2，不阻断 Task 4.6。
