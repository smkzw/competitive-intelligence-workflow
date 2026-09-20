# Conference Context: ci-r2-bc-science-acceptance-20260905

Created: 2026-09-05 05:12:43 CST
Objective: 独立审查 B/C fresh research package 到 evidence ingestion、确定性 GateSpec、不可变 report snapshot、独立科学复核绑定和候选 HTML 渲染的真实链路；重点挑战来源/事实/声明闭包、B 门户投影是否可改写医学事实、单臂安全性语义、C endpoint+timepoint 完整性、自我复核禁令、快照幂等及 rendered_unreviewed 边界。仅作审查，不修改代码，不宣称 R2/RC 完成。
Task type: `complex_delivery_conference`
Risk: `high`
Conference mode: `serial`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

- Ordinary tasks remain Codex-direct. Chinese labels or Chinese sentence work uses its declared execution route and does not start a conference.
  - This packet uses one Codex-led conference object (`general_single_object`) with no sub-venue chair. Its effective `CST` route chain is `codebuddy-cli/deepseek-v4-flash:max -> grok-build/grok-4.6:medium -> cursor/cursor-grok-4.6:medium -> openai-codex/gpt-5.6-luna:max`; the packet branch is recorded at creation and filtered against the actual execution route nodes recorded below. Before a new session, the runner rechecks the Beijing period; an already-started session is never rerouted.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Execution-Conference Model Deduplication

- Linked execution task: `ci-r2-bc-research-package-wiring-20260905`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `zcode/glm-5.3-flash`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.3.md`, especially §§3, 5, 6, 8, 9.
- `plans/codex_execution_ci-rebaseline-rebuild-v3.md`, R2.2--R2.4 and R3.2--R3.4.
- `reviews/codex_conference_ci-rebaseline-r2-science-review-20260905_review.md`.
- `src/ci_workflow/application/fresh_research_ingestion.py`.
- `src/ci_workflow/application/fresh_b_research_package.py` and
  `src/ci_workflow/application/fresh_c_research_package.py`.
- `src/ci_workflow/application/run_service.py` and B/C renderer snapshot bindings.
- `policies/gates/B-v1.yaml`, `policies/gates/C-v1.yaml`, and shared gate evaluator/models.
- Focused B/C tests and the current full-gate result recorded in the execution review.
- Do not add production paths unless the user explicitly authorized reading them for this task.

## Scope

- In scope: read-only code and contract audit; adversarial trace of B/C evidence
  lineage; deterministic gate and snapshot identity; independent reviewer
  identity/digest; portal projection fidelity; state-label correctness;
  actionable P0--P3 findings with exact file/line evidence.
- Out of scope: source edits, browser visual acceptance, external research,
  R2/RC/release approval, A-path redesign, PDF/PPT, old-workspace access.

## Success Criteria

- Each selected primary route returns an auditable output or an explicit health/fallback reason.
- The prompt uses the correct Agent identity, provider/model, effort, tools-enabled policy, and same-session continuation policy.
- The runner records session, usage/tool observations, fallback decisions, and failure reasons without `--max-turns 1`.
- No production path is read or modified; Codex retains final acceptance.
- Every material finding names the violated contract, counterexample, impact,
  and smallest safe remediation; absence of findings must be evidence-backed.

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

- 2026-09-05 05:12:43 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
