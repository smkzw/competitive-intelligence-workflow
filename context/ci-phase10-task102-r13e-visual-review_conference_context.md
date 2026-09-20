# Conference Context: ci-phase10-task102-r13e-visual-review

Created: 2026-09-02 00:13:27 CST
Objective: 由用户点名的三名独立真实医学经理基于 ego(lite) 逐项审阅 R13e A/B/C 站点式 HTML 的交互、横向比较、方案设计矩阵、默认视野与中文视觉体验；只读，不改代码。
Task type: `visual_delivery_conference`
Risk: `medium`
Conference mode: `parallel`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

- Ordinary tasks remain Codex-direct. Chinese labels or Chinese sentence work uses its declared execution route and does not start a conference.
  - This packet uses one Codex-led conference object (`visual_single_object`) with no sub-venue chair. Its effective `CST` route chain is `google-antigravity/gemini-3.7-flash:high -> kimi-code/kimi-for-coding:high -> openai-codex/gpt-5.6-terra:medium`; the packet branch is recorded at creation and filtered against the actual execution route nodes recorded below. Before a new session, the runner rechecks the Beijing period; an already-started session is never rerouted.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Execution-Conference Model Deduplication

- Linked execution task: `ci-phase10-task102-r13-product-rebuild`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `openai-codex/gpt-5.6-luna`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- 当前不可覆盖候选：`/Users/smkzw/Documents/AI Products/competitive-intelligence-acceptance/task-10.2-20260902-000900-r13e`。
- A 入口：`http://127.0.0.1:8770/a-real/reports/A/v1/html/overview.html`。
- B 入口：`http://127.0.0.1:8770/b-real/reports/B/v1/html/overview.html`；重点页为 `efficacy.html`、`baseline-overview.html`、`disposition-overview.html`。
- C 入口：`http://127.0.0.1:8770/c-real/reports/C/v1/html/overview.html`。
- Codex 当前 ego(lite) 视觉证据：`runs/tests/r13-ego/r13d-a-drawer-ego.png`、`r13d-b-baseline-ego.png`、`r13e-b-efficacy-cross-trial-ego.png`、`r13d-c-overview-ego.png`、`r13d-c-drawer-ego.png`。
- 产品设计与范围：`.trellis/tasks/09-01-phase-10-task-102-r13-product-rebuild/prd.md`、`design.md`、`implement.md`。
- 项目内化康哲规范：`contracts/kangzhe/design_specs/project_profile.md` 及同目录站点轨规范。
- Do not add production paths unless the user explicitly authorized reading them for this task.

## Scope

- In scope: 以中文资深临床试验医学经理身份真实浏览 A/B/C；检查默认视野、信息层级、临床含义、图表比较、表格可读性、点击下钻、关闭回焦、筛选与多页面一致性。
- A 必查：气泡点击能否打开疗效、安全性、产品档案和数据依据；全空 AESI 是否隐藏。
- B 必查：疗效是否有同一模糊临床概念下的跨试验治疗/对照并列图；表格能否明确对应产品、试验和组别；年龄/血红蛋白等基线是否跨研究归组；完成情况是否图表化。
- C 必查：概览是否覆盖全部研究和设计领域；横向矩阵是否逐试验展开；单元格能否下钻到原文、来源版本与定位；横向滚动只应局限在大矩阵内部。
- 浏览器硬约束：所有浏览、点击、截图、页面状态和视口检查必须使用 `ego-browser`（ego lite）；不得使用 Playwright、Chrome、WebKit、Selenium 或其他浏览器替代。
- Out of scope: 改代码、改报告、联网调研、安全测试、PDF/PPT、把日志或后端状态当用户报告内容。

## Reviewer Output Contract

- 分别列出阻断、重要缺陷、一般优化；每项写明报告/页面、可复现操作、观察结果、对医学经理的影响和最小修复建议。
- 明确区分亲眼在 ego(lite) 观察到的事实、基于页面内容的判断和建议。
- 不得只复述机器检查或截图；必须真实点击至少一个 A 气泡、一个 B 图表数值/表格数据单元格和一个 C 设计矩阵单元格。
- 不得宣称最终接受；Codex 独立复核后决定。

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

- 2026-09-02 00:13:27 CST: Conference initialized by `hermes_workflow_guard.py init-conference`.
