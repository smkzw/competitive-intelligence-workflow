# Conference Context: ci_phase5_task54_visual

Created: 2026-08-18 03:20:12
Objective: 以真实中文资深临床试验医学经理视角，对 Task 5.4 A 类多页面门户进行启用视觉的端到端试用和独立审评
Task type: `visual_delivery_conference`
Risk: `high`
Conference mode: `parallel`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

    - Visual/design/HTML/PPT tasks use a Codex-led panel with no sub-venue chair: Pi/Oh My Pi `kimi-code/k3-256k` (high). If unavailable, the runner tries Grok Build `grok-4.6` (high), then the distinct Cursor `cursor-grok-4.6-high` route, then the distinct Pi/OpenCode Go `gpt-5.6-luna` (max) route. The Codex subAgent Luna route remains a separate native/CLI compatibility path.
- Chinese labels or Chinese sentence review is handled directly by Codex and does not start a conference.
    - Other complex tasks use a Codex-chaired panel with no sub-venue chair. Participant 1 is Pi/Alibaba `qwen3.8-max` (xhigh) -> Pi/OpenCode Go `deepseek-v4-flash` (max) during the Beijing 22:00-07:00 window; daytime is Pi/CMS-SMK `deepseek-v4-flash` (max) -> Pi/OpenCode Go `deepseek-v4-flash` (max). Participant 2 is Grok Build `grok-4.6` (high), with the distinct Cursor `cursor-grok-4.6-high` and Pi/cms-router `minimax-m3` as fallbacks. Codex remains the final authority. The explicit Luna native/CLI compatibility route remains available for execution roles that declare Codex subAgent.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md`。
- `../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` 的 Task 5.4。
- `contracts/kangzhe/design_specs/{ROUTER,core,project_profile,track_site}.md`，以项目内副本为唯一设计权威。
- 当前候选站点：`.artifacts/a-complete/reports/A/v-fixture-001/html/index.html`。
- 当前浏览器验收证据：`.artifacts/a-complete/verification/A/v-fixture-001/`。
- 当前运行标识：`run_05cd4064323bad1716943268`；数据为合成验收案例，不代表真实医学结论。

## Scope

- In scope: 以真实中文资深临床试验医学经理身份，启用视觉并实际浏览全部 12 个专题页面与 4 个产品详情页；操作导航、筛选、搜索和气泡矩阵设置；评价信息组织、图表可读性、临床直觉、中文表达和使用负担。
- Out of scope: 修改任何源文件；把合成数据当成真实医学事实；B/C 报告、PDF、HTML-PPT、PPTX、安全性测试和旧工程。

## Success Criteria

- Each selected primary route returns an auditable output or an explicit health/fallback reason.
- The prompt uses the correct Agent identity, provider/model, effort, tools-enabled policy, and same-session continuation policy.
- The runner records session, usage/tool observations, fallback decisions, and failure reasons without `--max-turns 1`.
- No production path is read or modified; Codex retains final acceptance.
- 每位评审者必须提供实际打开页面和操作交互的证据，并按阻断、重要、一般三级列出问题；不能仅凭源代码或截图文件存在性给结论。
- 结论必须回答：一个不熟悉计算机但视觉敏感、希望少操作的中文资深医学经理，能否迅速看懂竞争格局、主要疗效、安全性风险和产品差异。

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

- 2026-08-18 03:20:12: Conference initialized by `hermes_workflow_guard.py init-conference`.
