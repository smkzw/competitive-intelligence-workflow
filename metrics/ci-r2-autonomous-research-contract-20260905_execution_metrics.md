# Execution Metrics: ci-r2-autonomous-research-contract-20260905

| Role | Provider | Model | Status | Duration | Tools | Result |
|---|---|---|---|---:|---:|---|
| `worker_01` | `zcode` | `GLM-5.3-Flash:max` | completed | 659.605 s | enabled | autonomous task proposal; Codex retained compact source plan and completion contract |
| `worker_02` | `zcode` | `GLM-5.3-Flash:max` | completed | 1362.695 s | enabled | immutable submission proposal; Codex redesigned audit-envelope plus specialized payload binding |
| `worker_03` | `zcode` | `GLM-5.3-Flash:max` | completed | 544.696 s | enabled | progress-state proposal; requirements retained, duplicate state model rejected |
| `worker_04` | `openai-codex` | `gpt-5.6-luna:max` | completed | 2000.696 s | enabled | independent public-entry, package, bundle and host-boundary audit; scheduled ZCode output did not satisfy execution-report acceptance and declared fallback completed |

## Codex verification scope

- Workflow execution: four isolated workers, one accepted round each, return code 0; the
  current schedule selected ZCode for workers 01-03, while worker 04 used the declared
  Pi/Luna fallback after the ZCode output failed the execution-report acceptance check.
  Runner receipt v2 binds every final report byte by SHA-256; audit passed without warning.
- Quality gate: Ruff `src tests tools`; strict mypy `src tools` 207 files; v1 unit/contract
  917 passed; retained compatibility 20 passed; layering 7 passed; legacy scanner passed.
- Integration: 441 passed.
- Focused source-classification/submission contract: 12 passed; targeted Ruff/mypy passed.
- Package: 322-file disposable bundle built, final-content verified, fresh-installed,
  package-verified and isolated-import tested; then deleted.
- Excluded: multi-report product execution, persisted Yaozh choice, real-host matrix,
  24-portal matrix, browser visual acceptance, clean RC and recovery freeze.
