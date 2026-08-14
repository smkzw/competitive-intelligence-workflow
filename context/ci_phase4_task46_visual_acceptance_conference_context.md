# Conference Context: ci_phase4_task46_visual_acceptance

Created: 2026-08-14 13:49:13
Objective: 以真实中文资深临床试验医学经理视角独立验收 Task 4.6 全站双浏览器三视口工具与实际门户产物

## 本轮验收对象

- 计划依据：`../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` Task 4.6。
- 浏览器验收工具：`tools/verify_portal.py` 与 `src/ci_workflow/qc/browser.py`。
- 已生成的完整合成项目：`.artifacts/task46-visual`。
- 门户入口：`.artifacts/task46-visual/reports/A/v-fixture-001/html/index.html`。
- 本次 Codex 实跑结果：16 个路由 × Chromium/WebKit × 1280/1440/1920，共 96 张原分辨率截图，双浏览器 trace 与 `report.json` 均位于 `.artifacts/task46-visual/verification/A/v-fixture-001/`；命令退出 0。
- 每位参与者必须亲自运行相同全站命令，但使用独立 `--output-dir`，并用视觉能力实际打开门户和截图，不得只读源码或采信现有 `report.json`。
- 这是一套 Task 4.6 基础设施合成站点，产品/试验详情页的完整医学内容属于 Phase 5–7，不把“合成内容不完整”误判为本任务 P1；但导航、页面责任、可读性、遮挡、溢出、错误状态、验证完整性均在本任务范围。
- 参与者只审评、不得修改任何文件；Codex 是最终接受者。

## 判定标准

1. 验证器确实覆盖静态责任页及清单中每个产品/试验详情页，不允许首页式、Top-N 或漏页假绿。
2. Chromium 与 WebKit 的 1280、1440、1920 均实际跑过；截图数量、分辨率、路由身份和 trace 一致。
3. 从懒惰、视觉敏感、不熟悉计算机和 AI 的中国资深临床试验医学经理视角，门户导航与页面层次可辨、无文字串行、明显遮挡、横向溢出、重复页脚或英文/程序员标签侵入用户界面。
4. 对任一意外（空结果、命令失败、缺页、数据异常）必须深挖原因，不能把退出码 0 当作唯一证据。
5. 最终只给 `PASS` 或 `REVISE`，并列 P0/P1/P2；P0/P1 必须附可复现路径、浏览器、视口与截图/观察证据。
Task type: `html_ppt_visual_browser`
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

- TODO: Add authoritative local files, extracts, datasets, screenshots, URLs, or user-provided materials.
- Do not add production paths unless the user explicitly authorized reading them for this task.

## Scope

- In scope: TODO
- Out of scope: TODO

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

- 2026-08-14 13:49:13: Conference initialized by `hermes_workflow_guard.py init-conference`.
