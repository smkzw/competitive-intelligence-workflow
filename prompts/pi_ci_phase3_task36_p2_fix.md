Continue the SAME Pi/DeepSeek implementation session `019ff827-34f5-7000-8c80-47705eb9c191`. P0/P1 are now zero, but independent re-verification found three functional P2 consistency defects that must be closed before Task 3.7. Preserve the current accepted behavior.

Hard boundaries:
- Work only in `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Read these files only: `AGENTS.md`; current Task 3.6 context/plan and current dirty Task 3.6 source/tests plus directly wired event/graph/blocker helpers. Do not read reviewer/worker reports.
- Authorized edits only Task 3.6 source/tests/CLI if needed. No specs/plans/Trellis/package architecture/unrelated files.
- Do not commit/stage. No network/visual/security/clinical-content work.
- Write exactly one output file: `runs/pi_ci_phase3_task36_p2_fix.md`; runner-owned, return it and do not write with tools.

Fix with behavior-level RED then GREEN:

1. Pre-resume blocker drift must fail closed.
- A preserved terminal decision must compare current blocker files to the artifact tuple bound by the original/current terminal-decision event that first established the decision (path/SHA/bytes/mtime as appropriate). Do not adopt a file modified before resume as the new reusable truth merely because it was in the pre-run baseline.
- Add a test: first valid fixture, modify `audit.md`, then `project run --resume`; exit 2 with concise Chinese restore/reopen guidance, no new accepted manifest/decision, and no claim of evidence result. Restore and normal resume passes.

2. Never trust cached `RunContext.universe_evidence`.
- Whenever a bound universe path exists, parse/hydrate from current file bytes unconditionally before terminal digest checks and handler use. Reusing the same `RunContext` object after changing the file must not certify the old digest. On terminal blocked state, changed evidence fails with explicit reopen guidance before dispatch.
- Add exact API regression using the same context object.

3. Project/report state consistency on fail-then-resume.
- When run 1 already bootstrapped project `running` then failed universe, and run 2 produces report `evidence_blocked`, persist a current-run valid project `running -> blocked` transition. Do not depend on bootstrap happening in the same run. Use persisted current state and declared transition contract; do not catch strings or broad exceptions.
- EX02 run 2 must assert project family reaches blocked under the second run. Terminal unchanged resume must not repeat that transition.

4. User-facing exception mapping.
- Wrap expected blocker package drift/integrity exceptions from the Task 3.2 writer into a typed `ContractConfigError` or `RunError` so CLI returns a defined nonzero code and Chinese guidance, never traceback. Add focused test if current paths can reproduce it without artificial internal monkeypatching.

Do not expand fixture idempotence or Task 9.5 packaging in this round. Run exact suite, CLI regressions, full suite, Ruff, strict mypy and real fixture->resume including pre-drift and stale-context probes. Clean task artifacts. Return compact report with exact counts and remaining uncertainty. Codex is final authority.
