# Conference Context: ci-r24-gatespec-blocker-closure-review-20260906

Created: 2026-09-05 19:59:16 CST
Objective: 独立挑战 R2.4 GateSpec、恢复信息增益、blocker/no-draft 闭包：核对当前实现与测试是否仍存在可导致科学假绿、候选删减、终态无机器审计或下游残留的 P0/P1；新鲜度模型、阈值和历史截止日语义仅列出风险，不替用户裁决
Task type: `code_open_audit`
Risk: `high`
Conference mode: `serial`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

- Ordinary tasks remain Codex-direct. Chinese labels or Chinese sentence work uses its declared execution route and does not start a conference.
  - This packet uses one Codex-led conference object (`general_single_object`) with no sub-venue chair. Its effective `CST` route chain is `zcode/glm-5.3-flash:max -> opencode-go/muse-spark-1.3-contributor:xhigh -> codebuddy-cli/deepseek-v4-flash:max -> openai-codex/gpt-5.6-sol:medium`; the packet branch is recorded at creation and filtered against the actual execution route nodes recorded below. Before a new session, the runner rechecks the Beijing period; an already-started session is never rerouted.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Execution-Conference Model Deduplication

- Linked execution task: `ci-r24-gatespec-blocker-closure-20260905`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `cursor/default`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.3.md` 第 5.4、5.5、6 节。
- `plans/codex_execution_ci-rebaseline-rebuild-v3.md` R2.4。
- `.trellis/tasks/09-05-r24-gatespec-blocker-closure/{prd,design,implement,checkpoint_20260906_p3_p5}.md`。
- `reviews/codex_execution_ci-r24-gatespec-blocker-closure-20260905_review.md` 与三个 runner
  持久化 worker 报告；这些是审计输入，不是自动正确的权威。
- 当前实现与测试：`src/ci_workflow/{gates,domain,application,capabilities,sources}` 中 R2.4
  相关文件、A/B/C GateSpec YAML、schema、fixture 与测试。

## Scope

- In scope: 只读独立挑战当前 R2.4 字节，寻找仍可造成科学假绿、候选删减、终态无机器
  审计、恢复伪造或 blocker 后下游残留的 P0/P1，并评价现有负向测试是否真正命中产品边界。
- Out of scope: 修改仓库；重复实现；门户视觉；外部检索；真实药智/三宿主/24 门户；替用户
  决定新鲜度模型、阈值或历史截止日语义；宣称 RC 或发布接受。

## Success Criteria

- Each selected primary route returns an auditable output or an explicit health/fallback reason.
- The prompt uses the correct Agent identity, provider/model, effort, tools-enabled policy, and same-session continuation policy.
- The runner records session, usage/tool observations, fallback decisions, and failure reasons without `--max-turns 1`.
- No production path is read or modified; Codex retains final acceptance.
- 对每项 P0/P1 给出精确文件/合同锚点、可复现绕过或足够具体的反例；若未发现，明确说明
  审阅范围和残余不确定性。
- 区分已被当前字节闭合的 worker 历史发现与仍开放问题，不因旧报告中的 TODO 误判现状。

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

- 2026-09-05 19:59:16 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
