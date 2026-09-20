# Execution Metrics: ci-r2-independent-review-hardening-20260905

| Role | Provider | Model | Status | Duration | Tools | Result |
|---|---|---|---|---:|---:|---|
| `worker_01` | `zcode` | `GLM-5.3-Flash` | completed | 2140.447 s | enabled | review issuer + CLI; Codex integrated A/B/C and runtime verification |
| `worker_02` | `zcode` | `GLM-5.3-Flash` | completed | 2328.800 s | enabled | post-format B/C binding and resume; Codex extended lineage acceptance |
| `worker_03` | `zcode` | `GLM-5.3-Flash` | completed | 2878.289 s | enabled | A parity; semantic hunks accepted, broad formatting not copied |
| `worker_04` | `zcode` | `GLM-5.3-Flash` | completed | 1894.500 s | enabled | bundle closure and bounded retained-smoke semantics |

## Codex verification scope

- Workflow audit: passed, 4/4 outputs present, no route drift.
- Quality gate: Ruff `src tests tools`; strict mypy `src tools` 205 files;
  v1 unit/contract 913 passed; retained compatibility subset 20 passed;
  layering 7 passed; legacy scanner passed.
- Integration: 438 passed.
- Focused hardening: 91 passed.
- Package: package manifest verified; 320-file candidate bundle built and final-content
  verified. Candidate bundle is disposable verification evidence, not an RC artifact.
- Excluded from this pass: real-host matrix, browser screenshot-byte verification,
  24-portal matrix, clean RC/fresh install/recovery freeze.
