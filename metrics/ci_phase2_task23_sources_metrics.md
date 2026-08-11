# Metrics: ci_phase2_task23_sources

Date: 2026-08-11

| Field | Value |
|---|---|
| Task type | `finite_code_task` |
| Risk | `medium` |
| Selected provider | 声明/夜间首选 `opencode-go`；实际验收 fallback `deepseek` |
| Selected model | `deepseek-v4-flash` |
| Selected effort | `max` |
| Duration | 最终 DeepSeek 验收约 256.209 秒；同 session 补充复核约 76.582 秒；首选路线另含健康检查 90 秒超时和未完成验收尝试 |
| API calls | OpenCode Go 1 次未被接受；DeepSeek 1 次验收 + 同 session 1 次复核 |
| Artifact size | 精简复核报告约 4 KB；runner 原始流接受后可恢复清理 |
| Result | PASS |

## Verification Burden

独立验收重跑 18/159 项测试、Ruff、strict mypy、包校验与差异检查，并攻击来源越权、事实/尝试混写、单次未找到提前完成、重复轮次、三次重试/退避伪造、两替代重复计数、审计字段缺失、状态回执错配及历史 cutoff 泄漏。首次 P2 账本缺口修复后同 session 复核。

## Routing Decision

Initial route reason: default route for task type.

北京夜间策略将 CMS-SMK Flash 替换为 OpenCode Go Flash。健康目录检查超时后按规则进行了真实路线尝试；真实尝试建立 session 但 runner 检出 `runtime_identity_mismatch`，因此按声明链 fallback 到 DeepSeek Flash。补充复核直接恢复已完成验收的 DeepSeek session，不新建 session、不再次 fallback。
