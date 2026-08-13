# Conference Metrics: ci_phase3_task36_acceptance

Date: 2026-08-13

| Role | Provider | Model | Status | Duration | API calls | Tokens | Result |
|---|---|---|---|---:|---:|---:|---|
| `general_pi_qwen38` | `opencode-go` | `deepseek-v4-flash` | completed | runner records | runner records | runner records | 最终 PASS，P0/P1/P2=0 |
| `general_grok45` | `grok-build` | `grok-4.6` | cancelled/incomplete | runner records | runner records | runner records | 不采信 |
| `general_grok45` fallback | `cursor-cli` | `cursor-grok-4.6-high` | completed | runner records | runner records | runner records | 修复后 PASS，P0/P1=0 |

## Timeout And Retry Evidence

Pi 健康目录查询超时但真实路由成功；Grok Build 首轮及两次同会话恢复均返回 cancelled/残缺，且最后一轮误扫其他参与者材料；耗尽恢复后按声明 fallback 使用 Cursor。所有长任务采用单次硬等待，无固定间隔重派。

## Quality Decision

首轮 exact/full 绿色仍被判 FAIL，暴露 CLI 恢复幽灵清单和 wheel 边界。修复后两位审查者清零 P0/P1；进一步关闭恢复前漂移、陈旧上下文、项目状态和异常映射，最终 Pi 复验 P0/P1/P2=0。Codex 以真实运行和 458 项回归接受。
