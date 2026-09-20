# Execution Metrics: ci-r23-publication-manual-product-gate-20260905

| Role | Provider | Model | Status | Duration | Tools | Result |
|---|---|---|---|---:|---:|---|
| `worker_01` | `cursor` | `default` | complete | 139.280 s | not reported | publication / package / connector audit accepted as input |
| `worker_02` | `cursor` | `default` | complete | 143.848 s | not reported | manual-inbox / run-service audit accepted as input |
| `worker_03` | `cursor` | `default` | complete | 148.219 s | not reported | negative-test matrix accepted as input |

## Route And Completion

- All three runner invocations returned code 0 on the declared `cursor/default` route.
- No fallback, manager, production write, or external account operation occurred.
- The provider did not expose stable aggregate token/tool counts in these runner records; those fields are recorded as unavailable rather than estimated.
- `audit-execution` passed with all three required worker reports complete and no route-identity error. The packet intentionally declared no execution manager; Codex performed integration and acceptance review.

## Quality Decision

Worker conclusions were treated as dated audit input, not acceptance. Codex verified each accepted finding against the current bytes, implemented the product-path repairs, expanded the negative tests, and reran the decisive checks documented in the corresponding review.
