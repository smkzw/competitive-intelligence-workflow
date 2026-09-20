# Conference Context: ci-phase10-task101-acceptance-matrix

Created: 2026-09-01 12:22:13 CST
Objective: 治理关联复核：确认 Task 10.1 已完成准确 18 个 required-v12、23-case catalog、HTML-only、摘要闭合、future-owner 状态、候选包纳入、测试与 Trellis 同步，且没有把未来 fresh-source、RC、恢复或旧根处置提前关闭。
Task type: `long_horizon_code`
Risk: `medium`
Conference mode: `serial`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

- Ordinary tasks remain Codex-direct. Chinese labels or Chinese sentence work uses its declared execution route and does not start a conference.
  - This packet uses one Codex-led conference object (`general_single_object`) with no sub-venue chair. Its effective `CST` route chain is `cursor/default -> opencode-go/muse-spark-1.2-contributor:xhigh -> cms-router/minimax-m3:xhigh -> google-antigravity/gemini-3.7-flash:high`; the packet branch is recorded at creation and filtered against the actual execution route nodes recorded below. Before a new session, the runner rechecks the Beijing period; an already-started session is never rerouted.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Execution-Conference Model Deduplication

- Linked execution task: `ci-phase10-task101-acceptance-matrix`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `openai-codex/gpt-5.6-luna`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- `../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` Task 10.1（批准的 18 族、子场景和责任阶段）。
- `.trellis/tasks/09-01-phase-10-task-101-acceptance-matrix/`（已完成的任务合同、实施勾选和恢复检查点）。
- `docs/decisions/0013-site-first-v1-delivery-scope.md`（首版 HTML-only）。
- `fixtures/acceptance/catalog.yaml`、`fixtures/acceptance/required-v12/`、`schemas/acceptance-catalog.schema.json`、`tests/acceptance/test_fixture_catalog.py`、`docs/acceptance/matrix.md`。
- `tools/bundle_contract.py`、`tests/hosts/test_fresh_install.py`（验收目录随候选包交付的闭合证据）。
- 执行 review/metrics 与此前同一 Pi/Cursor 会话的两轮独立审阅输出；模型输出只作证据。

## Scope

- In scope: 只读治理关联复核；确认 Task 10.1 当前合同、测试、Trellis 和执行证据一致，未来责任未提前关闭。
- Out of scope: 修改文件、fresh-source、最终 RC、恢复演练、E1 实施、旧根处置、PDF/PPT、生产写入和安全专项。

## Success Criteria

- Each selected primary route returns an auditable output or an explicit health/fallback reason.
- The prompt uses the correct Agent identity, provider/model, effort, tools-enabled policy, and same-session continuation policy.
- The runner records session, usage/tool observations, fallback decisions, and failure reasons without `--max-turns 1`.
- No production path is read or modified; Codex retains final acceptance.
- 给出 Pass 或精确当前范围缺陷；不得把未来 pending verifier/receipt 当作已经执行，也不得把延后格式轨道问题误算为首版 HTML 阻断。

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

- 2026-09-01 12:22:13 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
