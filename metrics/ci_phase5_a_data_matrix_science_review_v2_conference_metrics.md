# Conference Metrics: ci_phase5_a_data_matrix_science_review_v2

Date: 2026-08-28

| Role | Provider | Model | Status | Duration | API calls | Tokens | Result |
|---|---|---|---|---:|---:|---:|---|
| `general_pi_antigravity` | `google-antigravity` | `gemini-3.7-flash` | completed | 41.206 s | 0 | 5,711 estimated | stale digest; excluded from final acceptance |
| `general_grok46` | `grok-build` | `grok-4.6` | completed | 258.338 s | not reported | 4,798 estimated | accepted current digest after same-session correction |

## Timeout And Retry Evidence

两条路线均正常结束、未超时、未触发 fallback。Pi 使用同一 session 两轮；Grok 使用同一 session 两轮，第二轮纠正 Amlitelimab 时间点判断并锁定当前摘要。

## Quality Decision

仅 Grok 最终轮满足当前候选身份与摘要要求；Pi 结论因对象陈旧被排除。Codex 结合确定性摘要、定向测试及后续视觉验收，接受当前候选。
