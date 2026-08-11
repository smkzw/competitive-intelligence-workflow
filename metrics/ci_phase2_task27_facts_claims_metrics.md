# Metrics: ci_phase2_task27_facts_claims

Date: 2026-08-12

| Field | Value |
|---|---|
| Task type | `finite_code_task` |
| Risk | `medium` |
| Selected provider | `opencode-go` |
| Selected model | `deepseek-v4-flash` |
| Selected effort | `max` |
| Duration | 首轮约 6 分钟；两次同 session 修复复核约 7 分钟 |
| API calls | 1 个外部 session，3 轮；无 fallback |
| Artifact size | 三份精简审查报告；原始流接受后可恢复清理 |
| Result | PASS，最终 P0=0/P1=0/P2=0 |

## Verification Burden

独立验收重跑 4/182 项测试、Ruff、strict mypy、包校验和差异检查，并攻击来源重开、科学身份、规范化、冲突、披露状态、声明类型、计算文字、中文幅度表达和 schema 漂移。九项 P2 修复均复用原 session 验收。

## Routing Decision

Initial route reason: default route for task type.

北京夜间策略将声明的 CMS-SMK Flash 主节点替换为 OpenCode Go Flash。健康目录检查超时仅作诊断，随后真实路线成功建立 session `019ff1c2-a806-7000-847e-0deedae9f560`；两次补充复核恢复同一 session，无 fallback、无新建 session。
