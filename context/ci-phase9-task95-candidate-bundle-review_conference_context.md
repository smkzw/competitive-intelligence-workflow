# Conference Context: ci-phase9-task95-candidate-bundle-review

Created: 2026-09-01 09:17:15 CST
Objective: 独立审阅 Task 9.5 候选 Skill 包：挑战 bundle 内容闭包、隔离安装、Codex/Hermes/OMP 真实宿主进程回执、no-draft 语义、首版仅站点式 HTML 边界及中文安装说明；不得把版本探针或直接 ci-workflow 子进程冒充真实宿主通过。
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

- Linked execution task: `ci-phase9-task95-candidate-bundle`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `openai-codex/gpt-5.6-luna`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- `.trellis/tasks/09-01-phase-9-task-95-candidate-bundle/{task.json,prd.md,design.md,implement.md}`：Task 9.5 当前合同、设计、实现和恢复状态。
- `../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md`：获批的分阶段实施计划与 Task 9.5 验收口径。
- `dist/competitive-intelligence-workflow.tar.zst` 及其 `.manifest.json`、`.sha256`：本轮候选包及完整性旁车。
- `tools/{build_bundle.py,verify_bundle.py,install_bundle.py,run_host_smoke.py}`、`tools/bundle_contract.py`：构建、闭包核验、隔离安装和真实宿主冒烟入口。
- `src/ci_workflow/application/{host_smoke.py,host_smoke_runner.py}`、`src/ci_workflow/hosts/receipt.py`、`schemas/host-receipt.schema.json`：真实宿主进程、运行语义和回执合同实现。
- `docs/acceptance/host-smoke/{codex.json,hermes.json,omp.json,batch.json,archive.json,README.md}`：三宿主实跑与归档证据。
- `/private/tmp/ci-task95.cAkC1C`：同一候选包的当前隔离安装根，仅供只读核验；不是生产安装。
- `tests/contract/test_host_receipt_contract.py`、`tests/hosts/`、`tests/package/`：合同、fresh-install、宿主和候选包测试。
- Do not add production paths unless the user explicitly authorized reading them for this task.

## Scope

- In scope: 候选包内容闭包；声明 fixture 与设计规范自测是否随包安装；构建/安装 CLI 是否符合获批计划；隔离安装；Codex、Hermes、OMP 是否确由各自真实宿主进程启动已安装公共 Skill；三宿主进程、会话、运行是否独立；证据不足时 `no_draft=true` 且没有报告；首版是否严格为站点式 HTML；中文安装与验收说明是否可由非技术用户理解。
- Out of scope: PDF、HTML-PPT、PPTX 导出实现与验收；科学内容终局签署；生产入口覆盖；安全性测试；修改源文件或替 Codex作最终接受决定。

## Success Criteria

- Each selected primary route returns an auditable output or an explicit health/fallback reason.
- The prompt uses the correct Agent identity, provider/model, effort, tools-enabled policy, and same-session continuation policy.
- The runner records session, usage/tool observations, fallback decisions, and failure reasons without `--max-turns 1`.
- 独立核验候选包摘要、包内容闭包、fresh-install 根、三个回执的 Schema/时间/入口/进程/会话/运行及同包绑定。
- 不把版本探针、适配器自产 JSON 或直接 `ci-workflow` 子进程冒充为真实宿主通过；必须在回执中看到各宿主可执行文件、正常宿主退出和工作流证据不足退出语义。
- 对 `no_draft`、无报告产物、HTML-only 范围及中文说明给出明确通过/不通过和可复核证据；发现缺陷时提出最小修复与复测要求。
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

- 2026-09-01 09:17:15 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
