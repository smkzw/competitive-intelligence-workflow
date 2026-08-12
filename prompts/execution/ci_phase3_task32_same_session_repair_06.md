You are Pi continuing the existing Task 3.2 implementation session `019ff262-8ff4-7000-8709-4589a92be55c` with provider/model `opencode-go/deepseek-v4-flash:max`.

## Hard boundaries

- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- This is a narrow Task 3.2 repair. Do not enter Task 3.3, do not modify Task 3.1 contracts, and do not broaden into Phase 3 graph work.
- Do not commit. Do not edit Trellis, acceptance records, context, runs, reviews, metrics, prompts, design, plan, package manifest, or runner-managed reports.
- Allowed edits only:
  - `src/ci_workflow/gates/exhaustion.py`
  - `src/ci_workflow/gates/blocker_audit.py`
  - `schemas/blocker-audit.schema.json` only if the public contract truly needs a schema change
  - the four Task 3.2 integration test files.
- Do not perform security testing. Preserve native Chinese clinical user wording and zero-draft behavior.
- Runner-managed report path: `runs/execution/ci_phase3_task32_implementation/worker_01.md`. Never write it with tools; return a complete execution report for the runner.

Initial read set:

- `AGENTS.md`
- `context/ci_phase3_task32_context.md`
- `context/ci_phase3_task32_final_audit01_plan_excerpt.md`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md`
- `src/ci_workflow/gates/exhaustion.py`
- `src/ci_workflow/gates/blocker_audit.py`
- `src/ci_workflow/sources/retries.py`
- `tests/integration/test_double_exhaustion.py`
- `tests/integration/test_no_draft_when_blocked.py`
- `tests/integration/test_no_draft_on_unresolved_key_conflict.py`
- `tests/integration/test_no_draft_after_scientific_qc_rejection.py`

## Confirmed failures to repair

Codex independently reproduced all of the following against the current tree. Treat these as RED contracts, not suggestions.

1. A scientific gap accepts two `GapRouteEvidence` rows with the same `route_id`; the second can carry a phantom receipt and `attempt_count=99`. Require exactly one route summary per applicable route. A route summary contains multiple receipt IDs; duplicate route rows are invalid.
2. `GapRouteEvidence.final_result_class` is caller-supplied. A scientific route whose actual receipts are all `not_found` accepts `content_acquired`; a technical route whose actual receipts are all `content_acquired` accepts `rate_limited`. Derive and compare the final class from actual receipts. Use one deterministic terminal-receipt rule documented in code (chronologically latest `ended_at`, then stable tie-breakers is acceptable). Do not impose the scientifically wrong rule that every scientific route must end `not_found`: successfully acquired content can legitimately omit the needed field. For a technical `ACCESS_BLOCKED` route, the derived terminal class must be one of `TECHNICAL_RESULT_CLASSES`.
3. An A empty-universe public write accepts `EvidenceGap.gate_spec_id=gate-spec-b-v1` and a B field. In the empty branch, require the single eligibility gap's `evidence_gap.gate_spec_id == spec.spec_id` and `field_id == empty_universe.eligibility_gate_unit_id()`.
4. B/C empty-universe writes accept `snapshot=None`. Require B/C to bind a closed `ApplicableUniverseSnapshot`; keep A's true-zero-product path at `snapshot=None`. B/C candidate product/trial sets must remain exact matches to the snapshot.
5. `EmptyUniverseEvidence` calculates exclusion receipts from only `gaps[0]` while allowing extra gaps. An empty-universe evidence record must contain exactly one eligibility gap; bind its `gate_unit_id`, `object_id == search_scope_id`, and state to the scientific-absence states valid for an empty search, then require exclusion receipt IDs to cover that gap exactly. Do not silently ignore extra gaps.

## TDD and verification

Add one focused negative test per failure family before changing production code. At minimum include:

- duplicate scientific route summary rejected;
- scientific final class inconsistent with actual receipts rejected;
- technical `ACCESS_BLOCKED` route with successful terminal receipt rejected;
- A/B/C empty path rejects cross-report `gate_spec_id` and wrong eligibility `field_id`;
- B/C empty path rejects missing snapshot, while A true-zero path still passes;
- empty evidence rejects a second gap and mismatched search-scope object.

Use the public model/builder entry points and preserve existing positive cases. Then run:

```bash
mkdir -p /tmp/ci32-r6
TMPDIR=/tmp/ci32-r6 .venv/bin/pytest tests/integration/test_double_exhaustion.py tests/integration/test_no_draft_when_blocked.py tests/integration/test_no_draft_on_unresolved_key_conflict.py tests/integration/test_no_draft_after_scientific_qc_rejection.py -q -p no:cacheprovider
TMPDIR=/tmp/ci32-r6 .venv/bin/pytest tests/unit/test_gate_evaluator.py tests/reports/test_report_specific_gates.py tests/reports/test_gate_override_strictness.py -q -p no:cacheprovider
TMPDIR=/tmp/ci32-r6 .venv/bin/pytest -q -p no:cacheprovider
.venv/bin/ruff check <changed Python files>
.venv/bin/mypy --strict src/ci_workflow/gates/exhaustion.py src/ci_workflow/gates/blocker_audit.py
git diff --check
```

Also rerun the three confirmed `/tmp` attacks or equivalent one-process attacks and report that each now fails closed. If an existing fixture conflicts with the deterministic terminal rule, fix the fixture only after proving the source receipt chronology and intended final class; do not weaken the rule to make tests green.

## Required output

Return a complete execution report with boundary check, files changed, RED evidence, implementation, exact commands/results, failed paths and root cause, residual uncertainty, and next recommendation. Do not claim acceptance or commit authority.
