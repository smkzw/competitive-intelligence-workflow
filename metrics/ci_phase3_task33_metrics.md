# Metrics: ci_phase3_task33

Date: 2026-08-13

| Field | Value |
|---|---|
| Task type | `finite_code_task` |
| Risk | `high` |
| Selected provider | `opencode-go`（北京夜间路由生效） |
| Selected model | `deepseek-v4-flash` |
| Selected effort | `max` |
| Duration | 101.835 秒（三轮执行会话累计） |
| API calls | 13 次工具调用（三轮记录累计） |
| Artifact size | Task 3.3 源码、Schema、3 份精确测试及精简运行记录 |
| Result | `PASS；P0=0；P1=0` |

## Verification Burden

精确 3 项；既有 Phase 3 回归 241 项；全库 432 项；Ruff、strict mypy、Schema、包校验、diff 检查；两位隔离审查者分别执行 66/70 个临时探针。

## Routing Decision

声明首选为 CMS-SMK Flash；北京夜间覆盖将其替换为 OpenCode Go Flash。三轮均复用同一 Pi 会话，无 fallback。
