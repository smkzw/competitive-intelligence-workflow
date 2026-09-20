# Conference Context: ci-phase10-task101-acceptance-matrix-review

Created: 2026-09-01 12:04:05 CST
Objective: 独立审查 Task 10.1 首版站点式 HTML 验收矩阵是否与批准计划的 18 个 required-v12 机器族、ADR 0013、脱敏输入摘要、责任阶段、失败关闭测试和中文医学验收说明完整闭合；重点寻找自证循环、提前关闭未来责任、摘要或路径不可重算、旧格式回流和用户语言不当。
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

- `../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` Task 10.1，特别是 18 个批准机器 case 族及其子场景、owner stage 和失败关闭要求。
- `.trellis/tasks/09-01-phase-10-task-101-acceptance-matrix/{prd.md,design.md,implement.md,task.json}`：当前任务合同、HTML-only 裁决和精确验收节点。
- `docs/decisions/0013-site-first-v1-delivery-scope.md`：PDF、HTML-PPT、PPTX 延后，不能回流成为首版门槛。
- `schemas/acceptance-catalog.schema.json`、`fixtures/acceptance/catalog.yaml`、`fixtures/acceptance/full-matrix-v1/**`、`fixtures/acceptance/required-v12/**`：被审对象。
- `src/ci_workflow/application/acceptance_catalog.py`、`tests/acceptance/test_fixture_catalog.py`、`docs/acceptance/matrix.md`、`package-manifest.json`：摘要实现、确定性测试、中文说明和打包闭合。
- 执行证据：`runs/execution/ci-phase10-task101-acceptance-matrix/worker_01_round2.md`、`worker_02_round4.md`、`worker_03_round2.md`；这些只作证据，不是权威。

## Scope

- In scope: 独立读取并核对批准 18 族与子场景、23-case catalog、逐文件 SHA-256、case digest、IANA/cutoff、owner/receipt、HTML-only、失败关闭测试、中文医学验收文案；可运行只读验证命令。
- Out of scope: 修改任何文件、运行真实 fresh-source A/B/C、生成 RC、迁移或删除旧工程、PDF/HTML-PPT/PPTX、生产安装、安全专项、最终用户接受声明。

## Success Criteria

- Each selected primary route returns an auditable output or an explicit health/fallback reason.
- The prompt uses the correct Agent identity, provider/model, effort, tools-enabled policy, and same-session continuation policy.
- The runner records session, usage/tool observations, fallback decisions, and failure reasons without `--max-turns 1`.
- No production path is read or modified; Codex retains final acceptance.
- 审阅者不能把测试通过等同于通过：必须把批准计划当作独立集合，检查自证循环、未来责任提前关闭和已实现/未来 verifier 的区别。
- 输出明确给出接受、拒绝或需修复结论，并列出可定位文件/字段与最小修复建议。

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

- 2026-09-01 12:04:05 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
