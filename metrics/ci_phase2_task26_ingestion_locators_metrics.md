# Metrics: ci_phase2_task26_ingestion_locators

Date: 2026-08-12

| Field | Value |
|---|---|
| Task type | `finite_code_task` |
| Risk | `medium` |
| Selected provider | `opencode-go` |
| Selected model | `deepseek-v4-flash` |
| Selected effort | `max` |
| Duration | 首轮约 11 分钟；两次同 session 修复复核约 10 分钟 |
| API calls | 1 个外部 session，3 轮；无 fallback |
| Artifact size | 精简报告约 18 KB；原始流接受后可恢复清理 |
| Result | PASS，最终 P0=0/P1=0/P2=0 |

## Verification Burden

独立验收重跑 5/178 项测试、Ruff、strict mypy、包校验与差异检查，并攻击未知分类、孤立 supplement、用户文件名/摘要/父子关系、登记数组路径、重复网页标题、PDF 页表行列、schema 漂移、跨版本和同快照坐标篡改。三项 P2 修复均复用原 session 验收。

## Routing Decision

Initial route reason: default route for task type.

北京夜间策略将声明的 CMS-SMK Flash 主节点替换为 OpenCode Go Flash。健康目录检查超时仅作诊断，随后真实路线成功建立 session `019ff1a4-cd94-7000-b9f0-fb96b0772b41`；两次补充复核恢复同一 session，无 fallback、无新建 session。
