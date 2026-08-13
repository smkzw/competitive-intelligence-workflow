# Metrics: ci_phase4_task43

Date: 2026-08-14

| Field | Value |
|---|---|
| Task type | `html_ppt_visual_browser` |
| Risk | `high` |
| Selected provider | `alibaba` |
| Selected model | `qwen3.8-max` |
| Selected effort | `xhigh` |
| Duration | 跨一次中断恢复；最终验收约 4 小时 |
| API calls | runner 回执留存；不以调用量作为质量结论 |
| Artifact size | 最终代码与测试约 2,600 行差异；截图另存 `.artifacts` |
| Result | PASS；P0=0，P1=0 |

## Verification Burden

203 项聚焦测试 + 697 项全库测试；Ruff、strict mypy、包校验、diff check；三模型真实视觉试用；Codex 原分辨率复核。

## Routing Decision

声明主路线按夜间视觉/浏览器规则选择 Qwen 3.8 Max，但实时配额/runner 未产出可接受结果；保留失败证据后，按声明链使用同一 Cursor 会话完成两轮修复。没有把失败路线生成物直接视为完成。
