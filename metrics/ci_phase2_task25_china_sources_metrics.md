# Metrics: ci_phase2_task25_china_sources

Date: 2026-08-12

| Field | Value |
|---|---|
| Task type | `finite_code_task` |
| Risk | `medium` |
| Selected provider | `opencode-go` |
| Selected model | `deepseek-v4-flash` |
| Selected effort | `max` |
| Duration | 首轮约 12 分钟（含 90 秒诊断超时）；同 session 复核约 5 分钟 |
| API calls | 1 个外部 session，2 轮；无 fallback |
| Artifact size | 精简报告约 14 KB；原始流接受后可恢复清理 |
| Result | PASS，最终 P0=0/P1=0/P2=0 |

## Verification Burden

独立验收重跑 7/173 项测试、Ruff、strict mypy、包校验与差异检查，并攻击 CDE/NMPA 事件错配、登记原文篡改、locator 丢失、DXY 冒充官方、企业/会议冒充论文或登记、公众号越域、策略漂移和 CDE 指南草案/替代/跨辖区覆盖。两项 P2 修复后复用原 session 再验收。

## Routing Decision

Initial route reason: default route for task type.

北京夜间策略将声明的 CMS-SMK Flash 主节点替换为 OpenCode Go Flash。健康目录检查 90 秒超时仅作诊断，随后真实路线成功建立 session `019ff18c-07bf-7000-a6f2-7599e684805c`；补充轮恢复同一 session，无 fallback、无新建 session。
