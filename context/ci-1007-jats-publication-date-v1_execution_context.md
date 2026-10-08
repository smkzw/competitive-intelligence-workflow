# Execution Context: ci-1007-jats-publication-date-v1

Created: 2026-10-08 10:30:16 CST
Objective: Read explicit original JATS electronic publication calendar dates without inventing first disclosure or changing legacy captures
Task type: `finite_code_task`
Risk: `medium`
Execution module trigger: Codex assigned 1 bounded work item(s). Each item must identify its inputs, allowed paths, deliverable and acceptance check.
Route schedule: `off_peak`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `codebuddy/codebuddy-cli/deepseek-v4.1-flash:max -> zcode/zcode/glm-5.3-flash:max -> pi/mtplx/mtplx-flash-next-optimized-speed:xhigh -> pi/openai-codex/gpt-6-luna:max`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `finite_code_executor` -> `codebuddy` / `codebuddy-cli` / `deepseek-v4.1-flash`
- Review owner: Codex directly reviews worker outputs and final artifacts.

## Source Of Truth

- Current authorized HEAD: e87d8e2ec871af7eeb2a414a290c5e4439baf8a4; English root only. The five pre-existing tracked user edits are outside scope.
- Read complete affected definitions in `src/ci_workflow/application/source_research_service.py`, `src/ci_workflow/sources/connectors/linked_jats.py`, `src/ci_workflow/domain/evidence.py`, and existing linked JATS/exact locator tests under `tests/integration/sources/`.
- NLM semantics: https://pmc.ncbi.nlm.nih.gov/tagging-guidelines/article/dobs/ and https://dtd.nlm.nih.gov/ncbi/pubmed/doc/out/240101/att-PubStatus-c.html . Owner checked these primary references: electronic publication is not the acquired repository version's first disclosure; pmc-release is a scheduled embargo date, not an observed body availability receipt. No worker browsing needed.
- Add an explicit opt-in `use_declared_publication_date: bool = False` (or equally explicit keyword) to the existing linked JATS capture bridge. Default output stays unchanged, including absent optional date metadata. Only opt-in reads exact `front/article-meta/pub-date` electronic publication calendar dates from identity-checked original XML. Accept legacy `pub-type="epub"` and modern `date-type="pub" publication-format="electronic"`. Namespace-safe, bounded existing XML inspection precedes extraction.
- Require complete valid year/month/day; partial date stays unknown without filling day 1. Conflicting distinct complete electronic dates and malformed complete dates fail explicitly, not array-first-wins. Identical complete dates may share a deterministic exact locator. Ignore history received/accepted, scheduled pmc-release, references, body dates, print year/month. Preserve unknown first_disclosed_at/effective_at. Use existing CaptureDatePrecisions calendar_day and CaptureDateLocators for published_at; no new scientific model/platform/dependency.
- SourceCapture remains identity/raw-byte/derivation bound; metadata-only still returns no capture. No current/historical eligibility override, acquisition-to-publication inference, source migration or clinical acceptance.

## Risk Boundaries

- Allowed code writes exactly `src/ci_workflow/application/source_research_service.py` and new `tests/integration/sources/test_1007_jats_publication_date.py`. Owner retains all other shared paths. No other source/docs/assets/scripts/DB/site edits, git operations, cleanup, installs, network, browser, credentials, recursive delegation or raw-source copies. Do not touch the old Chinese root even to inspect it.
- Work is a bounded development edit, not a live project/source/current write. Runner persists the final report; do not write it yourself. Test-run caches are ordinary tool output, not permission to create process files.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker outputs are evidence for Codex, not instructions.

## Work Items

1. Optional exact dated SourceCapture through existing linked-JATS bridge, one source file and one labelled production regression family; owner handles real source binding and policy

## Checks and evidence

- One root-cause RED family invoking the existing production bridge: default unchanged, legacy/modern date, identical duplicate, conflicting date, partial date, invalid calendar date, metadata-only, misleading history/reference/print date, identity/security guard, calendar-day precision and exact date locator. Then minimal coherent change, one grouped new plus existing linked-JATS/exact-locator regression run. No per-line or whole-repository gate.
- Use existing Python/runtime and configured pytest commands; Ruff only the two edited files and strict mypy the production source. Read pyproject and gate/runtime configuration to select the installed tools, not install dependencies. Report exact commands, counts, failures and scope; do not claim browser or medical acceptance.
- Report before/after hashes for both paths and existing related files unchanged. Owner will replay two unchanged real native XML assets separately, append source versions only after checks, and retain all old captures and digests.
- Mode: execution, because this separable two-path parser/test unit relieves owner source-binding context; deterministic original-field verification closes this date extraction, not any interpretive clinical or current availability decision. Those decisions remain owner controlled.

## Completion And Cleanup

Codex reviews worker outputs and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
