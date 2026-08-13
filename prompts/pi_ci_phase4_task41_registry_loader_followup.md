Continue the same Phase 4 Task 4.1 Pi execution session. Do not restart or redesign. One P1 remains after the second isolated review.

Hard boundaries:

- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Preserve unrelated changes; do not commit.
- Modify only `src/ci_workflow/reports/common/page_registry.py` and the smallest relevant tests under `tests/unit/reports/` or `tests/contract/`.
- Do not implement later renderer/UI work or security testing.
- Runner-managed output path: `runs/pi_ci_phase4_task41_registry_loader_followup.md`. Return the handoff and do not write that report path directly.

Read these files only:

- `AGENTS.md`
- `src/ci_workflow/reports/common/page_registry.py`
- `src/ci_workflow/reports/common/__init__.py`
- `tests/unit/reports/test_view_model.py`
- `tests/contract/test_page_catalogs.py`

Remaining defect:

`PageRegistry.load()` is the production frozen-catalog loader, but it still calls `_load_from_dir`, the same alternate-directory test helper. An isolated verifier monkeypatched that helper and observed production view validation invoking it. Therefore the promise that the alternate-directory helper is unused by production validation is not mechanically true.

Repair with the smallest clear separation:

- production `PageRegistry.load()` must load only its internally resolved frozen source/package catalogs through a dedicated production-private path;
- the test-only alternate-directory helper must be a distinct private method/path and must never be called by `load()` or production validators;
- avoid duplicating parsing/validation semantics if possible, but do not route production through the test override point;
- add an exact regression test that monkeypatches the alternate-directory helper to raise and proves `PageRegistry.load()` plus a public production validator still work from the frozen catalogs;
- keep the helper unexported and caller-selected roots rejected.

Run the new node RED then GREEN, all Task 4.1 tests, Ruff, mypy strict, package verify, and full pytest. Explain the concrete call separation and provide results. Do not commit.
