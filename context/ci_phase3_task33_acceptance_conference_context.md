# Conference Context: ci_phase3_task33_acceptance

Created: 2026-08-12 22:20:42
Objective: 独立验收 Task 3.3 用户辅助下载、自动识别归档与幂等恢复实现，审查真实用户路径、规则绑定、状态事件和假绿
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

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §10.2、§11.5、§11.7。
- 批准实施计划 Task 3.3；验收文件名与预期为三份精确集成测试、最终 `3 passed`。
- `src/ci_workflow/ingestion/manual_inbox.py`、`schemas/download-request.schema.json`、`src/ci_workflow/ingestion/__init__.py`、`package-manifest.json`。
- `policies/gates/A-v1.yaml`、`B-v1.yaml`、`C-v1.yaml` 及 `src/ci_workflow/gates/models.py`。
- `tests/integration/test_manual_inbox_recovery.py`、`test_user_filename_auto_rename.py`、`test_download_request_transitions.py`。
- Codex 当前锚点：精确测试 `3 passed`；Task 3.1/3.2 回归 `241 passed`；全库 `432 passed`；Ruff、严格 mypy、Schema、包校验、`git diff --check` 通过。参与者必须自行复核。

## Scope

- In scope: 只读审查真实收件目录扫描、规则/报告/关键缺口绑定、请求身份、下载清单、内容匹配、隔离、规范归档、来源版本、重抽取任务、六态事件和崩溃重放。
- In scope: 运行精确三文件测试及自建临时目录反例；核对用户只需下载、保留原文件名并放入一个目录是否真实成立。
- Out of scope: 修改文件、联网下载、OCR、Task 3.4+、报告渲染、视觉验收、安全性测试、生产路径。

## Success Criteria

- Each selected primary route returns an auditable output or an explicit health/fallback reason.
- The prompt uses the correct Agent identity, provider/model, effort, tools-enabled policy, and same-session continuation policy.
- The runner records session, usage/tool observations, fallback decisions, and failure reasons without `--max-turns 1`.
- No production path is read or modified; Codex retains final acceptance.
- 每位参与者给出 `PASS|FAIL; P0=n; P1=n; P2=n`；仅 P0=0 且 P1=0 才建议接受。
- P0/P1 必须包含文件/行、可执行复现、实际/预期、用户影响、最小修复和建议回归名。
- 至少挑战：伪造/串错规则、主文已足够仍请求、同参/跨运行重建、相同坏文件多轮、合法+无效多文件、PDF/HTML 冒充、DOI/NCT/PMID 规范化、隔离重复、归档漂移、作业崩溃重放、状态依赖 Schema、下载列表后端词泄漏。

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

- 2026-08-12 22:20:42: Conference initialized by `hermes_workflow_guard.py init-conference`.
