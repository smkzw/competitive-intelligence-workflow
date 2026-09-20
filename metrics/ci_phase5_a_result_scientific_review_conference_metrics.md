# Conference Metrics: ci_phase5_a_result_scientific_review

Date: 2026-08-28

| Role | Provider | Model | Status | Duration | API calls | Tokens | Result |
|---|---|---|---|---:|---:|---:|---|
| `general_pi_antigravity` | `google-antigravity` | `gemini-3.7-flash` high | completed | 279.264s | 1 | 79,679 | 首轮过于乐观，不作为最终接受依据 |
| `general_grok46` | `grok-build` | `grok-4.6` medium | completed | 1177.679s | 3 | 3,965,747 | 两轮追问后接受最终摘要 |

## Timeout And Retry Evidence

- 两个首轮均返回码 0、无回退。
- Grok 首轮发现阻断后，按同一 session `7a62dcc6-4300-4103-8b0a-fe11c5ee04a2` 完成 round 2 与 round 3；没有新开会话。
- 三个 Grok round 的时长分别为 611.960s、379.675s、186.044s；均未超时、未截断。

## Quality Decision

Pi 首轮仅作补充证据；Grok 首轮拒绝、第二轮残余审计、第三轮最终接受形成有效独立挑战链。Codex 对最终摘要逐项复核后接受。
