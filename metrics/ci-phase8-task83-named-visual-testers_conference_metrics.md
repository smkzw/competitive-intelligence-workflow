# Conference Metrics: ci-phase8-task83-named-visual-testers

Date: 2026-08-31

| Role | Provider | Model | Status | Duration | API calls | Tokens | Result |
|---|---|---|---|---:|---:|---:|---|
| `visual_single_object` | `kimi-code` | `k3-256k` | 完成 | 327.1 秒 | runner 记录 | runner 记录 | 首轮提出修订项 |
| `minimax_medical_manager` | `cms-router` | `minimax-m3` | 三轮完成 | 见 runner | runner 记录 | runner 记录 | 最终建议接受 |
| `cursor_grok_medical_manager` | `cursor` | `cursor-grok-4.6` | 三轮完成 | 见 runner | runner 记录 | runner 记录 | 最终建议接受 |
| `codebuddy_medical_manager` | `codebuddy-cli` | `hy3-x` | 三轮完成 | 见 runner | runner 记录 | runner 记录 | 最终建议接受 |

## Timeout And Retry Evidence

所有首轮和复验均自然结束；没有因延迟重复派发。点名路线已在 Task 8.2 首次启用时通过连通性测试，本次 runner 健康检查再次通过。

## Quality Decision

首轮发现真实中文受众与断行缺陷，触发一次修订回路；第三轮对最终哈希和像素证据达成无阻断结论。
