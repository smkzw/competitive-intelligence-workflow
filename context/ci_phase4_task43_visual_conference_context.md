# Conference Context: ci_phase4_task43_visual

Created: 2026-08-14 03:26:17
Objective: 以真实资深医学经理视角独立试用并审评 Task 4.3 筛选交互与视觉可用性
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

- Task 4.3 当前真实页面：`http://127.0.0.1:8765/filter-test.html`。
- 当前截图：`.artifacts/task43-portal/current/screenshots/filter-1280.png`、`filter-1024.png`。
- 产品与视觉合同：`.trellis/tasks/08-13-phase-4-common-report-portal/prd.md`、`contracts/kangzhe/design.md` 与 `contracts/kangzhe/design_specs/`。
- 参与者须亲自使用浏览器完成选择、跨维度组合、页面/模块重置、空结果、前进后退和 1024 宽度体验；不能只读源码或截图。

## Scope

- In scope: Task 4.3 筛选入口、全页/模块层级、选择摘要、空结果、重置、网址恢复、键盘与 1280/1024 视觉可用性。
- Out of scope: Task 4.4 图表、Task 4.5 证据抽屉、真实临床结论、PDF/PPT、安全测试、源代码修改。

## Success Criteria

- Each selected primary route returns an auditable output or an explicit health/fallback reason.
- The prompt uses the correct Agent identity, provider/model, effort, tools-enabled policy, and same-session continuation policy.
- The runner records session, usage/tool observations, fallback decisions, and failure reasons without `--max-turns 1`.
- No production path is read or modified; Codex retains final acceptance.
- 三位参与者都必须以“懒惰、视觉敏感、不熟悉计算机和 AI 的中文资深临床试验医学经理”身份完成真实试用，并对是否可接受给出 PASS/REVISE 结论与 P0/P1/P2 缺陷。

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

- 2026-08-14 03:26:17: Conference initialized by `hermes_workflow_guard.py init-conference`.
