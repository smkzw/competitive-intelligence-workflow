# Execution Metrics: ci-phase7-task75-report-c-portal

| Role | Provider | Model | Status | Duration | Tools | Result |
|---|---|---|---|---:|---:|---|
| `worker_01` | `openai-codex` fallback | `gpt-5.6-luna` | completed | 1937.5 s | runner未单列 | real fixture + RED |
| `worker_02` | `cursor` | `default` | completed | 942.6 s | runner未单列 | renderer + physical portal |
| `worker_03` | `cursor` | `default` | completed | 601.5 s | runner未单列 | independent browser RED |

## Route And Recovery Evidence

- Worker 01 primary Grok Build and Cursor CLI attempts ended before a usable
  resumable session; the runner recorded the declared Luna fallback and a
  completed output. Workers 02/03 started after the Beijing schedule boundary
  and used the packet's declared same-platform night branch.
- No silent model substitution or task re-dispatch occurred.

## Acceptance Evidence

- Final C suite: `197 passed in 58.32s`.
- Ruff: all checks passed.
- Browser attack: 120 checks, 740 passes, zero defects, 32 screenshots.
- Frozen digest: `bcf4fb223bea61c282684e80d2bae8c1906ecc7b2cf9d500970ee385da4df058`.
