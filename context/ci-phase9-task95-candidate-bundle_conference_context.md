# Conference Context: ci-phase9-task95-candidate-bundle

Created: 2026-09-01 10:06:47 CST
Objective: 对已完成修复的 Task 9.5 候选 Skill 包做治理关联复审：核实 bundle 内容闭包、规范 fresh-install、Codex/Hermes/OMP 三真实宿主完整无草稿阻断到补件恢复和站点式 HTML、中文安装说明及当前摘要归档；沿用既有独立审阅会话，不重做实现。
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

- `.trellis/tasks/09-01-phase-9-task-95-candidate-bundle/{prd.md,design.md,implement.md,task.json}`
- `../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` Task 9.5
- `dist/competitive-intelligence-workflow.tar.zst{,.sha256,.manifest.json}`
- `tools/{build_bundle.py,verify_bundle.py,install_bundle.py,run_host_smoke.py}`
- `skills/competitive-intelligence-workflow/SKILL.md`
- `docs/user-guide/install.md`
- `docs/acceptance/host-smoke/{README.md,archive.json,batch.json,codex.json,hermes.json,omp.json}`
- `src/ci_workflow/application/{fresh_install.py,host_smoke.py,host_smoke_runner.py,host_smoke_scenario.py}`
- `tests/hosts/test_fresh_install.py`
- 规范候选安装根 `/Users/smkzw/.cc-switch/skills/clinical-research/competitive-intelligence-workflow`，仅只读核验。
- 既有同会话独立复审：`runs/conference/ci-phase9-task95-candidate-bundle-review/general_single_object.md`。这只是历史审阅证据，不替代本轮重新核实。

## Scope

- In scope: 当前 bundle 闭包与摘要、规范安装、三真实宿主完整阻断—恢复—HTML 路径、归档绑定、首版 HTML-only 用户口径和中文安装说明。
- Out of scope: 新实现、PDF/PPT、报告内容/视觉重审、安全专项、生产写入或旧工程迁移。

## Success Criteria

- Each selected primary route returns an auditable output or an explicit health/fallback reason.
- The prompt uses the correct Agent identity, provider/model, effort, tools-enabled policy, and same-session continuation policy.
- The runner records session, usage/tool observations, fallback decisions, and failure reasons without `--max-turns 1`.
- No production path is read or modified; Codex retains final acceptance.
- 当前 bundle SHA-256、archive、dist 与规范安装内容地址应一致为 `50a91aac3e0050887ae48e29e921a45cf540d986b418eaac8d4af068f6a3e8c3`。
- 三份回执必须各自证明初始 no-draft 和最终 HTML，且批次 `real_host_pass=true`。

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

- 2026-09-01 10:06:47 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
- 本治理包用于把已完成的 `-review` 同会话审阅与执行任务标识关联；复用同一 Pi 会话 `01a05a8c-f404-7000-aada-4c33619bd1a4`，不新建审阅会话。
