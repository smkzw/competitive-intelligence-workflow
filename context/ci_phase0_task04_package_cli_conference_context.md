# Conference Context: ci_phase0_task04_package_cli

Created: 2026-08-11 15:28:04
Objective: 独立验收 Phase 0 Task 0.4 的安装包清单、公开与内部 Skill 边界、唯一中文 CLI 及失败关闭行为，拒绝源码自证和旧产物假绿。
Task type: `high_risk_contradiction_review`
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

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md`，重点 §6、§9、§10。
- `package-manifest.json` 与 `schemas/package-manifest.schema.json`。
- `skills/competitive-intelligence-workflow/` 与 `skills/_internal/`。
- `src/ci_workflow/`、`pyproject.toml`、`uv.lock`。
- `tests/contract/test_package_manifest.py`、`tests/integration/test_cli_help.py`、`tests/integration/test_cli_command_catalog.py`。
- 当前工作树与真实命令输出；不得读取其他会商参与者的输出。

Task 0.4 冻结要求：一个公开 Skill 入口；15 个内部 Skill 仅声明稳定输入、输出、禁止与恢复边界，不复制全局组织图；唯一 CLI 目录为 `package verify`、`project create`、`project verify`、`project run [--resume]`、`capability preflight`、`fixture run`，禁止别名。当前阶段仅前三者中的包校验与项目创建/校验有真实处理器，后续能力必须非零返回 `CAPABILITY_NOT_IMPLEMENTED` 和中文说明。

阶段边界：Task 0.4 的 `package-manifest.json` 核验当前源树/候选包根的闭合性；Python wheel 只承载 CLI 模块，不是最终跨宿主 Skill bundle。完整可安装 `.tar.zst` bundle、fresh install 与三宿主实际入口验收由批准计划 Task 9.5 建立。审查者必须指出 wheel 边界，但不得把 Task 9.5 提前实现作为 Task 0.4 的通过条件。

## Scope

- In scope: 只读检查清单闭合、Skill 边界、CLI 目录、包/项目骨架处理器、失败关闭、当前测试是否能机械证明这些要求。
- Out of scope: 修改文件；实现 Phase 1 以后业务；安全性测试；报告视觉设计；联网临床检索；旧工程迁移或删除。

## Success Criteria

- Each selected primary route returns an auditable output or an explicit health/fallback reason.
- The prompt uses the correct Agent identity, provider/model, effort, tools-enabled policy, and same-session continuation policy.
- The runner records session, usage/tool observations, fallback decisions, and failure reasons without `--max-turns 1`.
- No production path is read or modified; Codex retains final acceptance.
- 两位参与者分别运行实际命令和至少一个负例，报告 P0/P1/P2 缺陷；只有 P0=0、P1=0 才可建议接受。
- 不因 52 项测试已绿而假定正确；核对 wheel/源树/项目根的边界并指出任何安装语义歧义。

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

- 2026-08-11 15:28:04: Conference initialized by `hermes_workflow_guard.py init-conference`.
- 2026-08-11 15:31: source packet、冻结 CLI 目录与验收边界由 Codex 补齐；参与者仅做独立只读挑战。
- 2026-08-11 15:51: 独立审查发现 CLI 目录 schema 与 Skill 提示词运行时假绿；Codex 以变异测试修复，并将 Python wheel / Task 9.5 最终 bundle 的阶段边界写入本上下文。
