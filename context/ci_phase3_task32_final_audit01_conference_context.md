# Conference Context: ci_phase3_task32_final_audit01

Created: 2026-08-12 20:10:27
Objective: 在全新隔离上下文中只读攻击性验收 Task 3.2：按设计 v1.2 与批准计划验证双重穷尽、用户可读阻断审计包、无草稿/无下游、空宇宙、冲突及科学质控否决，只有 P0/P1 为零方可通过。
Task type: `high_risk_contradiction_review`
Risk: `high`
Conference mode: `parallel`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

    - Visual/design/HTML/PPT tasks use a Codex-led panel with no sub-venue chair: Pi/Oh My Pi `kimi-code/k3-256k` (high). If unavailable, the runner tries Grok Build `grok-4.5`, then the distinct Cursor `cursor-grok-4.5-high` route, then the distinct Pi/OpenCode Go `gpt-5.6-luna` (max) route. The Codex subAgent Luna route remains a separate native/CLI compatibility path.
- Chinese labels or Chinese sentence review is handled directly by Codex and does not start a conference.
    - Other complex tasks use a Codex-chaired panel with no sub-venue chair. Participant 1 is Pi/Alibaba `qwen3.8-max` (xhigh) during the Beijing 22:00-07:00 window. Outside that window its exact Qwen Max node is replaced by Pi/OpenCode Go `deepseek-v4-flash` (max); during the night window, every exact Pi/cms-smk `deepseek-v4-flash` node is replaced by the same Pi/OpenCode Go route. Its remaining fallbacks are Pi/cms-smk `deepseek-v4-flash` (max), Pi/OpenCode Go `deepseek-v4-flash` (max), and Pi/DeepSeek `deepseek-v4-flash` (max), with effective-route deduplication. Participant 2 is Grok Build `grok-4.5`, with the distinct Cursor `cursor-grok-4.5-high` and Pi/cms-router `minimax-m3` as fallbacks. Codex remains the final authority. The explicit Luna native/CLI compatibility route remains available for execution roles that declare Codex subAgent.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md`，重点 §8.4、§10.3—10.5、§19.2。
- `/Users/smkzw/Documents/AI Products/.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md`，重点 Task 3.2 与 Phase 3 退出合同；该文件只读。
- `policies/gates/{A-v1,B-v1,C-v1}.yaml` 与 Task 3.1 的已接受实现。
- 当前未提交 Task 3.2 差异：`src/ci_workflow/gates/{exhaustion,blocker_audit}.py`、`schemas/blocker-audit.schema.json` 及四份 Task 3.2 集成测试。
- 当前机械锚点：Task 3.2 精确集合 92 passed；Task 3.1 143 passed；全库 423 passed；Ruff、strict mypy、JSON Schema、package verify、`git diff --check` 均通过。验收者必须自行复现关键检查，不得仅采信这些数字。
- 不读取先前会商或执行者的结论文件，避免污染隔离判断。

## Scope

- In scope：攻击性检查双重穷尽角色分离、Phase 2 `EvidenceGap` 锚定、逐路线科学/技术证明、中文用户文本、空宇宙闭合、冲突、科学质控否决、公共写入口重验证、幂等性、审计包 Schema、所有阻断场景零草稿/零下游产物。
- In scope：核对 A/B/C 三个空场景、三份 GateSpec 的每个适用关键单元、A/B/C 关键冲突、三类科学质控否决确有机械测试；主动构造至少一个现有测试之外的高价值反例。
- Out of scope：Task 3.3 及之后功能；HTML/PDF/PPT/PPTX；安全测试；改代码、改测试、改 Trellis 或验收记录；外部联网研究。

## Success Criteria

- 每位验收者返回带文件/行号、可复现命令或最小反例的独立结论；纯建议、风格问题或“可能”不算 P1。
- 只有 P0=0 且 P1=0、精确测试与至少一个独立反例验证通过，才可给出 `PASS`；否则给出 `FAIL` 和最小修复边界。
- 不以 92/143/423 这些既有数字代替复测，不以测试通过代替源代码合同审查。
- 不改任何源文件、测试、Trellis 或验收记录；Codex 保留最终接受权。

## Parallel Work Rule

For logic-heavy, rigor-sensitive, or artifact-heavy tasks, each participant independently runs the whole bounded workflow and writes a separate output. Leads compare after all available participant outputs are in or explicitly marked pending.

## Timeout Policy

- Participant soft wait: 60 minutes.
- Large-task participant wait: 120 minutes.
- Chair hard wait: 120 minutes.
- Failure rule: Do not fail a model for slow response alone; fail only on terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no useful progress after the high-budget same-session recovery loop. A catalog/auth/transport health preflight timeout or malformed response is diagnostic and must still allow one live route attempt; only a missing CLI or an explicitly invalid, retired, or unlisted model may block before live dispatch. If a resumable session exists after a step/size boundary, continue it before fallback; repeated identical output/tool evidence triggers the no-progress breaker.
- Pass/turn boundary: one conference prompt is one conference pass. The
  `--max-turns` value controls internal Agent tool-calling turns and is never
  set to 1 for substantive conference execution; generated participant and
  chair commands use the route budgets recorded by the guard.

## Risk Boundaries

- External Agents are advisory; Codex remains final authority.
- Codex owns visual/browser/PPT/PDF/rendered checks, live authority checks, final clinical/regulatory conclusions, and production writes.
- Do not mark a slow model failed solely due to latency.

## Loop Log

- 2026-08-12 20:10:27: Conference initialized by `hermes_workflow_guard.py init-conference`.
