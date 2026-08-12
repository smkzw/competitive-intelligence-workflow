# Conference Context: ci_phase3_task35_acceptance

Created: 2026-08-13 03:32:43
Objective: 独立验收 Task 3.5 部分交付协调器是否真实满足 v1.2：选择合同不可漂移、报告/格式独立、终态区分、重复阻断可恢复、报告版本重绑和共享事件库读路径不可伪造
Task type: `complex_delivery_conference`
Risk: `high`
Conference mode: `parallel`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

    - Visual/design/HTML/PPT tasks use a Codex-led panel with no sub-venue chair: Pi/Oh My Pi `kimi-code/k3-256k` (high). If unavailable, the runner tries Grok Build `grok-4.6` (high), then the distinct Cursor `cursor-grok-4.6-high` route, then the distinct Pi/OpenCode Go `gpt-5.6-luna` (max) route. The Codex subAgent Luna route remains a separate native/CLI compatibility path.
- Chinese labels or Chinese sentence review is handled directly by Codex and does not start a conference.
    - Other complex tasks use a Codex-chaired panel with no sub-venue chair. Participant 1 is Pi/Alibaba `qwen3.8-max` (xhigh) during the Beijing 22:00-07:00 window. Outside that window its exact Qwen Max node is replaced by Pi/OpenCode Go `deepseek-v4-flash` (max); during the night window, every exact Pi/cms-smk `deepseek-v4-flash` node is replaced by the same Pi/OpenCode Go route. Its remaining fallbacks are Pi/cms-smk `deepseek-v4-flash` (max) and Pi/OpenCode Go `deepseek-v4-flash` (max), with effective-route deduplication. Participant 2 is Grok Build `grok-4.6` (high), with the distinct Cursor `cursor-grok-4.6-high` and Pi/cms-router `minimax-m3` as fallbacks. Codex remains the final authority. The explicit Luna native/CLI compatibility route remains available for execution roles that declare Codex subAgent.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §10.1–10.2、§19.2。
- `context/ci_phase3_task35_context.md` 与批准计划 Task 3.5。
- `src/ci_workflow/graph/recovery.py`、两份 `tests/graph/test_partial_delivery*.py`。
- 已接受 Task 3.4 的 `executor.py`、`reducer.py`、`transitions.py`、`guards.py`、`registry.py`、`types.py` 作为运行边界。
- 参与者不得读取 worker reports、Codex review 或另一参与者输出。

## Scope

- In scope: 选择合同首动作持久化与版本单调、完整报告×格式矩阵、项目部分交付/终态阻断、重复阻断重开代次、报告版本重绑链、协调器业务事件读路径校验、真实 GraphExecutor/EventStore 状态。
- In scope: 运行两个精确节点和独立临时目录攻击，验证不是测试表格假绿。
- Out of scope: 修改文件、Task 3.6/3.7、CLI/fixture、报告门户/格式渲染、安全/浏览器/PDF/PPT/视觉/临床监管测试。

## Success Criteria

- Each selected primary route returns an auditable output or an explicit health/fallback reason.
- The prompt uses the correct Agent identity, provider/model, effort, tools-enabled policy, and same-session continuation policy.
- The runner records session, usage/tool observations, fallback decisions, and failure reasons without `--max-turns 1`.
- No production path is read or modified; Codex retains final acceptance.
- 两个批准精确节点通过；独立反例未发现 P0/P1。任一 P0/P1 即 FAIL；P2 必须有明确后续归属。
- 报告必须以 `PASS/FAIL` 和 `P0=n; P1=n; P2=n` 结束。

## Parallel Work Rule

For logic-heavy, rigor-sensitive, or artifact-heavy tasks, each participant independently runs the whole bounded workflow and writes a separate output. Leads compare after all available participant outputs are in or explicitly marked pending.

## Timeout Policy

- Participant soft wait: 60 minutes.
- Large-task participant wait: 120 minutes.
- Chair hard wait: 120 minutes.
- Failure rule: Do not fail a model for slow response alone; fail only on terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no useful progress after the high-budget same-session recovery loop. A catalog/auth/transport health preflight timeout or malformed response is diagnostic and must still allow one live route attempt; only a missing CLI or an explicitly invalid, retired, or unlisted model may block before live dispatch. If a resumable session exists after a step/size boundary, continue it before fallback; repeated identical output/tool evidence triggers the no-progress breaker.
- Pass/turn boundary: one conference prompt is one conference pass. The
  `--max-turns` value controls internal Agent tool-calling turns and is never
  set to 1 for substantive conference execution; generated participant and
  chair commands use the route budgets recorded by the guard.

## Risk Boundaries

- External Agents are advisory; Codex remains final authority.
- Codex owns visual/browser/PPT/PDF/rendered checks, live authority checks, final clinical/regulatory conclusions, and production writes.
- Do not mark a slow model failed solely due to latency.

## Loop Log

- 2026-08-13 03:32:43: Conference initialized by `hermes_workflow_guard.py init-conference`.
