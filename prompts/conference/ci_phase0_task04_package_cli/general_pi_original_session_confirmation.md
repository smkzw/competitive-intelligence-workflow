You are Pi continuing the original conference session `019fefba-eb43-7000-8356-de4cd0f7b6b5` on its already-established effective route `cms-smk/cms-model`.

Hard boundaries:
- Work read-only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Do not read other participant outputs or edit project files.
- Runner-managed output path: `runs/conference/ci_phase0_task04_package_cli/general_pi_original_session_confirmation.md`. Never write that report path with tools; return the complete report and let the runner persist it.

Read these files only:
- `context/ci_phase0_task04_package_cli_conference_context.md`
- `schemas/package-manifest.schema.json`
- `src/ci_workflow/cli.py`
- `tests/contract/test_package_manifest.py`
- `tests/integration/test_cli_help.py`
- `tests/integration/test_cli_command_catalog.py`

Task:
This is a targeted same-session closure of the defects you reported earlier. Run the four focused Task 0.4 tests and `uv run ci-workflow package verify --root .`. Confirm: exact six-command schema, seventh-command rejection, `$skill-id` runtime rejection, deferred exit exactly 3, and Chinese-native help/error. Apply the context's approved Task 0.4 versus Task 9.5 bundle boundary. Return only `# Original-session closure`, `## Evidence`, `## Verdict`, with P0/P1 counts. PASS requires P0=0 and P1=0.
