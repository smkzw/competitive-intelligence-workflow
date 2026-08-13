# Metrics: ci_phase3_task36

Date: 2026-08-13

| Field | Value |
|---|---|
| Task type | `finite_code_task` |
| Risk | `high` |
| Selected provider | `opencode-go` |
| Selected model | `deepseek-v4-flash` |
| Selected effort | `max` |
| Duration | 多轮同会话修复；每轮均在 120 分钟硬等待内完成 |
| API calls | 由 runner stdout JSON 保留 |
| Artifact size | 实现提交 12 files / 4017 insertions / 7 deletions |
| Result | PASS；P0=0、P1=0、P2=0 |

## Verification Burden

四文件 11 项、含 CLI 15 项、全库 458 项；Ruff、strict mypy、schema/catalog、package verify、wheel 新模块和真实 fixture→resume→篡改拒绝均由 Codex复核。

## Routing Decision

finite-code 初始路由按全局策略进入 Pi；OpenCode-Go 会话发生运行模型身份漂移而被 runner 拒绝，随后使用声明的 Pi/DeepSeek 路由并在同一会话完成三轮针对性修复。未因延迟换路由。
