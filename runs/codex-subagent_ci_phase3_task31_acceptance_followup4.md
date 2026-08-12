# Final Read-Only Reassessment

## Boundary

Reviewed only the supplied Task 3.1 artifacts. No source, test, Trellis, acceptance, or runner files were modified; the requested runner output file was not written.

Sources read included the prior report, pause record, worker/manager followups, implementation plan, ADR, gate modules, and all three Task 3.1 test files.

## Verification

Commands and outputs:

- Exact trio with cache/bytecode disabled: `143 passed`.
- Full suite with `TMPDIR=/tmp`: `331 passed`.
- Two new regressions: `2 passed`.
- Additional coverage/lineage/threshold/A-B-C/parent tests: `12 passed`.

## Findings

1. Model-copy tampering is closed.

`_aggregate_report_gates` calls `_assert_batch_integrity` before semantic aggregation ([models.py:1158](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/gates/models.py:1158>), [models.py:1732](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/gates/models.py:1732>)).

Probes rejected forged keys, nested altered lineage, reorder, duplicate, and cross-report mutations. The original batch JSON remained byte-identical.

2. Detached re-stamping has no supported/public path.

The batch and aggregator are private (`_GateEvaluationBatch`, `_aggregate_report_gates`) and absent from package exports ([__init__.py:52](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/gates/__init__.py:52>)). Production call-site search found only the atomic evaluator path ([evaluator.py:585](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/gates/evaluator.py:585>)); recomputation delegates to it ([coverage.py:301](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/gates/coverage.py:301>).

A deliberately private direct import can still re-stamp stale results, but this is not a supported/public call path.

3. Public recomputation is correct.

`evaluate_report` under a new snapshot produced a new snapshot-bound key. The same-version raised-threshold spec recomputed to `BLOCKED` with threshold `2` and count `1`.

4. Prior evidence boundaries remain green.

Complete object matrices, distinct immutable lineage, raised B thresholds, parent immutability, A result-bearing derivation, B group/endpoint numerics, C registry-only sufficiency, conditional C fields, and override strictness all passed targeted and exact tests.

5. The two new regressions are meaningful.

The model-copy test captures the source batch JSON before attacks and compares against it afterward ([test_gate_evaluator.py:2238](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/tests/unit/test_gate_evaluator.py:2238>)); it is not a self-comparison after mutation.

The detached-result test checks the public package surface and exercises real `evaluate_report` recomputation for changed snapshots and same-version threshold changes ([test_gate_evaluator.py:2282](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/tests/unit/test_gate_evaluator.py:2282>).

## Remaining P2

Context-free `ReportGateResult.model_validate` still accepts an unknown same-report `unit_id`, because it has no `GateSpec` context ([models.py:797](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/gates/models.py:797>)). No authoritative production loader using this path was found. The internal aggregator performs spec membership validation ([models.py:1756](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/gates/models.py:1756>).

Counts: P0=0; P1=0; P2=1.

PASS; P0=0; P1=0
