VERDICT: FAIL

P0=0, P1=1, P2=0

Remaining finding:

- P1 — private alternate-directory helper is still used by production validation.
  - Evidence: [`page_registry.py:264`](</Users/smkzw/Documents/AI Products/competitive-intelligence-workflow/src/ci_workflow/reports/common/page_registry.py:264>) calls `_load_from_dir`; production validators call `PageRegistry.load`.
  - Direct runtime attack: production view validation invoked `_load_from_dir` once.
  - The public `root` parameter is removed and the helper is private/unexported, but the “unused by production validation” boundary is not met.
  - Smallest repair: separate the production frozen-catalog loader from the test-only `_load_from_dir` helper, so production validation never calls the alternate-directory helper.

Repaired findings verified:

- Row context is mandatory; unknown and cross-report pages are rejected.
- `PageRegistry.load(root=...)` is rejected; helper is unexported.
- Row-set digest changes for label, disclosure, page, and snapshot changes; ordering and serialization remain deterministic.
- Recomputed tampered exception identities are rejected.

Commands/results:

- New regression nodes: `8 passed`
- Complete Task 4.1 suites: `69 passed`
- Ruff: passed
- mypy: `Success: no issues found in 5 source files`
- Package verification: `PACKAGE_OK`
- Direct attacks: all specified attacks passed except the helper-use boundary above.

No files were modified.
