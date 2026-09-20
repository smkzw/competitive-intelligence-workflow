# Codex 执行审阅：ci-phase8-task84-html-ppt-runtime

## Verdict

接受。Task 8.4 的独立 HTML-PPT 运行时合同已完成；此结论不等同于 A/B/C 正式幻灯片的视觉验收。

## 执行产出

- worker_01 完成候选运行时与项目 HTML-PPT 设计合同的差距审计。
- worker_02 收敛固定画布、深链、键盘导航、页码、进度、逐字稿、演讲者视图、计时与双窗同步。
- worker_03 补齐 Chromium/WebKit、多视口、`file://`、离线 ECharts SVG 及可追溯截图证据。

## Codex 独立复核与修订

- 将画布从 `translate + scale` 改为容器 Grid 双轴居中、画布单一等比缩放；浏览器断言直接检查几何中心误差、纯缩放矩阵和逻辑画布尺寸。
- 演讲者窗口增加独立外链、页面错误和控制台错误审计，并确认当前页/下一页预览帧已实际绘制。
- 原图审阅发现逐字稿与预览图表过早截图；改为等待过渡完成、内容可见和 SVG 实际生成后再取证。
- 独立会商发现演讲者截图文件名与真实尺寸不符；Codex 进一步识别出“演示结束”在未到末页误显示的 CSS 根因。修复后用原会话复验关闭。

## 决定性验证

- `node --check assets/html-ppt/runtime.js`
- `ruff` 通过。
- `pytest tests/acceptance/test_html_ppt_runtime_smoke.py`：18/18 通过。
- Chromium 和 WebKit 覆盖 1280×720、1600×900、1920×1080、2048×1024；全部为 `file://`，无远程请求、页面错误或控制台错误。
- 八张当前原始截图均由 Codex 重新打开审阅；逐字稿、演讲者下一页图表及首/末页结束状态已正常显示。
- 运行时清单中的 JS/CSS SHA-256 与实际文件一致。
- `audit-execution` 返回 `ok=true`，无路由漂移。
- 独立视觉会商同会话二轮复验建议接受；Codex 完成最终浏览器和原图验收。

## Boundary Compliance

Task 8.5 才负责 A/B/C HTML-PPT 视觉叙事与康哲 FX 母版注入；Task 8.6 负责正式幻灯片的最大化窗口视觉终验及点名多模型会商。

## Hermes Workflow Evidence

`audit-execution` 返回 `ok=true`。Grok Build 在建立可恢复会话前终止，runner 依声明回退链使用 `pi/cursor/cursor-grok-4.6:medium`，无路由漂移或任意替换。
