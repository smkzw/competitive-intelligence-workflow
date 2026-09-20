# Conference Context: ci_phase5_a_data_matrix_visual_review_v2

Created: 2026-08-28 03:12:48
Objective: 以真实医学经理视角独立复验特应性皮炎A类报告预览v8。必须使用视觉/浏览器实际打开 `.artifacts/a-data-matrix-recheck-preview-v8/overview.html`、`safety.html`、`matrix.html`，在1024、1280、1440视口复验上一轮缺陷是否关闭，并检查首屏信息层级与中文原生表达；安全性热图默认完整显示且无需左右拖动；首页与安全性详情图在表之前；疗效安全性矩阵气泡、试验提示、筛选与表格一致；AK120不得因多剂量合并安全性进入默认矩阵；Amlitelimab气泡须绑定NCT05131477同组。不得继续使用 v6 的旧截图或旧测量替代 v8 实测。输出接受/拒绝、v8 截图/运行时证据和明确修复项。
Task type: `visual_delivery_conference`
Risk: `medium`
Conference mode: `serial`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

- Visual/design/HTML/PPT tasks use a Codex-led panel with no sub-venue chair. The effective visual participant chain is `kimi-code/k3-256k:medium -> grok-build/grok-4.6:high -> cursor/cursor-grok-4.6:high -> google-antigravity/gemini-3.7-flash:high -> opencode-go/muse-spark-1.2-contributor:xhigh`; it is filtered against the actual execution route nodes recorded below before dispatch.
- Chinese labels or Chinese sentence review is handled directly by Codex and does not start a conference.
- Other complex, logic-heavy, evidence-sensitive, artifact-heavy, code-review, and high-risk contradiction work uses a Codex-chaired panel with no sub-venue chair. Participant 1 is Pi/google-antigravity `gemini-3.7-flash` (high) -> Pi/OpenCode Go `muse-spark-1.2-contributor` (high) -> Kimi Code `k3-256k` (medium) -> Codex subAgent `gpt-5.6-luna` (max). Participant 2 is Grok Build `grok-4.6` (medium) -> Pi/Cursor `cursor-grok-4.6` (medium) -> Pi/cms-router `minimax-m3` (high). Codex remains the final authority.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Execution-Conference Model Deduplication

- Linked execution task: `ci_phase5_a_data_matrix_recheck`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `codex/gpt-5.6-luna`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- 当前复审对象：`.artifacts/a-data-matrix-recheck-preview-v8/{overview,safety,matrix}.html`。
- v7 使用与已获科学复核接受的 v2 候选相同数据，只修复安全性明细的视觉与交互；候选内容摘要为 `40f10108d8ab422a0b8adfcb149ebb6cd351e37cb66d73bc7e25d80d44d9664f`。
- Codex 浏览器复核记录：`.artifacts/_codex_visual_probe_v8/measurements.json` 及 `matrix_1024.png`、`matrix_1440.png`。复审者必须自行实测，不能只复述此记录。
- Do not add production paths unless the user explicitly authorized reading them for this task.

## Scope

- In scope: 复验上一轮拒收的三个问题——明细列宽、默认全量展开导致的极端页面高度、1024 px 横向溢出；同时确认热图和矩阵未回退。
- Out of scope: 改动数据内容、重做科学证据复核、编辑源文件或生产入口。

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

- 2026-08-28 03:12:48: Conference initialized by `hermes_workflow_guard.py init-conference`.
- 2026-08-28：首轮真实浏览器复核拒绝 v6；明细表 10,223 行默认展开、页面约 175.8 万 px 高，且 1024 px 下表格需左右拖动。
- 2026-08-28：Codex 修复并生成 v8。明细保留全部 10,222 条，默认每页 50 条；1024/1280/1440 px 实测页面高 6,029/6,840/6,854 px，表格宽度分别为 924/924、1100/1100、1100/1100，首行高 60.2/75/75 px，维度列宽 129.4/154/154 px；翻页后从第 1/205 页变为第 2/205 页且首行变化；无控制台错误。矩阵控制器在 1024 px 恢复为三列，图表顶部 y=652，首个气泡 y=844，已进入首屏。请在同一 Kimi 会话中自行重新打开 v8 三页并独立复验，不能只采信这些数值或继续复用 v6 证据。

## Same-session Review Request

这是修复后的定向复验，不是重复派发旧任务。请先重新读取本文件，确认当前对象是 v8；随后真实打开 v8 三页并保存到新的 `.artifacts/_visual_probe_v8/` 证据目录。至少实测：三视口安全性明细的总行数与可见行数、分页状态与翻页变化、页面高度、维度列宽、表格及热图 scrollWidth/clientWidth；三视口矩阵控制器列数及图表/首个气泡相对首屏位置；首页、矩阵关键数据绑定与控制台错误。最终返回完整更新版会议输出，并明确接受或拒绝 v8。若输出仍以 v6 为对象，则该轮无效。
