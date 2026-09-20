# Execution Metrics: ci-r2-bc-research-package-wiring-20260905

| Role | Provider | Model | Status | Duration | Tools | Result |
|---|---|---|---|---:|---:|---|
| `worker_01` | `zcode` | `GLM-5.3-Flash` | completed | shared hard wait ~47 min | enabled | rejected wholesale: caller gate trust violation |
| `worker_02` | `zcode` | `GLM-5.3-Flash` | completed | shared hard wait ~47 min | enabled | selectively accepted and repaired |
| `worker_03` | `zcode` | `GLM-5.3-Flash` | completed | shared hard wait ~47 min | enabled | selectively accepted and repaired |

All roles completed in one runner round with no fallback or re-dispatch. The
runner exposed one shared hard-wait duration rather than trustworthy per-role
durations, so no fabricated individual timing is reported.
