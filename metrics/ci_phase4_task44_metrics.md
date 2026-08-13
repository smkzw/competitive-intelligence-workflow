# Metrics: ci_phase4_task44

Date: 2026-08-14

| Field | Value |
|---|---|
| Task type | `html_ppt_visual_browser` |
| Risk | `high` |
| Selected provider | `alibaba` |
| Selected model | `qwen3.8-max` |
| Selected effort | `xhigh` |
| Duration | 约 2 小时 45 分（含实现、退修、双轮视觉试用与全回归） |
| API calls | 多会话；精确调用数由 runner stdout 保留，接受后不长期保留原始日志 |
| Artifact size | 当前 Task 4.4 截图 18 张；ECharts 包内资源 1,121,883 bytes |
| Result | PASS after revise-and-rerun |

## Verification Burden

245 项聚焦、851 项全库、两浏览器、scoped Ruff、strict mypy、包校验、资源摘要、真实截图与两条有效医学经理复验。

## Routing Decision

夜间视觉执行主路由不可用后按 manifest 使用 Cursor 同会话 fallback。用户指定视觉通道分别真实尝试；没有将 Grok 的无实质修复后输出替换为其他模型或伪记通过。
