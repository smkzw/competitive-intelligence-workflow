# Conference Context: ci_phase4_task44_visual

Created: 2026-08-14 06:31:17
Objective: 以真实医学经理角色独立试用 Task 4.4 九类图表、完整表与筛选联动
Task type: `html_ppt_visual_browser`
Risk: `high`
Conference mode: `parallel`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

    - Visual/design/HTML/PPT tasks use a Codex-led panel with no sub-venue chair: Pi/Oh My Pi `kimi-code/k3-256k` (high). If unavailable, the runner tries Grok Build `grok-4.6` (high), then the distinct Cursor `cursor-grok-4.6-high` route, then the distinct Pi/OpenCode Go `gpt-5.6-luna` (max) route. The Codex subAgent Luna route remains a separate native/CLI compatibility path.
- Chinese labels or Chinese sentence review is handled directly by Codex and does not start a conference.
    - Other complex tasks use a Codex-chaired panel with no sub-venue chair. Participant 1 is Pi/Alibaba `qwen3.8-max` (xhigh) during the Beijing 22:00-07:00 window, with first backup Pi/OpenCode Go `deepseek-v4-pro` (max) and the original Flash fallback retained after it; during the night window, its CMS-SMK Flash fallback is rewritten to Pi/OpenCode Go `deepseek-v4-flash` (max). Outside that window, participant 1 uses the specific daytime chain Pi/CMS-SMK `deepseek-v4-flash` (max) -> Pi/OpenCode Go `deepseek-v4-pro` (max) -> Pi/OpenCode Go `deepseek-v4-flash` (max). Other exact Qwen Max nodes use the global daytime replacement Pi/OpenCode Go `deepseek-v4-pro` (max). Participant 2 is Grok Build `grok-4.6` (high), with the distinct Cursor `cursor-grok-4.6-high` and Pi/cms-router `minimax-m3` as fallbacks. Codex remains the final authority. The explicit Luna native/CLI compatibility route remains available for execution roles that declare Codex subAgent.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Source Of Truth

- 当前真实页面：`http://127.0.0.1:8766/tests/fixtures/task44-chart-table-sync/index.html`。
- 当前截图：`.artifacts/task44-chart/current/state-*.png`。
- 产品合同：`context/ci_phase4_task44_context.md`、`contracts/kangzhe/design.md`、`docs/specs/competitive-intelligence-workflow-design-v1.2.md`。
- 参与者必须亲自使用浏览器完成筛选、图点/表行双向点选、1024/1280 视口和滚动阅读；只读源码或截图不算真实试用。

- 真实页面与修复前后截图均为本任务 fixture；不得外推为完整门户或真实临床结论。

## Scope

- In scope: 1280/1024、筛选/网址状态、图表与表格双向联动、未公开、负值、中文可读性和信息密度。
- Out of scope: A/B/C 完整业务门户、证据抽屉、PDF/PPT、真实临床数据结论和安全专项测试。

## Success Criteria

- Each selected primary route returns an auditable output or an explicit health/fallback reason.
- 三位用户指定参与者分别为 CodeBuddy CLI/kimi-k2.6、Pi/cms-router/minimax-m3、Grok Build/grok-4.6；都以“懒惰、视觉敏感、不熟悉计算机和 AI 的中文资深临床试验医学经理”身份真实操作并给出 PASS/REVISE、P0/P1/P2。
- 重点审评：一眼判断治疗/对照差异、单位/方向/时间窗/分析人群是否清楚、未公开是否会误读为 0、图在前表在后是否有用、四个小多图是否冗长、点选联动是否直观、1024 是否可读、是否有程序员/日志语言。
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

- 2026-08-14 06:31:17: Conference initialized by `hermes_workflow_guard.py init-conference`.
