# Conference Context: ci-phase8-task84-runtime-visual-review

Created: 2026-08-31 09:50:29 CST
Objective: 独立只读审阅 Task 8.4 HTML-PPT 运行时底座的真实浏览器截图与交互证据，确认固定画布、双轴居中、逐字稿、讲者当前页和下一页、页码、计时及离线图表没有阻断；不得把极简运行时 fixture 当作正式康哲视觉母版，不修改文件。
Task type: `visual_delivery_conference`
Risk: `medium`
Conference mode: `parallel`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.


## Conference Panel Assignment

- Ordinary tasks remain Codex-direct. Chinese labels or Chinese sentence work uses its declared execution route and does not start a conference.
  - This packet uses one Codex-led conference object (`visual_single_object`) with no sub-venue chair. Its effective `CST` route chain is `kimi-code/k3-256k:medium -> openai-codex/gpt-5.6-terra:medium`; the packet branch is recorded at creation and filtered against the actual execution route nodes recorded below. Before a new session, the runner rechecks the Beijing period; an already-started session is never rerouted.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Execution-Conference Model Deduplication

- Linked execution task: `ci-phase8-task84-html-ppt-runtime`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `grok-build/grok-4.6`, `cursor/cursor-grok-4.6`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- 运行时：`assets/html-ppt/runtime.js`、`assets/html-ppt/runtime.css`、`assets/html-ppt/manifest.json`。
- 测试及样例：`tests/acceptance/test_html_ppt_runtime_smoke.py`、`tests/fixtures/html-ppt-runtime/index.html`。
- 当前原始截图：`docs/acceptance/runs/8.4/screenshots/` 中 Chromium/WebKit 各四张。
- 机器证据：`docs/acceptance/runs/8.4/browser-contract-ledger.json`、`browser-contract-evidence.md`、`verdict.md`。
- 产品边界：`.trellis/tasks/08-31-phase-8-task-84-html-ppt-runtime/prd.md`、`design.md`。
- Do not add production paths unless the user explicitly authorized reading them for this task.

## Scope

- In scope: 只读审阅八张原始截图和上述运行时/测试证据；核对画布居中、页码、逐字稿、演讲者当前页/下一页、计时、图表可见性及两浏览器一致性。
- Out of scope: 修改文件、联网、安全测试、正式 A/B/C 幻灯片视觉风格或医学内容验收；极简 fixture 不是康哲视觉母版。

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

- 2026-08-31 09:50:29 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
