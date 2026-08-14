# Conference Metrics: ci_phase4_task45_visual

Date: 2026-08-14

Duration: 11:02–15:05（含两轮同会话定点修复复核）。

| Role | Provider | Model | Session | Final result |
|---|---|---|---|---|
| 医学经理审评 1 | codebuddy-cli | kimi-k2.6 | `96496dd2-dc1c-4756-a0c4-b17a8118fba4` | R3 PASS |
| 医学经理审评 2 | grok-build | grok-4.6 | `76fd5696-801c-4fff-95bd-78bdaedca621` | R3 PASS |
| 医学经理审评 3 | cms-router | minimax-m3 | `019ffe3c-9dbf-7000-bdbb-9872c1542a07` | R3 PASS |

## Timeout And Retry Evidence

三路首次调用均做真实连通与操作；长任务按 120 分钟硬等待，不因运行中或无新增输出而重派。MiniMax R2 报告在工具调用处截断，按同会话恢复；其余均为同会话定点复核，无隐式 fallback。

## Quality Decision

R1/R2 的 REVISE 均有截图和可复现交互支撑；修复后 R3 三路一致 PASS，Codex 的确定性检查与独立视觉复核一致。
