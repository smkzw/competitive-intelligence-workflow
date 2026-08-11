# Metrics: ci_phase2_task24_foreign_connectors

Date: 2026-08-11

| Field | Value |
|---|---|
| Task type | `finite_code_task` |
| Risk | `medium` |
| Selected provider | `opencode-go`（北京夜间有效路由） |
| Selected model | `deepseek-v4-flash` |
| Selected effort | `max` |
| Duration | 首轮约 7 分 43 秒（含 90 秒诊断超时）；同 session 复核约 3 分 45 秒 |
| API calls | 1 个外部 session，2 轮；无 fallback |
| Artifact size | 精简报告约 9 KB；原始流接受后可恢复清理 |
| Result | PASS，最终 P0=0/P1=0/P2=0 |

## Verification Burden

独立验收重跑 7/166 项测试、Ruff、strict mypy、包校验与差异检查，并攻击分页/版本、原文可变、嵌套 PMID、方案论文误判、补充材料来源越权、监管声明越域、草案/撤回/替代、谱系环与多当前版本。三项 P2 修复后同 session 再验收。

## Routing Decision

Initial route reason: default route for task type.

北京夜间策略把声明的 CMS-SMK Flash 主节点替换为 OpenCode Go Flash。健康目录检查 90 秒超时仅作诊断，随后真实路线尝试成功，session `019ff176-4098-7000-a137-78698e26dd5b` 由首轮复用至补充轮；未 fallback、未新建 session。
