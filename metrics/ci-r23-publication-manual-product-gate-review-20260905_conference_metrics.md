# Conference Metrics: ci-r23-publication-manual-product-gate-review-20260905

Date: 2026-09-05

| Role | Provider | Model | Status | Duration | API calls | Tokens | Result |
|---|---|---|---|---:|---:|---:|---|
| `evidence_single_object` | `grok-build` | `grok-4.6` | complete | 362.039 s | 15 | 1,471,039 | revise; D1-D10 accepted for disposition |

## Timeout And Retry Evidence

- Return code: 0; timed out: false; conference rounds: 1.
- Input tokens: 137,908; cache-read input tokens: 1,314,560; output tokens: 18,571; reasoning tokens: 12,795.
- Output SHA-256: `6680a043dd7f05015d187d45170cd833ce03ba715eaef02d451260e203b7c44d`.
- No retry, continuation, fallback, or late result. A post-result MCP child-process termination warning did not affect the persisted output.

## Quality Decision

The participant correctly rejected the pre-repair product gate and supplied reproducible defects. Codex closed all ten accepted findings and independently verified the resulting contracts and product paths. Conference verdict is pass-after-revision for R2.3 only, not release acceptance.
