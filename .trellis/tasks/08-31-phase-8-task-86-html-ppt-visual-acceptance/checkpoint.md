# Task 8.6 检查点

## 起点

- A 20 页：`adcf8487aa85996d0d4886d7801a16a544f2b703cac5a331d4a7a7af085eb2e4`
- B 24 页：`087d04b0aa1ddb0da26c5370fcf26e8bb328efc4705136194bbe0ecdb5740b1d`
- C 18 页：`fd2d47565bfdb1b12f6405c62ed53f9762eac67c92175302a5a6eba8d3064113`
- Task 8.5：22 项测试、Ruff、三轮视觉会商、只读收口执行审计均通过。

## 首轮重点

1. A `a-matrix-2` 相邻标签留白与引线。
2. C `EASI ≥ 75 %改善` 的中文排版。
3. B `b-efficacy` 92.2 数值与图例间距。
4. 全 62 页最大化和非 16:9 原图，而非继续抽样。

## 2026-08-31 续建锚点

- 已重新读取最新全局/项目 `AGENTS.md`，并完整读取 `ponytail`、`html-ppt`、`kangzhe-design` 的 `ROUTER → core → track_htmlppt → htmlppt_fx`、`clinical-ppt-visual-review`、`playwright`、`trellis-framework`、`multi-agent-harness-ops`。
- 项目内化版 `core.md`、`track_htmlppt.md`、`htmlppt_fx.md`、Logo 与 `gx_fx.css/js` 和最新版逐字节一致；项目 `ROUTER.md` 保留已批准的四格式/PDF专属扩展，不回写通用版。
- 当前显示器基线：CFORCE 的 CSS 尺寸 1280×800；Mi Monitor 的 CSS 尺寸 1920×1080。另保留 1280×720 与 2048×1024。
- 本轮点名测试线路更新为 `pi/cms-router/minimax-m3`、`pi/cursor/default`、`codebuddy/hy3-x`。

## 2026-08-31 完成锚点

- 最终哈希：A `718705c6d1aa1347907b600e27a9753230f8ad93afb17a0cfa73f44eb164d7a6`；B `2bf6a334fd484f1df99bca363f1425503f83e9aa9727a73986a6fcd846c3a406`；C `e284dec451cc8355a5ebdd376a903785b3a10e984a9a6bae9bc3c73a61a8f342`。
- 最终证据：`visual-final-4-chromium` 与 `visual-final-4-webkit` 各 248 张原图，四视口自动缺陷均为 0。
- Codex 已查看 Chromium 1920×1080 全部 62 页，并对矩阵页及 9 个改动/高密度页完成跨视口、跨浏览器补充终验。
- Ruff 通过，HTML-PPT 测试 22 项通过。
- Terra 的剩余 P2 已修复；CodeBuddy 建议通过；MiniMax 与当前原图冲突的判断已由 Codex 驳回；Cursor/default 两次连通失败后排除且未替换。
- 最终接受记录：`docs/acceptance/runs/8.6/final-visual-acceptance.md`。
- 下一安全动作：按重构实施计划进入 Task 8.6 之后的跨格式阶段；HTML-PPT 通过不得外推为 PDF/PPTX 通过。
