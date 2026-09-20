# Conference Context: ci_phase5_a_values_matrix_visual_review_v4

Created: 2026-08-28 05:55:57
Objective: 以真实医学经理视角启用视觉能力，独立验收最终A类特应性皮炎HTML报告：首页和安全性详情页在768、1024、1280、1440像素下默认完整显示四个安全性维度，无横向拖动；核查中文可读性、图表优先、数值层级、表格与筛选交互，不修改文件，不替代Codex终验。
Task type: `visual_delivery_conference`
Risk: `high`
Conference mode: `serial`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

- Visual/design/HTML/PPT tasks use a Codex-led panel with no sub-venue chair. The effective visual participant chain is `grok-build/grok-4.6:high -> cursor/cursor-grok-4.6:high -> google-antigravity/gemini-3.7-flash:high -> opencode-go/muse-spark-1.2-contributor:xhigh -> codex/gpt-5.6-luna:max`; it is filtered against the actual execution route nodes recorded below before dispatch.
- Chinese labels or Chinese sentence review is handled directly by Codex and does not start a conference.
- Other complex, logic-heavy, evidence-sensitive, artifact-heavy, code-review, and high-risk contradiction work uses a Codex-chaired panel with no sub-venue chair. Participant 1 is Pi/google-antigravity `gemini-3.7-flash` (high) -> Pi/OpenCode Go `muse-spark-1.2-contributor` (high) -> Kimi Code `k3-256k` (medium) -> Codex subAgent `gpt-5.6-luna` (max). Participant 2 is Grok Build `grok-4.6` (medium) -> Pi/Cursor `cursor-grok-4.6` (medium) -> Pi/cms-router `minimax-m3` (high). Codex remains the final authority.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Execution-Conference Model Deduplication

- Linked execution task: `ci_phase5_a_values_matrix_visual`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `kimi-code/k3-256k`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- `.artifacts/a-values-matrix-fix-final-v4/reports/A/v1/html/overview.html`：最终A类报告门户首页。
- `.artifacts/a-values-matrix-fix-final-v4/reports/A/v1/html/safety.html`：最终A类报告安全性详情页。
- `.artifacts/a-values-matrix-fix-final-v4/reports/A/v1/html/efficacy.html`：疗效详情页，用于核查图表层级与图例可读性。
- `reviews/ci_phase5_a_values_matrix_fix_screenshots/final-v4/`：Codex在1024/1280像素下的实渲染全页与安全性矩阵截图。
- `docs/design/kangzhe-design-spec.md`：项目内化的康哲设计规范（若路径存在）；如不存在，只以最终页面的视觉一致性与目标用户可用性审查。
- Do not add production paths unless the user explicitly authorized reading them for this task.

## Scope

- In scope: 以真实中文临床试验行业资深医学经理视角，使用浏览器和截图实际审查首页、安全性详情页和疗效详情页；检查768/1024/1280/1440 px默认可视、四个安全性维度、无水平滚动、中文标签、数值层级、图表顺序和筛选交互。
- Out of scope: 修改文件、重做科学数据复核、PDF/PPT交付、扩展到B/C类报告、替代Codex终验。

## Success Criteria

- 报告可从门户进入，Logo、标题、导航和主要模块未错位。
- 首页与安全性详情页默认均展示任何TEAE、任何SAE、预先界定AESI、一项常见AE，且无需水平拖动。
- 不同观察期与未公开状态的文字可见、不与数值混淆。
- 疗效图例不遮挡最后一行，安全性明细表表头与页面导航不互相遮挡。
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

- 2026-08-28 05:55:57: Conference initialized by `hermes_workflow_guard.py init-conference`.
