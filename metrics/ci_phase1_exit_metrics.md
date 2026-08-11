# Metrics: ci_phase1_exit

Date: 2026-08-11

| Field | Value |
|---|---|
| Task type | `finite_code_task` |
| Risk | `medium` |
| Selected provider | `cms-smk` |
| Selected model | `deepseek-v4-flash` |
| Selected effort | `max` |
| Duration | 首轮 985.35 秒；夜间路由后的窄幅复核 60.03 秒 |
| API calls | 首轮 1 round；补充复核 1 round；均无 fallback |
| Artifact size | 首轮报告 9,897 bytes；补充报告 2,142 bytes；7.4 MB runner 原始输出已清理 |
| Result | PASS |

## Verification Burden

独立评审复跑 62 项正式退出清单、133 项全库回归、7 项 SQLite 血缘专项、静态检查、包校验、Trellis 校验和真实项目移动/能力预检，并逐项审查孤儿归属、绝对路径、事件恢复、四类日期、回执/缺口、快照和当前运行清单绑定。Codex 另行执行两次真实临时项目演练和 Chromium 探针。

## Routing Decision

首轮按有限代码默认路由使用 `Pi/cms-smk/deepseek-v4-flash:max` 并正常完成。22:00 后补充复核触发全局夜间替换为 `Pi/opencode-go/deepseek-v4-flash:max`；runner 将请求的原 session 恢复重置为新 session，已作为机制偏差记录，且不影响首轮独立 PASS。
