# Execution Metrics: ci-r2-yaozh-routing-20260905

| Role | Provider | Model | Status | Duration | Tools | Result |
|---|---|---|---|---:|---:|---|
| `worker_01` | `cursor` | `default` | completed | 112.790 s | 74 | authority/task findings; receipt v2 SHA `810f83b7…9ecd` |
| `worker_02` | `cursor` | `default` | completed | 140.787 s | 99 | optional dependency reproduction; receipt v2 SHA `f1467b10…d4a5` |
| `worker_03` | `cursor` | `default` | completed | 134.709 s | 100 | acceptance matrix and 21-test baseline; receipt v2 SHA `43c539ea…b46` |

Codex verification: focused TDD; integration 489 passed; full gate Ruff + strict mypy 209
files + v1 940 + retained 20 + layering 7 + legacy scan; final bundle 324 files,
SHA-256 `ae6f90bd498edc81ed8f05ab7ba5eecc4c59224629d0354e195dce68e237a2d5`;
fresh-install 9 passed / 1 explicit real-host skip.

User-requested sidecar review: CLI compatibility `gpt-6-astra:high`, completed once,
report SHA-256 `40b32b1f4dd42f2f690cd8cd9bbdf9a2e5395b0549782e274aaae042ead1223e`.
Native admission failed before dispatch because the stale guard catalog rejected Astra high;
no model substitution occurred.
