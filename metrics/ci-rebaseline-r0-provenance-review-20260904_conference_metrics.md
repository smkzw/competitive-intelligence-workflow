# Conference Metrics: ci-rebaseline-r0-provenance-review-20260904

Date: 2026-09-04

| Pass | Role | Provider | Model | Status | Duration | Tool calls | Output chars | Result |
|---|---|---|---|---|---:|---:|---:|---|
| Initial | `general_single_object` | `cursor` | `default` | completed | 543.815 s | 886 | 8,883 | VETO: 2 P1 + 3 P2 |
| Same-session remediation review | `general_single_object` | `cursor` | `default` | completed | 475.497 s | 963 | 5,329 | PASS |
| Total | — | — | — | completed | 1,019.312 s | 1,849 | 14,212 | PASS after repair |

## Route And Continuation Evidence

- Agent: Pi; session `01a06b65-d857-7000-8f30-816c54f99ec5` for both passes.
- Requested and observed runtime identity was `cursor/default` throughout.
- Round 2 records `resumed=true`, return code 0, no timeout, no fallback and no provider/model substitution.
- The runtime reported 2,879 output tokens for round 2 but no comparable aggregate token total for round 1; missing values are not inferred.

## Timeout And Retry Evidence

Both passes completed within the 7,200-second hard-wait boundary. No terminal failure or route fallback occurred. Codex waited on the existing process/session and did not re-dispatch because of silent runtime intervals.

## Verification Result

The participant re-ran the full four-step quality gate and focused negative checks before changing the verdict to PASS. Codex separately validated the external source/backup manifest pair and rehashed 19,498 read-only backup nodes. R0 is accepted as a preservation and quality baseline only; no implementation, portal, bundle, RC or release claim is counted here.
