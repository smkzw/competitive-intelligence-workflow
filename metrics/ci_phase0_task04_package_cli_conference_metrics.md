# Conference Metrics: ci_phase0_task04_package_cli

Date: 2026-08-11

| Role / attempt | Provider | Model | Status | Duration | Tokens | Result |
|---|---|---|---|---:|---:|---|
| `general_pi_qwen38` initial + original-session closure | `cms-smk` | `cms-model` | 完成 | 718.535 秒 | 150,244（含缓存） | 初审提出阻断；原 session 修复复核 PASS |
| `general_pi_qwen38` time-route reset extra evidence | `cms-smk` | `cms-model` | 完成但不计同会话 | 186.232 秒 | 44,247（含缓存） | 有效附加 PASS；resume 被 runner 清空并新建 session |
| `general_grok45` initial + two recoveries | `grok-build` | `grok-4.5` | 恢复耗尽 | 78.053 秒 | 292,570（含缓存） | 三次 cancelled 进度句，不计验收 |
| `general_grok45` fallback 1 | `cursor-cli` | `cursor-grok-4.5-high` | 证据不足 | 192.885 秒 | 405,181（含缓存） | 静态审查；Shell 全部被 Ask 模式拒绝 |
| `general_grok45` fallback 2 | `cms-router` | `minimax-m3` | 完成 | 212.298 秒 | 47,897（含缓存） | 新鲜可执行验收 PASS |

## Timeout And Retry Evidence

- 所有 participant runner 使用 7,200 秒硬等待和 128 internal turns；主会场以 45 秒长轮询等待，不按固定短间隔重派。
- Grok session `c27fa169-1486-4f42-a661-72f63d328231` 首轮与两个同 session recovery 都是 `stopReason=cancelled` 且只有进度句；只有恢复耗尽后才 fallback。
- Cursor session `c9f05959-dd08-49da-978b-a6e0dd7ee04c` 完整返回，但 Ask 权限拒绝所有 Shell，无法满足真实命令验收；随后使用声明的第二 fallback，不把静态报告冒充执行 PASS。
- Pi 初始 session `019fefba-eb43-7000-8356-de4cd0f7b6b5` 正常完成。第一次修复续跑经 `beijing-qwen3.8-max-window` 时 `resume_session_reset=true`，产生 `019fefc8-7046-7000-99cf-532c42c701fd`；Codex识别后直接用有效 route 恢复原 session，终态仍为 `019fefba-eb43-7000-8356-de4cd0f7b6b5`。
- Minimax session `019fefc8-703d-7000-b1cb-cf7bac8962ff` 完整执行，无 fallback。

## Quality Decision

Pi 原 session 与 Minimax 两条独立可执行路径均验证全量 53 项、包校验、中文 CLI、deferred 退出码和变异失败关闭，最终 P0=0、P1=0。Grok 空输出和 Cursor 无 Shell 输出被保留为路由诊断但不参与 PASS。Task 0.4 接受；Task 9.5 bundle 义务继续保持未完成状态。
