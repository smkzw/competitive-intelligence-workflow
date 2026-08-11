# Metrics: ci_phase2_task21_ontology

Date: 2026-08-11

| Field | Value |
|---|---|
| Task type | `finite_code_task` |
| Risk | `medium` |
| Selected provider | `opencode-go` |
| Selected model | `deepseek-v4-flash` |
| Selected effort | `max` |
| Duration | 独立评审 309.273 秒；首次连通性检查约 90 秒 |
| API calls | 1 round；无 fallback |
| Artifact size | 精简报告 7,951 bytes；约 4.9 MB runner 原始输出待可恢复清理 |
| Result | PASS |

## Verification Burden

独立评审复跑四个 exact GREEN、隔离复现四个 RED、4/5/137 项套件、Ruff、strict mypy、包校验与差异检查，并对自由文本纳入、传统背景提升、纯传统组合、pending 静默排除、提前闭合、审查回执不完整和包漏登记进行对抗探针。

## Routing Decision

任务在北京夜间创建，守卫按全局策略将声明的 CMS-SMK 路由替换为 `Pi/opencode-go/deepseek-v4-flash:max`；连通性检查和真实会话均成功，无 fallback。
