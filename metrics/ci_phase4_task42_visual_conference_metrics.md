# Conference Metrics: ci_phase4_task42_visual

Date: 2026-08-14

| Role | Provider | Model | Status | Duration | API calls | Tokens | Result |
|---|---|---|---|---:|---:|---:|---|
| `medical_manager_visual_codebuddy` | `codebuddy-cli` | `kimi-k2.6` | complete | 163.471 s（第二轮） | runner 记录 | runner 未结构化汇总 | PASS |
| `medical_manager_visual_minimax` | `cms-router` | `minimax-m3` | complete | 173.561 s（第二轮） | runner 记录 | 99,918 | PASS |
| `medical_manager_visual_grok` | `grok-build` | `grok-4.6:high` | complete | 160.567 s（第三轮） | runner 记录 | 116,859 | PASS |

## Timeout And Retry Evidence

- 三条路线首次均先做各自健康检查，再执行真实审查。
- CodeBuddy 与 Pi 首轮提出修复项后复用原 session 做第二轮，没有新开或改模型。
- Grok 首轮和第二轮均在浏览器工具边界以 cancelled 返回不完整过程句；未视作通过，第三轮继续同一 session 并禁止重复工具调用后得到完整判决。

## Quality Decision

三条指定路线最终均 PASS；Codex 结合确定性浏览器测试与实图复核接受 Task 4.2。评审中超出当前任务的数据/图表要求被记录到 4.3–4.5，而非用假数据补齐。
