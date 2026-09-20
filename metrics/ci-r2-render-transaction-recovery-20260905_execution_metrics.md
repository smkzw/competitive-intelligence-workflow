# Execution Metrics: ci-r2-render-transaction-recovery-20260905

| Role | Provider | Model | Status | Duration | Tools | Result |
|---|---|---|---|---:|---:|---|
| `worker_01` | `zcode` | `GLM-5.3:max` | completed | 2539.069 s | enabled | shared render transaction, A adapter and RED/GREEN matrix |
| `worker_02` | `cursor` | `default` | completed | 420.417 s | enabled | B/C adapters and per-report recovery tests |
| `worker_03` | `cursor` | `default` | completed | 185.654 s | enabled | read-only post-integration transaction/binding audit |

## Codex verification scope

- Three governed sessions, one completed round each, return code 0; runner receipt v2 binds
  every final report with `output_sha256`.
- Focused transaction suite: 43 passed; integration: 481 passed.
- Quality gate: Ruff `src tests tools`; strict mypy `src tools` 209 files; v1 unit/contract
  940 passed; retained compatibility 20 passed; layering 7 passed; legacy scanner passed.
- Package: 324-file disposable bundle, SHA-256
  `cbe06b136e90b416943eb9c7087fec0ce4709dda0872e43b6018d8b105c81e77`;
  required-v12 final-content verified; fresh-install 9 passed, 1 explicit real-host skip.
- Excluded: real-host matrix, browser visual acceptance, 24-portal matrix, clean RC,
  recovery freeze, concurrent writers and orphan-snapshot cleanup.
