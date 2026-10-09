# Conference Metrics: ci-1007-source-additions-owner-review-v1

Date: 2026-10-10 CST

| Role | Provider | Model | Status | Duration | API calls | Tokens | Result |
|---|---|---|---|---:|---:|---:|---|
| `general_single_object` v1 | `zcode-live-bigmodel` | `GLM-5.3-Flash/max` | terminal | 821.427s | unknown | 113849 cumulative | scoped ACCEPT; impact metadata defect |
| same-session impact/scope v2 | `zcode-live-bigmodel` | `GLM-5.3-Flash/max` | terminal | 192.734s | unknown | 127052 cumulative | scoped ACCEPT repair |

## Timeout And Retry Evidence

One original session sess_d2e1f9f9-5c7b-4009-8956-8a18b7ec9f74, each round
exit0/no fallback. Runtime requested/response model and requested/observed max
verified; protocol errors empty. 14/11 parsed tool calls, zero parsed tool
results (not proof that tools were disabled). V1 live tmp-project probe2PASS
5.86s; v2 actual focused regression3PASS9.98s. No progress polling, latency
redispatch or new reviewer opinion. V2 preflight passed before launch.

## Quality Decision

Owner accepts the bounded code repair with actual126 related integration PASS
193.77s and Ruff5files/strict2product PASS. This is not real source adoption,
clinical/report/browser or RC acceptance. Both original reports/logs retained.
V1 reportSHA8c4fc269; v2 reportSHAf68e4f9a. Latest frozen source088a7500,
shared builderded89faa, test541ad17e. Pre-repair interrupted manifests remain
historical and are not rewritten into new evidence.
