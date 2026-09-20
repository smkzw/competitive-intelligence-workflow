# Conference Metrics: ci-phase8-task86-visual-final

Date: 2026-08-31

| Role | Provider | Model | Status | Duration | API calls | Tokens | Result |
|---|---|---|---|---:|---:|---:|---|
| `visual_single_object` | `kimi-code` → `openai-codex` | `k3-256k` → `gpt-5.6-terra` | 完成（同一 Pi 会话回退） | 见运行日志 | 见运行日志 | 未统一折算 | 首轮严重问题解除；剩余 P2 已修复 |
| `medical_manager` | `cms-router` | `minimax-m3` | 完成 | 见运行日志 | 见运行日志 | 未统一折算 | 有效问题修复；两项与最终原图冲突的判断不采纳 |
| `medical_manager` | `codebuddy` | `hy3-x` | 完成 | 67.162 秒 | 见运行日志 | 输入约 621、输出约 2019 | 建议通过 |
| `medical_manager` | `cursor` | `default` | 排除 | 两次连通性验证 | — | — | 未建立可靠视觉连接；未替换线路 |

## Timeout And Retry Evidence

- Kimi Code 在可恢复工作开始前返回 403 配额错误；按治理记录在同一 Pi 会话切换至 Terra，没有新建替代会话。
- Cursor/default 连通性验证连续两次失败后排除，未将诊断失败误判为视觉结论。
- 其余线路使用原会话完成第二轮复核；会话标识分别为 Terra `01a05648-7ed2-7000-91e0-cf0158fc4bf1`、MiniMax `01a05648-7ab0-7000-8419-22b6f3b78064`、CodeBuddy `b9547677-b77f-44b3-a1b2-c399d3a44fa6`。

## Quality Decision

会商不是终验。Codex 依据最终 `visual-final-4-*` 原图、当前 HTML 哈希、Ruff 与
22 项测试裁决通过；旧版原图中的问题或与当前图证冲突的意见不阻断交付。
