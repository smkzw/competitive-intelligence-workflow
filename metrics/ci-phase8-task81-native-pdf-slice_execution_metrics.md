# Execution Metrics: ci-phase8-task81-native-pdf-slice

| Role | Provider | Model | Status | Duration | Tools | Result |
|---|---|---|---|---:|---:|---|
| `worker_01` | `cursor` | `default` | completed | runner recorded | enabled | fixture + structural RED |
| `worker_02` | `cursor` | `default` | completed | runner recorded | enabled | ReportLab builder + flowables |
| `worker_03` | `cursor` | `default` | completed | same-session 2 rounds | enabled | structure/text/render verification |

## Route And Recovery Evidence

- All three workers used the declared `pi/cursor/default` execution route.
- Worker 03 retained session `01a053a8-a362-7000-844d-9828c708d116` for its
  targeted post-fix continuation; no silent provider/model substitution occurred.
- Poppler tools were supplied from the bundled runtime path; no package install or
  fallback was required.

## Acceptance Evidence

- Focused tests: `8 passed`.
- Ruff: all checks passed.
- Final PDF SHA-256: `b32d7c390ec3d456a5b47c63f996537c360ce7ac0bb3068784c624ed8e9cbbbe`.
- Current pages: 4 SHA-bound renders at 150 dpi.
