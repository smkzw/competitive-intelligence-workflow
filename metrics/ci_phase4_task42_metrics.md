# Metrics: ci_phase4_task42

Date: 2026-08-14

| Field | Value |
|---|---|
| Task type | `html_ppt_visual_browser` |
| Risk | `high` |
| Selected provider | `alibaba` |
| Selected model | `qwen3.8-max` |
| Selected effort | `xhigh` |
| Duration | 跨执行、补修与三方复审的长任务；各外部路线按 120 分钟硬等待运行 |
| API calls | 由各 runner 记录；未汇总为单一调用数 |
| Artifact size | 门户源代码、共享资产、45 项浏览器测试；验收站点 21 个物理页 |
| Result | PASS；P0=0，范围内 P1=0 |

## Verification Burden

真实截图揭示两类原测试未覆盖的假绿：三页导航无法外推至 B 类 21 页，以及技术占位语污染受众页面。新增 B 类 21 页/5 组矩阵、显式导航覆盖、中文禁词、同源截图和三模型医学经理复审后关闭。

## Routing Decision

夜间主路线 Qwen 真实调用以 429 周配额终止；Harness 未声明的 Mimo 替代被拒绝。有效执行使用声明的 Cursor CLI fallback，同一会话完成两次补修。最终视觉验收使用用户指定 CodeBuddy/Kimi 2.6、Pi/Minimax M3、Grok Build 4.6，均未 fallback。
