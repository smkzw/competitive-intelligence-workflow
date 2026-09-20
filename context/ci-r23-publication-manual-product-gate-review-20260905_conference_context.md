# Conference Context: ci-r23-publication-manual-product-gate-review-20260905

Created: 2026-09-05 18:07:12 CST
Objective: 独立审阅 R2.3 Publication 与人工补件产品门实现：核查正式 verdict 唯一权威、两策略获取、独立复核绑定、单快照单次用户响应、多报告局部暂停、原地补件处理、不可得分流及证据不足终态；只读审阅并输出可执行缺陷清单，不修改文件，不宣称最终验收。
Task type: `high_risk_contradiction_review`
Risk: `high`
Conference mode: `serial`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

- Ordinary tasks remain Codex-direct. Chinese labels or Chinese sentence work uses its declared execution route and does not start a conference.
  - This packet uses one Codex-led conference object (`evidence_single_object`) with no sub-venue chair. Its effective `CST` route chain is `xai/grok-4.6:high -> xai/grok-4.6:high -> openai-codex/gpt-6-astra:low`; the packet branch is recorded at creation and filtered against the actual execution route nodes recorded below. Before a new session, the runner rechecks the Beijing period; an already-started session is never rerouted.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Execution-Conference Model Deduplication

- Linked execution task: `ci-r23-publication-manual-product-gate-20260905`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `cursor/default`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- `.trellis/tasks/09-05-r23-publication-manual-product-gate/{prd.md,design.md,implement.md,checkpoint_20260905_p1_audit.md}`
- `src/ci_workflow/domain/publication.py`
- `src/ci_workflow/domain/research_package.py`
- `src/ci_workflow/ingestion/publication_gate.py`
- `src/ci_workflow/ingestion/manual_inbox.py`
- `src/ci_workflow/application/publication_manual_gate.py`
- `src/ci_workflow/application/research_package_submission.py`
- `src/ci_workflow/application/run_service.py`
- `src/ci_workflow/cli.py`
- `schemas/research-package.schema.json`, `package-manifest.json`, `schemas/package-manifest.schema.json`
- `tests/integration/test_v13_publication_gate.py`, `tests/contract/test_v13_intake_package.py`, `tests/integration/test_multi_report_product_run.py` and existing manual-inbox tests.
- Current deterministic evidence: focused chain `38 passed`, all integration `510 passed`; first full gate had Ruff and strict mypy green, 940/941 active tests green, and one now-corrected CLI catalog expectation drift.
- Do not add production paths unless the user explicitly authorized reading them for this task.

## Scope

- In scope: read-only code/contract/test review of R2.3, including negative-path adequacy and whether product outcomes are honest.
- Out of scope: edits, internet research, rendered portal visual acceptance, unrelated legacy/PDF/PPT code, and final release acceptance.

## Success Criteria

- Each selected primary route returns an auditable output or an explicit health/fallback reason.
- The prompt uses the correct Agent identity, provider/model, effort, tools-enabled policy, and same-session continuation policy.
- The runner records session, usage/tool observations, fallback decisions, and failure reasons without `--max-turns 1`.
- No production path is read or modified; Codex retains final acceptance.
- Findings cite exact files/lines or reproducible commands; severity distinguishes correctness defects from future enhancements.

## Parallel Work Rule

For logic-heavy, rigor-sensitive, or artifact-heavy tasks, each participant independently runs the whole bounded workflow and writes a separate output. Leads compare after all available participant outputs are in or explicitly marked pending.

## Timeout Policy

- Participant soft wait: 60 minutes.
- Large-task participant wait: 120 minutes.
- Chair hard wait: 120 minutes.
- Failure rule: Do not fail a model for slow response alone; fail only on terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no useful progress after the high-budget same-session recovery loop. A catalog/auth/transport health preflight timeout or malformed response is diagnostic and must still allow one live route attempt; explicit user routes also proceed when the catalog is stale or incomplete, while a genuinely missing CLI or native transport boundary may block. If a resumable session exists after a step/size boundary, continue it before fallback; repeated identical output/tool evidence triggers the no-progress breaker.
- Pass/turn boundary: one conference prompt is one conference pass. The
  `--max-turns` value controls internal Agent tool-calling turns and is never
  set to 1 for substantive conference execution; generated participant and
  chair commands use the route budgets recorded by the guard.

## Risk Boundaries

- External Agents are advisory; Codex remains final authority.
- Codex owns visual/browser/PPT/PDF/rendered checks, live authority checks, final clinical/regulatory conclusions, and production writes.
- Do not mark a slow model failed solely due to latency.

## Loop Log

- 2026-09-05 18:07:12 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
