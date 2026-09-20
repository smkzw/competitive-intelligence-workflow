# Codex Execution Review: ci-r2-review-runtime-fixture-rebaseline-20260905

## Verdict

`accept` for this bounded execution slice. This is not R2 completion, real-source
matrix acceptance, RC freeze, or release.

## Worker Outputs

- `worker_01`: adopted only after Codex tightened the implementation. The final
  transition reopens the verdict artifact bytes, validates the artifact as a
  formal `ScientificQcVerdict`, rebuilds authoritative persisted lineage, binds a
  separate review request to the original producer session/run and immutable
  candidate digest, and permits only one-way promotion from
  `rendered_unreviewed`.
- `worker_02`: adopted. Missing caller-declared preview snapshots are no longer
  trusted; B/C preview paths self-lock their actual data and remain
  `rendered_unreviewed`. Existing but corrupt or identity-mismatched snapshots
  still fail closed.
- `worker_03`: adopted. HTML-only v1 tests and retained non-HTML regression tests
  are explicitly separated, the gate reports its real scope, and stale B drawer
  assertions no longer invent an unreported numerator.

## Manager Assessment

No execution manager was declared. Codex reviewed all three worker reports,
their actual patches, the affected runtime paths, and the independent test
results. The execution packet audit reports all three roles present with no
route drift, missing logs, warnings, or errors.

## Codex Independent Verification

- `tools/gate.sh`: passed all six steps. Ruff passed; strict mypy passed on 204
  source files; v1 fast layer `904 passed, 20 deselected`; retained legacy layer
  `20 passed, 904 deselected`; layer audit `4 passed`; legacy runtime reference
  scan passed.
- Focused R2/runtime/preview/visual/real-source suite: `103 passed`; the only
  three failures are the preserved positive checks against Task 10.2 external
  A/B/C projects. Those artifacts correctly fail because their recorded
  `package_digest` predates the current candidate. They require R5 regeneration
  and must not be relabeled, mutated, or excluded as if current.
- `ci-workflow package verify --root .`: `PACKAGE_OK`, stage
  `development-candidate`.
- `audit-execution --task-type long_horizon_code`: `ok=true`, three completed
  worker outputs, no manager required, no warnings or errors.
- The requested independent `gpt-6-astra:high` stage review was attempted after
  prompt preflight. Native admission rejected the unregistered model; the
  same-model CLI compatibility attempt then reached the service and terminated
  with HTTP 400 because Codex CLI 0.147.0 is too old for `gpt-6-astra`. No other
  model was substituted, so no Astra review verdict exists.

## Cleanup Decision

Archive this accepted execution packet with the workflow guard, then remove only
the three exact runner workspaces and the exact debug directory after archive
verification. Preserve source, reports, logs, hashes, current project `tmp/`,
protected Codex sessions, and every unrelated dirty-tree item.
