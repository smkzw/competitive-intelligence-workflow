# Metrics: ci_phase5_task51

Date: 2026-08-14

| Field | Value |
|---|---|
| Task type | `competitive_intelligence` |
| Risk | `high` |
| Selected provider | `codex` |
| Selected model | `codex-main` |
| Selected effort | `high` |
| Duration | 约 2 小时 10 分钟（含三轮独立审查与全仓回归） |
| API calls | 3 个顺序 worker 初始 pass、1 个同 session 修复 pass、3 个同 Luna session 审查 pass |
| Artifact size | A 源码与测试约 3,000 行；紧凑 run reports 约 60 KB |
| Result | PASS；Task 5.1 accepted |

## Verification Burden

91 项专项、308 项共享证据交叉回归、1110 项全仓测试、Ruff、strict mypy；独立 Luna 30 个反例最终通过。

## Routing Decision

Initial route reason: high-risk clinical evidence contract. Worker 使用 Pi/CMS-SMK DeepSeek V4 Flash；原生 Luna capability probe 明确拒绝后，按 AGENTS 使用 `gpt-5.6-luna:max` CLI compatibility fallback，并在同一 session 完成三轮审查。
