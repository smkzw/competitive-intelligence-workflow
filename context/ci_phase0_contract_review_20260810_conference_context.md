# Conference Context: ci_phase0_contract_review_20260810

Created: 2026-08-10 18:34:10
Objective: 在不修改文件的独立上下文中复核 Task 0.1-0.2 的真实闭合性、康哲合同稳定双读与单词漂移判断，识别任何会导致 Phase 0 假阳性的 P0/P1 缺口。
Task type: `complex_delivery_conference`
Risk: `high`
Conference mode: `parallel`

## Codex Main Venue

- Chair: Codex.
- Duties: understand the real task, decompose, define sources of truth, route work, protect boundaries, verify final artifacts, own visual/browser/PPT/PDF checks, own production writes, and deliver to the user.

## Conference Panel Assignment

    - Visual/design/HTML/PPT tasks use a Codex-led panel with no sub-venue chair: Pi/Oh My Pi `kimi-code/k3-256k` (high). If unavailable, the runner tries Grok Build `grok-4.5`, then Cursor CLI `cursor-grok-4.5-high`, then Pi/OpenCode Go `gpt-5.6-luna` (max), then Pi/Kimi `k3-256k` (high).
- Chinese labels or Chinese sentence review is handled directly by Codex and does not start a conference.
    - Other complex tasks use a Codex-chaired panel with no sub-venue chair. Participant 1 is Pi/Alibaba `qwen3.8-max` (xhigh) during the Beijing 22:00-07:00 window, and outside that window its exact Qwen Max node is replaced by Pi/cms-smk `cms-model` (high); its remaining fallbacks are Pi/cms-smk `cms-model` (high), Pi/cms-smk `deepseek-v4-flash` (max), Pi/OpenCode Go `deepseek-v4-flash` (max), and Pi/DeepSeek `deepseek-v4-flash` (max). Participant 2 is Grok Build `grok-4.5`, with Cursor CLI `cursor-grok-4.5-high` and Pi/cms-router `minimax-m3` as fallbacks. Codex remains the final authority. The explicit Luna native/CLI compatibility route remains available for execution roles that declare Codex subAgent.
- Every conference role starts with one bounded same-session pass. Codex reviews its quality and may dispatch zero or more targeted follow-up prompts through the same session. A new session is a routing failure unless a primary role failed before a resumable session existed and the documented fallback was activated.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md`，批准产品规格，SHA-256 `f96be175464d06f4a4b2075f020016148e3ac864d07b7ffe05a27db476ca465f`。
- `/Users/smkzw/Documents/AI Products/.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md`，批准实施计划，SHA-256 `4cc0b3af68e9b114ddc9b9c08242a84b7932215647d75b352c450c6dc723326f`；仅限读取 Phase 0 与 Task 0.1–0.3 条款。
- Task 0.1：`docs/decisions/0000-design-v1.2-approval.md`、`migration/legacy_manifest.{jsonl,schema.json}`、`tools/check_no_legacy_refs.py`、`tests/migration/test_no_legacy_runtime_dependency.py`。
- Task 0.2：`pyproject.toml`、`uv.lock`、`docs/decisions/0001-technology-stack.md`、`tests/contract/test_dependency_manifest.py`。
- Task 0.3 当前材料：`docs/decisions/0002-kangzhe-contract-reconciliation.md`。
- 两份只读合同候选（明确允许参与者读取、统计和比较，但禁止修改、复制或创建派生资产）：
  - `/Users/smkzw/Documents/康哲项目资料/模版/design_share_v2.md`
  - `/Users/smkzw/Documents/康哲项目资料/模版/design_v2.md`
- Git 提交 `5b131be` 与 `888204b`，以及当前只读 `git status`、测试、静态检查、摘要和稳定性命令输出。

## Scope

- In scope：独立重跑或检查 Task 0.1/0.2 的确定性验收；检查测试是否真正覆盖其声称合同；复核 Task 0.3 的 stable-read 元数据、当前共同正文差异、预计修正摘要和用户确认边界；只报告 P0/P1 以及会制造 false-green 的确切缺口。
- Out of scope：修改任何文件；提前执行 Task 0.4；生成报告或视觉资产；扩展安全专项测试；重新设计已批准 v1.2 产品范围；把格式偏好或小型代码风格建议升级为阻断。

## Success Criteria

- Each selected primary route returns an auditable output or an explicit health/fallback reason.
- The prompt uses the correct Agent identity, provider/model, effort, tools-enabled policy, and same-session continuation policy.
- The runner records session, usage/tool observations, fallback decisions, and failure reasons without `--max-turns 1`.
- No production path is read or modified; Codex retains final acceptance.
- 每个 finding 必须提供文件/行、可复现命令或具体合同断言，并区分 observed / inferred / recommended。
- 明确给出 Task 0.1、Task 0.2、Task 0.3 decision material 各自 `PASS`、`PASS WITH REQUIRED REPAIR` 或 `FAIL`；不得用总体印象代替逐项结论。
- 对康哲候选必须核对两个完整文件摘要、行数、共同正文锚点、唯一差异和“经验法则→经验阈值”预计摘要；若无法复现要明确原因。
- 参与者只拥有否决/建议权，不得写入源文件或 runner 管理的输出路径。

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
- `/Users/smkzw/Documents/康哲项目资料/模版/` 的两份已列候选是本次唯一 workspace 外只读例外；禁止读取同目录其他项目材料。
- 不得把未获得用户确认的当前康哲摘要称为“已批准”。

## Loop Log

- 2026-08-10 18:34:10: Conference initialized by `hermes_workflow_guard.py init-conference`.
