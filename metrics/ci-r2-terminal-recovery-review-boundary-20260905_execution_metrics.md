# Execution Metrics: ci-r2-terminal-recovery-review-boundary-20260905

| Role | Provider | Model | Status | Duration | Tools | Result |
|---|---|---|---|---:|---:|---|
| `worker_01` | `zcode` | `GLM-5.3-Flash` | completed | ~64 min | not separately counted | report retained; implementation rejected, minimal existing-contract adapter used |
| `worker_02` | `zcode` | `GLM-5.3-Flash` | completed | ~25 min | not separately counted | selectively accepted and tightened; runtime wiring remains open |
| `worker_03` | `zcode` | `GLM-5.3-Flash` | completed | ~40 min | not separately counted | accepted; preview-origin acceptance fail-closed |

No fallback and no redispatch occurred. All three sessions used the declared primary
route. Codex remained silent during the long waits and inspected outputs only after
runner completion.
