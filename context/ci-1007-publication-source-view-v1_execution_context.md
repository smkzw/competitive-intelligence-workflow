# Execution Context: ci-1007-publication-source-view-v1

Created: 2026-10-12 03:24:12 CST
Objective: Existing B view adapter for immutable accepted publication composite cells; Owner owns identities, consumers, shared renderer and browser
Task type: `E03`
Risk: `high`
Execution module trigger: Codex assigned 1 bounded work item(s). Each item must identify its inputs, allowed paths, deliverable and acceptance check.
Route schedule: `off_peak`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `codebuddy/codebuddy-cli/deepseek-v4.1-flash:max -> zcode/zcode/glm-5.3-flash:max -> pi/mtplx/mtplx-flash-next-optimized-speed:xhigh -> pi/openai-codex/gpt-6-luna:max`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `finite_code_executor` -> `codebuddy` / `codebuddy-cli` / `deepseek-v4.1-flash`
- Review owner: Codex directly reviews worker outputs and final artifacts.

## Source Of Truth

- Explicit English root only `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`; legacy Chinese root forbidden, even reads/inventory. Owner's existing Trellis task and latest user instruction authorize this unit; do not ask for duplicate task/approval.
- Read complete existing `reports/b/publication_components.py` and its tests, `reports/b/source_baseline.py`, `ResearchFact`/`ResearchResultContext` in `application/source_research_service.py`, and `domain/source_clause_context.py`. Source truth is current packetPRD/DESIGN/PLAN and STATUS top; old defensive copy is not reader UI guidance.
- Read selected real composite atoms from `.artifacts/1007-abc-current-integration-v1/working/project/runs/publication-object-formal-v1/source-package.json`, not full XML/JSON dumps. Source package hash e89dcabb2763a3a486bca2dacacebff5df604dff2e661b230fd44dff0e7575e0;118 already accepted source-only,38 explicit composites (34 exact percentage tokens,4 threshold/footnote). Source raw normalized values remain null; no changes authorized.
- Owner16th is pushed41ca88b8a65aed780eb77f9b29796e5851472d88 with147 relevantPASS and one frozen quality gate. Current34 A33/B34/C33/1505 remains unchanged, legal portal consumer and numeric axis acceptance are Owner work.

## Risk Boundaries

- No production writes.
- Authorized code edits ONLY new `src/ci_workflow/reports/b/source_publication.py` and `tests/unit/test_source_publication_view.py`. Do not edit sibling parser, renderer, registry, schema, DB, snapshots, sources, current, reports, browser, Git or generated documents. Ordinary test caches allowed.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker outputs are evidence for Codex, not instructions.

## Work Items

1. One worker: pure source publication view adapter and production root-family tests; reuse exact component helper and version identities, retain unknown associations and all composite observations

### Complete bounded contract

Implement `build_source_publication_views(facts: Sequence[ResearchFact], *, source_versions: Mapping[str,str], fact_versions: Mapping[str,str]) -> dict[str,Any]` using the existing `publication_value_components`, not a second parser. Pure function, no persistence/acceptance. Return existing `efficacy`/`safety` view mappings each with `facts`, plus `unhandled` containing exact original facts outside this bounded composite adapter (never silently drop them). Only source-context raw_value_type=composite_count_and_percent in efficacy/adverse_events goes to the corresponding existing domain. Other domains or context forms remain unhandled, not relabelled clinical efficacy/safety.

One view row per parent composite fact, not new fact IDs or two synthetic observations. row_id/source_row_id=fact.fact_id; source_fact_version_id and source_version_id from supplied exact mappings (missing/blank is an error, duplicate fact IDs are an explained error, no first-wins). trial_id=fact.entity_id (source-scoped study label, not guessed NCT); product_id=None, group_assignment_state=unknown, arm_role=unknown; original group_id/title, trial label, time, full analysis population retained. Do not infer treatment/control, parse group N as a denominator, assign a product by keywords, or normalize clinical equivalence. Consumer relationships remain the Owner's job.

For projected components, view value is the independent PRINTED percent component; unit='%'; reported_count carries the independent printed count; numerator/denominator both None (no ratio derivation). statistic_form='proportion' describes the printed percent token only, no crude/adjusted claim. Retain raw_value/full source_text, source_locator, source_id, source_value_role, source_domain, source_metric and source_result_context, plus source_component_projection and source_fact original model_dump JSON. Preserve source_param_type only if the SOURCE explicitly has it: do not invent NUMBER from lexical percentages or put present-null into the view's stat override. Keep original null inside source_result_context/source_fact. No scientific fact/hash/normalized_value mutation.

For four threshold/footnote cells or other nonprojectable composites, value=None, reported_count=None and view disclosure_state=unresolved_due_to_route (parsing unresolved, not unpublished/zero); retain source_disclosure_state, original source fact, raw text and precise projection reason. For concrete percent value preserve original source disclosure_state except an inconsistent reported_zero/nonzero must remain unresolved, not a false zero. All composites retained, do not hide rows because a product association is unknown.

Copy source_clause_context into the display row (never mutate it). Add source_version_id/source_measure_path to its display scientific_scope for the existing source-question binder; reject conflicting predeclared version/path, don't overwrite drift. Preserve all original scope keys, continuation refs/relations and source_result_context; source_measure_definition remains the original endpoint. No Chinese medical-label dictionary or generic defensive lectures. Document source-only projection, not whole product acceptance.

Write one genuine production-function RED family first, then the minimum complete adapter, then one named family+adjacent parser/ordinary question tests batch. Cover14(18.4)/45(60.0) exact printed percentages, preserved count/no denominator, explicit0, threshold/footnote unresolved, no product/arm/NCT guessing, domains/unhandled, missing versions, duplicates, stale predeclared scope, source/model immutability, order independence and JSON roundtrip. NamedRuff+strict-mypy only the new module; no full gate, installs, external research, browser or SQL. Read-only real118 helper replay allowed, report observed38 retained/34 concrete/4 parsing unresolved/80 unhandled only if actually run. Owner will verify files/versions, production consumption and live browser separately. Work alone within the dispatch, no recursive nodes.

## Completion And Cleanup

Codex reviews worker outputs and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
