# Codex Execution Plan: ci-1007-source-current-additions-v1

Objective: Extend the existing source-current refresh transaction to append newly accepted source atoms without dropping prior active or user-cleared facts

## Work Items

| Worker | Assigned item | Report |
|---|---|---|
| `worker_01` | Implement optional typed accepted-source additions in source_current_refresh.py with bounded root-family regression tests; no scientific acceptance, live project, database, browser, Git or current writes | `runs/execution/ci-1007-source-current-additions-v1/worker_01.md` |

## Codex Acceptance

Bounded optional source additions within the existing transaction, preserving replacement-only compatibility, accepted-source proof/exact snapshot consumers, old current/user-clear/unaffected C, legitimate A+B propagation, bad-source/value/scope/duplicate/stale rejection, idempotency and failure-current rollback. One RED family/coherent change/related regressions, scoped static checks. Only source_current_refresh.py/new test file product edits; no real project/source adoption/browser/Git writes. Owner separately integrates sources and accepts.
