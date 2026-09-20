# Metrics: ci-r24-gatespec-blocker-closure-20260905

Date: 2026-09-06

| Field | Value |
|---|---|
| Task type | `long_horizon_code` |
| Risk | `high` |
| Selected provider | `cursor` |
| Selected model | `default` |
| Selected effort | `` |
| Duration | execution workers 183.998–247.919 s each; conference recorded separately |
| API calls | three governed worker runner passes |
| Artifact size | three compact worker reports plus v2 receipts; product changes remain in dirty tree |
| Result | execution accepted; parent task pending freshness decision |

## Verification Burden

Codex independently reran deterministic code, product-chain and package gates. Worker output was used
to discover attacks, not to establish done. Browser/visual acceptance was not in this control task.

## Routing Decision

Initial route reason: user-declared node route; risk governs acceptance, not silent substitution.
