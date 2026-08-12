# Conference Metrics: ci_phase3_task33_acceptance

Date: 2026-08-13

| Role | Provider | Model | Status | Duration | API calls | Tokens | Result |
|---|---|---|---|---:|---:|---:|---|
| `general_pi_qwen38` | `alibaba` | `qwen3.8-max` | completed | 5699.392 秒（首轮+修复+摘要绑定） | 297 工具调用 | 原会话运行报告 | `PASS；P0=0；P1=0` |
| `general_grok45` | `grok-build` | `grok-4.5` | completed | 428.527 秒（含两次取消续跑与摘要绑定） | 原会话运行报告 | 原会话运行报告 | `PASS；P0=0；P1=0` |

## Timeout And Retry Evidence

Pi 健康探针超时为 advisory，真实主路线成功建立会话并完成；保持同一会话长等待。Grok 两次 `cancelled` 均保留同一 session，第三次以只读工具权限完成；无 fallback、无重派。

## Quality Decision

两位参与者分别完成 66/70 个完整探针，并对最终微修追加 31 项/摘要绑定复核；所有 P0/P1 清零，本任务内 P2 已关闭。投递指引与 PDF 登录页识别分别归 Task 3.5/3.6 和 Task 3.4。
