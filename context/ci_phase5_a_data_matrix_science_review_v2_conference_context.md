# Conference Context: ci_phase5_a_data_matrix_science_review_v2

Created: 2026-08-28 02:41:34
Objective: 独立审阅特应性皮炎A类报告候选包 cae2c3383b04b1987e51d675a21a13e99a9ed8f03718f0704e4cb09356a78f74 的疗效与安全性数值完整性、试验身份、同试验治疗/对照配对、公开完整/部分/未公开状态、跨试验误配风险及用户可见中文表达。重点核对 curated-result-evidence.json、source extracts、research-content.json、检索闭环记录；不得把预测披露或跨试验数值当作可比较结果。输出接受/拒绝及逐项证据。
Task type: `complex_delivery_conference`
Risk: `high`
Conference mode: `parallel`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

- Visual/design/HTML/PPT tasks use a Codex-led panel with no sub-venue chair. The effective visual participant chain is ``; it is filtered against the actual execution route nodes recorded below before dispatch.
- Chinese labels or Chinese sentence review is handled directly by Codex and does not start a conference.
- Other complex, logic-heavy, evidence-sensitive, artifact-heavy, code-review, and high-risk contradiction work uses a Codex-chaired panel with no sub-venue chair. Participant 1 is Pi/google-antigravity `gemini-3.7-flash` (high) -> Pi/OpenCode Go `muse-spark-1.2-contributor` (high) -> Kimi Code `k3-256k` (medium) -> Codex subAgent `gpt-5.6-luna` (max). Participant 2 is Grok Build `grok-4.6` (medium) -> Pi/Cursor `cursor-grok-4.6` (medium) -> Pi/cms-router `minimax-m3` (high). Codex remains the final authority.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Execution-Conference Model Deduplication

- Linked execution task: `ci_phase5_a_data_matrix_recheck`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `codex/gpt-5.6-luna`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- 修复后候选：`.artifacts/a-data-matrix-recheck-candidate-v2/research-content.json`
- 修复后内容摘要：`40f10108d8ab422a0b8adfcb149ebb6cd351e37cb66d73bc7e25d80d44d9664f`
- 结构化清单：`fixtures/positive/a-atopic-dermatitis/curated-result-evidence.json`
- 原始来源：`fixtures/positive/a-atopic-dermatitis/sources/`
- 检索闭环：`.trellis/tasks/08-28-phase-5-report-a-data-matrix-recheck/evidence/zero-result-coverage.md`
- 修复后预览：`.artifacts/a-data-matrix-recheck-preview-v6`
- Do not add production paths unless the user explicitly authorized reading them for this task.

## Scope

- In scope: 对否决意见逐项复核：ICP-332官方直接披露值及分子分母边界、AK120剂量组隔离、611研究药相关上呼吸道感染口径、TQH2722 II期身份、产品状态文字、矩阵同试验同组配对。
- Out of scope: 生成正式报告、替换当前入口、PPT/PDF与其他适应症。

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

- 2026-08-28 02:41:34: Conference initialized by `hermes_workflow_guard.py init-conference`.
- 2026-08-28: 首轮出现一项接受、一项拒绝；Codex按拒绝意见修复并生成新摘要。定向合同/浏览器回归61项通过；1024 px首页及安全性页无横向溢出；矩阵排除AK120混组组合并保留6个同组可比产品。请求同会话复核新摘要，不得沿用旧摘要结论。
- 2026-08-28: 第二轮Grok认为Amlitelimab默认矩阵跨试验。Codex随后以预览v6真实Chromium运行时核验：Amlitelimab气泡为`NCT05131477`、`125 mg KY1005 (Part 1)`，疗效42.9%、任何TEAE 67.5%，疗效与安全性由`trialId + armDetail`同时约束；AK120气泡数为0；矩阵共6个气泡。已在气泡增加`data-trial-id`、`data-arm-detail`及含登记号的提示，并新增浏览器回归；8项相关测试通过。1024 px下overview/safety文档宽均为1024，热图924/924。请区分“安全性热图按产品跨试验横向比较（报告预期，且注明同产品多试验取最高发生率）”与“气泡矩阵把同一产品不同试验疗效/安全性拼成一点（禁止）”。本轮只对新摘要与实际v6运行时作最终接受/拒绝，不得沿用旧摘要或未运行的静态推断。
