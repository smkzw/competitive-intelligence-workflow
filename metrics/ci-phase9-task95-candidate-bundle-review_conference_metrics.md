# Conference Metrics: ci-phase9-task95-candidate-bundle-review

Date: 2026-09-01

| Role | Provider | Model | Status | Duration | API calls | Tokens | Result |
|---|---|---|---|---:|---:|---:|---|
| `general_single_object` 首轮 | `cursor` | `default` | 完成 | 51.830s | 0 | 约 2563 | 拒绝过早归档，发现恢复、Skill 自发现、安装与摘要绑定缺口 |
| `general_single_object` 同会话复审 | `cursor` | `default` | Pass | 155.987s | 63 | 约 2164 | 重新读取修复后证据，确认核心阻断项闭合并 advisory accept |

## Timeout And Retry Evidence

两轮使用同一会话 `01a05a8c-f404-7000-aada-4c33619bd1a4`；无 fallback、无超时、无重开会话。第二轮由 Codex 在完成真实三宿主复验后定向补发。

## Quality Decision

Pass。首轮缺陷均有磁盘证据闭合；残余建议不影响 Task 9.5 的 bundle、fresh-install、三真实宿主和站点式 HTML 退出条件。
