# Conference Metrics: ci-1007-current-navigation-security-v1

Date: 2026-10-08

| Role | Provider | Model | Status | Duration | API calls | Tokens | Result |
|---|---|---|---|---:|---:|---:|---|
| `evidence_single_object` initial | `codebuddy-cli` | `deepseek-v4.1-flash` | exit0 |382.035s |56 parsed tool calls |not promoted to billing claim |REVISE |
| same-session bounded follow-up | `codebuddy-cli` | `deepseek-v4.1-flash` | exit0 |60.806s |3 tool-result events /11 assistant events |not promoted to billing claim |ACCEPT_BOUNDED F1/F3/F4 |

## Timeout And Retry Evidence

Single initial route with7200s hard wait/max-turns128 requested; same session continued once with6810s remaining timeout/16 turns requested. Total actual review442.841s plus6.319s initial health check, no timeout/fallback/latency redispatch. Follow-up initially failed prompt preflight (missing unique output declaration); runner did NOT dispatch until corrected preflight passed.

Native terminal num_turns166→181 is cumulative provider bookkeeping; initial stream109 assistant events, follow-up11. Do not claim that the wrapper independently enforces the provider turn counter. Requested max effort is not provider-attested. Reduced same-session independence is intentional targeted repair review. Shell unavailable; no reviewer test execution claimed. Raw runner logs stay local; compact source/output digests and actual identity are versioned.

## Quality Decision

Source corrections accepted only after owner50-case batch and fixed-source r10 HTTP proof; browser/Ego/install/scientific/three-host/24-portal acceptance separate. Initial REVISE, first source hashes and failure receipts retained.
