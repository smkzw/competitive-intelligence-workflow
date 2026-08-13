Continue the SAME independent Cursor/Grok reviewer session `91cbac3e-56b0-4ec7-bd62-08440bac1b71`. The implementation has changed after your FAIL. Do not read worker/other reviewer reports and do not edit source.

Hard boundaries:
- Work only in `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Read these files only: previously authorized Task 3.6 sources/tests/context/plan plus the current diff since your review.
- Write exactly one output file: `runs/conference/ci_phase3_task36_acceptance/cursor_resume_reverify.md`; runner-owned, return it and do not write it with tools.
- Read-only, no network/visual/security/clinical-content work.

Re-test or source-verify the P1/P2 findings from your prior review against the current tree, especially:
1. first valid no-draft A run then CLI/fresh-context unchanged-input `--resume`;
2. current run reuse events, terminal decision event, checkpoint, `reused_artifacts` hashes/mtime and tamper rejection;
3. failed-input then canonical input appears, CLI resume; changed evidence on terminal blocked state must fail with explicit reopen guidance;
4. schema-invalid fixture rejection, expected-outcome enforcement and stale docs.

Packaging boundary is now explicit: Task 3.6 verifies new Python wheel members only; the plan's Task 9.5 owns the installable full bundle with schemas/policies/migrations/assets/fixtures. Do not count the known bare-wheel data omission as Task 3.6 P1 unless current Task 3.6 source newly worsens that boundary; retain it as a mandatory Task 9.5 verification item.

Return a complete revised verdict `PASS` or `FAIL` with P0/P1/P2 counts, commands/evidence, and any minimal remaining remedy. Codex is final authority.
