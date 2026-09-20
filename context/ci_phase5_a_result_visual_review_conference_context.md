# Conference Context: ci_phase5_a_result_visual_review

Created: 2026-08-28 00:29:05
Objective: 以真实医学经理视角独立验收A类报告数值完整性与安全性矩阵默认可见性，使用用户指定的Pi cms-router Minimax M3和Grok Build 4.6 medium。
Task type: `visual_delivery_conference`
Risk: `high`
Conference mode: `parallel`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

- Visual/design/HTML/PPT tasks use a Codex-led panel with no sub-venue chair. The effective visual participant chain is `kimi-code/k3-256k:medium -> grok-build/grok-4.6:high -> cursor/cursor-grok-4.6:high -> google-antigravity/gemini-3.7-flash:high -> opencode-go/muse-spark-1.2-contributor:xhigh -> codex/gpt-5.6-luna:max`; it is filtered against the actual execution route nodes recorded below before dispatch.
- Chinese labels or Chinese sentence review is handled directly by Codex and does not start a conference.
- Other complex, logic-heavy, evidence-sensitive, artifact-heavy, code-review, and high-risk contradiction work uses a Codex-chaired panel with no sub-venue chair. Participant 1 is Pi/google-antigravity `gemini-3.7-flash` (high) -> Pi/OpenCode Go `muse-spark-1.2-contributor` (high) -> Kimi Code `k3-256k` (medium) -> Codex subAgent `gpt-5.6-luna` (max). Participant 2 is Grok Build `grok-4.6` (medium) -> Pi/Cursor `cursor-grok-4.6` (medium) -> Pi/cms-router `minimax-m3` (high). Codex remains the final authority.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Execution-Conference Model Deduplication

- Linked execution task: `ci_phase5_a_result_visual_review`
- Execution evidence status: `no linked execution packet`
- Excluded provider/model nodes: none
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- 正式工作流产物：`.artifacts/a-result-visibility-accepted-v1/reports/A/v1/html/`。
- 浏览器量化：`.artifacts/a-result-visibility-accepted-v1/verification/browser-metrics.json` 与 `interaction-metrics.json`。
- 视觉证据：`.artifacts/a-result-visibility-accepted-v1/verification/screenshots/`。
- 数值真源：`fixtures/positive/a-atopic-dermatitis/research-package.json`，内容摘要 `21e8a4c39a30cb6b2c00ed90a265f7e843f93bffeb9b811f3da45b44183fefaa`。

## Scope

- In scope: A 类报告疗效/安全性数值完整性、安全热图默认宽度与 6 事件多选布局、图表先于表格、关键 n/N 抽查。
- Out of scope: B/C 报告、PDF/PPT、全量英文源术语本地化、超长详情页整体信息架构重做。

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

- 2026-08-28 00:29:05: Conference initialized by `hermes_workflow_guard.py init-conference`.
- 2026-08-28 00:30:02: 自动路由为 Kimi K3；因用户明确指定 Pi/cms-router Minimax M3 与 Grok Build 4.6 medium，按显式路由执行，未启用自动回退。
- 2026-08-28 00:30:02: 两条显式路由先执行健康预检。Grok 预检正常；Minimax 目录实际含 `MiniMax-M3`，但预检因大小写匹配误判 `model_not_listed`，按显式路由规则继续一次真实调用。
- 2026-08-28 00:33:55: Pi/cms-router Minimax M3 真实视觉操作完成，返回码 0、无回退，结论通过。
- 2026-08-28 00:39:01: Grok Build 4.6 medium 真实视觉操作完成，返回码 0、无回退，结论通过。
- 2026-08-28: Codex 复核两份报告、浏览器数据与截图，确认本次两项修复无阻断；英文源术语残留与长页扫读列为后续非阻断调优。
