# Conference Metrics: ci_phase5_a_values_matrix_visual_review_v4

Date: 2026-08-29

| Role | Provider | Model | Status | Duration | API calls | Tokens | Result |
|---|---|---|---|---:|---:|---:|---|
| `visual_pi_k3_256k` | `grok-build` | `grok-4.6` | completed | 530.341 s initial + 251.947 s resumed | 3 completed rounds | 3,054,191 total tokens including cache | pass after repair |

## Timeout And Retry Evidence

- Initial session completed normally in 530.341 s and found two blocking visual defects.
- The resumed same-session runner completed two recorded rounds in 105.750 s and 146.197 s; both returned code 0 with `end_turn`.
- Session id remained `e6a575f5-3342-4985-89e4-44caf774f8da`; no fallback, timeout or redispatch occurred.
- The resumed call changed Grok reasoning effort to the user-requested medium while retaining the same provider/model/session.

## Quality Decision

Pass only after final-v5. The initial output was correctly treated as revise, not acceptance. Machine metrics, Chromium/WebKit rendering, Codex image inspection and same-session independent visual recheck now agree on the four bounded acceptance points.
