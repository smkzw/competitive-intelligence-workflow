# Execution Metrics: ci-r2-capability-execution-gate-20260905

| Role | Provider | Model | Status | Duration | Tools | Result |
|---|---|---|---|---:|---:|---|
| `worker_01` | `cursor` | `default` | completed | 100.982 s | 98 | run-service insertion audit; report SHA `477d3587…6bb3` |
| `worker_02` | `cursor` | `default` | completed | 267.274 s | 252 | persistence/replay audit; report SHA `2f1c75e6…6d25` |
| `worker_03` | `cursor` | `default` | completed | 118.456 s | 137 | negative/recovery matrix; report SHA `343229fc…90e` |

Codex verification: focused 38 passed; integration 499 passed; full gate Ruff + strict
mypy 209 files + v1 active 940 + retained 20 + layering 7 + legacy scan; bundle 324 files,
SHA-256 `60af99a93a9a47da27da00b41b1721323a73d8841194bcbda856723696e76ecb`;
fresh-install 9 passed / 1 explicit real-host skip.
