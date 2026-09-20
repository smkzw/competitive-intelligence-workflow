# Conference Context: ci-phase9-task93-optional-monitoring-review

Created: 2026-09-01 03:56:41 CST
Objective: 独立审查 Task 9.3 当前实现：候选是否可能越权成为事实或触发发布，去重与 model_copy 防漂移是否可靠，技术失败/未发现/未公开是否真实区分，用户处置和刷新交接是否只读且可恢复，监测是否可卸载，中文提示是否面向医学经理。只给出可复现问题与通过条件，不修改代码。
Task type: `complex_delivery_conference`
Risk: `medium`
Conference mode: `serial`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

- Ordinary tasks remain Codex-direct. Chinese labels or Chinese sentence work uses its declared execution route and does not start a conference.
  - This packet uses one Codex-led conference object (`general_single_object`) with no sub-venue chair. Its effective `CST` route chain is `codebuddy-cli/deepseek-v4-flash:max -> zcode/glm-5.3-flash:max -> grok-build/grok-4.6:medium -> cursor/cursor-grok-4.6:medium -> openai-codex/gpt-5.6-luna:max`; the packet branch is recorded at creation and filtered against the actual execution route nodes recorded below. Before a new session, the runner rechecks the Beijing period; an already-started session is never rerouted.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Execution-Conference Model Deduplication

- Linked execution task: `ci-phase9-task93-optional-monitoring`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `zcode/glm-5.3`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §17.3。
- `.trellis/tasks/09-01-phase-9-task-93-optional-monitoring/`。
- Task 9.3 当前源码、合同/集成/图测试与三份执行报告。
- 不读取或修改生产路径。

## Scope

- In scope: 监测候选合同、去重、事件与投影恢复、诊断、用户处置、只读刷新交接、可卸载性与中文提示。
- Out of scope: 宿主调度适配、事实接纳、正式快照、报告发布、HTML/PDF/PPT 生成与安全测试。

## Success Criteria

- Each selected primary route returns an auditable output or an explicit health/fallback reason.
- The prompt uses the correct Agent identity, provider/model, effort, tools-enabled policy, and same-session continuation policy.
- The runner records session, usage/tool observations, fallback decisions, and failure reasons without `--max-turns 1`.
- No production path is read or modified; Codex retains final acceptance.

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

- 2026-09-01 03:56:41 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
