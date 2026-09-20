# Conference Context: ci_phase5_a_values_science_review_v3

Created: 2026-08-28 05:26:55
Objective: 独立复核A类特应性皮炎报告新增的10个已上市创新药总体不良事件治疗组/对照组数值：逐行核对来源、NCT、剂量、观察期、组别与数值，识别任何跨试验、跨剂量、跨时间窗误配；并评估疗效28/38、安全性数值26/38、总体TEAE 20/38的缺失解释是否足以支持报告生成。不得修改文件，不得自行接受科学审查。
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

- Linked execution task: `ci_phase5_a_values_matrix_visual`
- Execution evidence status: `linked`
- Excluded provider/model nodes: `kimi-code/k3-256k`
- If an execution packet exists but runner evidence is missing or unreadable, initialization fails closed. Agent adapters are ignored for this check; provider boundaries and model identity are retained, and effort differences do not bypass deduplication.

## Source Of Truth

- `.artifacts/a-values-matrix-fix-candidate-v3/research-content.json`：待独立复核的规范化研究内容，摘要 `eb6684ad1bc32313c6af17ce174a4aaf34be46fdfb5e44c2eb88bd4fdc91b4d9`。
- `fixtures/positive/a-atopic-dermatitis/curated-result-evidence.json`：新增结果行、来源定位与本地来源摘要的清单。
- `fixtures/positive/a-atopic-dermatitis/sources/`：清单逐项绑定的主要论文、监管审评或公司官方披露摘录。
- `reviews/ci_phase5_a_values_matrix_fix_data_audit.md`：补数前的分层缺失诊断与覆盖基线。
- Do not add production paths unless the user explicitly authorized reading them for this task.

## Scope

- In scope: 10个已上市创新药新增的20条治疗组/对照组总体不良事件结果；NCT、试验、剂量、组别、时间窗、分子分母及来源一致性；剩余缺失是否为真实未公开或尚未抽取；能否晋级为新的报告候选。
- Out of scope: 修改文件、生成科学复核接受结论、替Codex做最终报告/浏览器/视觉验收、扩展到B/C类报告。

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

- 2026-08-28 05:26:55: Conference initialized by `hermes_workflow_guard.py init-conference`.
