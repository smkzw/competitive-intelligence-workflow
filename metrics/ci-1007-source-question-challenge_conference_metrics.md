# Conference Metrics: ci-1007-source-question-challenge

Date: 2026-10-08 (local)

| Role | Provider | Model | Status | Duration | API calls | Tokens | Result |
|---|---|---|---|---:|---:|---:|---|
| `evidence_single_object` initial | `codebuddy-cli` | `deepseek-v4.1-flash`, max CLI | terminal incomplete | 525.454s | unknown;32 observed tool calls | whole model usage unknown | progress only; not accepted |
| same-session continuation | same | same | terminal bounded descriptive review | 213.456s | unknown;9 observed tools | unknown | 15 families / 35 contexts returned |

## Timeout And Retry Evidence

Initial exit0/no fallback is not complete review. Same-session resume uses the
remaining 6674-second process budget (initial525.454s of7200s), not another7200s
fresh model attempt. Resume preflight two errors corrected before launch; final
preflight0. No latency polling, redispatch or in-flight artifact QA.

## Quality Decision

15 descriptive families accepted with owner source corrections/limited scope;
cumulative runtime738.910s. No independently executed reviewer hashes/tests or
science-code review. No full numeric/source-universe/visual/RC claim.
