Active task: .trellis/tasks/08-12-phase-3-evidence-gates-recovery

You are the same independent Codex subAgent acceptance reviewer for Task 3.1, continuing session `019ff27d-3370-7202-92ce-003822c8d38e` with model `gpt-5.6-luna` and effort `max`. Preserve verifier isolation: read the current artifacts and acceptance criteria, run read-only checks, and do not edit or repair. Your previous verdict was `FAIL; P0=2; P1=0; P2=1`; reassess only after independently verifying the current tree.

Hard boundaries:

- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Read-only review. Do not modify source, tests, policies, schemas, Trellis state, acceptance records, or any prior runner report.
- Do not perform security testing. Test functional evidence integrity: report results must belong to the current evidence snapshot and current rule content.
- Runner-managed output path: `runs/codex-subagent_ci_phase3_task31_acceptance_followup4.md`. Do not write it through tools.
- The context-free `ReportGateResult` membership limitation remains a documented P2 unless you find a current authoritative loader path that accepts it without `GateSpec` validation.

Read these files only:

- `runs/codex-subagent_ci_phase3_task31_acceptance_followup3.md`
- `context/ci_phase3_task31_pause_2026-08-12.md`
- `runs/execution/ci_phase3_task31_implementation/worker_02_followup_05.md`
- `runs/execution/ci_phase3_task31_implementation/manager_followup_04.md`
- `.trellis/tasks/08-12-phase-3-evidence-gates-recovery/implement.md`
- `docs/decisions/0011-phase-3-evidence-gates-and-recovery.md`
- `src/ci_workflow/gates/models.py`
- `src/ci_workflow/gates/evaluator.py`
- `src/ci_workflow/gates/coverage.py`
- `src/ci_workflow/gates/__init__.py`
- `tests/unit/test_gate_evaluator.py`
- `tests/reports/test_report_specific_gates.py`
- `tests/reports/test_gate_override_strictness.py`

Acceptance questions:

1. Is a Pydantic `model_copy` forged batch key or nested altered unit-result lineage rejected at the actual internal aggregation entry, independent of initial constructor validation?
2. Is there any supported/public call path that accepts detached `unit_results` from spec/snapshot A and re-stamps them as spec/snapshot B? Search production and package exports, not just the new tests.
3. Does the supported `evaluate_report(spec, snapshot, bindings, contract_version=...)` path recompute under a new evidence snapshot and a same-version rule whose threshold/content changed?
4. Do coverage recomputation, complete object matrix, distinct fact lineage, threshold enforcement, A/B/C evidence semantics, and parent immutability remain intact?
5. Are the two new exact regressions meaningful and non-tautological after Codex corrected the source-batch byte comparison?

Codex independently observed on the current tree:

- the two named attacks: 2 passed;
- Task 3.1 exact trio: 143 passed;
- full suite: 331 passed;
- Ruff, strict mypy, package verify, public API probe, and `git diff --check` passed.

Run the smallest decisive checks plus any adversarial probes needed to answer the questions. Record sources read, call-site searches, commands and real outputs, failures/uncertainty, and P0/P1/P2 counts. Finish with exactly one verdict line: `PASS; P0=0; P1=0` or `FAIL; P0=<n>; P1=<n>`. Do not claim task completion or write acceptance records.
