# Execution Metrics: ci-r2-review-runtime-fixture-rebaseline-20260905

| Role | Provider | Model | Status | Duration | Tools | Result |
|---|---|---|---|---:|---:|---|
| `worker_01` | `zcode` | `GLM-5.3-Flash` | completed | runner did not emit a trustworthy aggregate duration | enabled | adopted after Codex hardening and independent verification |
| `worker_02` | `zcode` | `GLM-5.3-Flash` | completed | runner did not emit a trustworthy aggregate duration | enabled | adopted |
| `worker_03` | `zcode` | `GLM-5.3-Flash` | completed | runner did not emit a trustworthy aggregate duration | enabled | adopted |

Codex verification: gate `904 + 20 + 4` passing tests plus static/reference
checks; focused suite `103 passed` with three intentionally preserved stale
external-project failures; package verification passed; execution audit passed.

Requested side review: `gpt-6-astra:high` did not start. Native admission rejected
the unregistered model and the same-model CLI compatibility attempt terminated
with HTTP 400 because CLI 0.147.0 is below the model's required runtime version.
No fallback model was substituted.
