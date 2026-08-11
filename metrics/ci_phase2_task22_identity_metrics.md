# Metrics: ci_phase2_task22_identity

Date: 2026-08-11

| Field | Value |
|---|---|
| Task type | `finite_code_task` |
| Risk | `medium` |
| Selected provider | `opencode-go` |
| Selected model | `deepseek-v4-flash` |
| Selected effort | `max` |
| Duration | 首次评审约 130.325 秒；同 session 复核约 89.625 秒；首次健康检查约 90 秒超时但真实路线成功 |
| API calls | 同一 session 三个模型轮次；修复后 runner 调用含两轮；无 fallback |
| Artifact size | 精简报告约 7 KB；runner 原始输出约 3 MB，接受后可恢复清理 |
| Result | PASS |

## Verification Burden

Reviewer 重跑 10/147 项测试、Ruff、strict mypy、包校验与差异检查，并攻击名称/NCT/CTR 主键滥用、实体类型碰撞、别名/标识符冲突先到先得、静默覆盖、重复/漏评适格、未知引用、pending 绕过与 Top-N 截断。首次两项 P1 经同 session 修复复核闭合。

## Routing Decision

Initial route reason: default route for task type.

任务在北京夜间创建，守卫把声明的 CMS-SMK 节点替换为 `Pi/opencode-go/deepseek-v4-flash:max`。健康目录检查 90 秒超时，按规则作为诊断保留并执行一次真实路线；真实路线成功建立 session。修复后使用同一 session 继续，没有重置或 fallback。
