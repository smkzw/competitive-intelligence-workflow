# Conference Metrics: ci_phase5_a_data_matrix_visual_review_v2

Date: 2026-08-28

| Role | Provider | Model | Status | Duration | API calls | Tokens | Result |
|---|---|---|---|---:|---:|---:|---|
| `visual_pi_k3_256k` | `kimi-code` | `kimi-code/k3-256k` | completed | 233.304 s (v8 final pass) | 9 | 2,379 estimated | accepted v8 after real Chromium recheck |

## Timeout And Retry Evidence

首次 v6 运行正常完成并拒绝；一次同 session 续跑因仍使用旧对象而判为无效证据；最终在相同 session 中以 v8 上下文重新实测，正常完成、未超时、未触发 fallback。

## Quality Decision

最终 v8 轮满足对象身份、三视口、真实浏览器、截图与运行时测量要求。Codex 独立测量与参与者结果一致，视觉门槛通过。
