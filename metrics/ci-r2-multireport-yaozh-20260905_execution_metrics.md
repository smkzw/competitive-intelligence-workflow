# Execution Metrics: ci-r2-multireport-yaozh-20260905

| Role | Provider | Model | Status | Duration | Tools | Result |
|---|---|---|---|---:|---:|---|
| `worker_01` | `zcode` | `GLM-5.3:max` | completed | 2506.674 s | enabled | multi-report execution, state aggregation and digest-scoped resume |
| `worker_02` | `zcode` | `GLM-5.3:max` | completed | 1744.312 s | enabled | one-time project Yaozh answer and closed CLI/catalog contract |
| `worker_03` | `zcode` | `GLM-5.3:max` | completed | 787.673 s | enabled | independent baseline audit; D1/D2 repaired, D3 retained |

## Codex verification scope

- Three isolated workers, one completed round each, return code 0; receipt v2 includes
  `output_sha256` for every final report.
- Focused recovery: 6 passed; multi-report/Yaozh/adjacent contracts: 99 passed.
- Integration: 461 passed.
- Quality gate: Ruff `src tests tools`; strict mypy `src tools` 208 files; v1 unit/contract
  917 passed; retained compatibility 20 passed; layering 7 passed; legacy scanner passed.
- Package: 323-file disposable bundle, SHA-256
  `2c937684f1c8b531797c188a702143627fbdceab11ae702b879bd4e1fd2ff053`;
  required-v12 final-content verified; fresh-install 9 passed, 1 explicit real-host skip.
- Excluded: Yaozh browser-route consumption, interrupted-render recovery, real-host matrix,
  24-portal matrix, browser visual acceptance, clean RC and recovery freeze.
