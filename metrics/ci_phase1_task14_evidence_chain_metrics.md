# Metrics: ci_phase1_task14_evidence_chain

Date: 2026-08-11

| Field | Value |
|---|---|
| Task type | `finite_code_task` |
| Risk | `medium` |
| Selected provider | `cms-smk` |
| Selected model | `deepseek-v4-flash` |
| Selected effort | `max` |
| Duration | 229.405 seconds |
| API calls | 1 个 runner round；无 fallback |
| Artifact size | 5,694 bytes（最终独立验收报告） |
| Result | PASS |

## Verification Burden

独立审查真实重跑精确 10 项、全库 118 项、Ruff、strict mypy 和包校验，并检查内容寻址、项目移动、日期语义、片段定位、追加式迁移与双合同失败关闭。Codex 随后用项目固定虚拟环境独立重跑同一检查组，并补测两个 nullable-but-required 字段的缺失拒绝。

## Routing Decision

按当前全局有限代码首选路由选择 `Pi/cms-smk/deepseek-v4-flash:max`；会话正常完成，无 fallback、无重派。日夜间策略评估未改变本次首选路由。
