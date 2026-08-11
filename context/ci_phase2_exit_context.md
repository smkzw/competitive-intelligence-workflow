# Task Context: ci_phase2_exit

Created: 2026-08-12 01:19:55
Objective: 独立否证 Phase 2 创新药宇宙、来源路由、录制官方来源到声明链与阶段退出条件
Task type: `high_risk_contradiction_review`
Risk: `high`
Selected agent route: `codex` / `gpt-5.6-luna` / `max`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §3、§8–12、§19.2。
- `docs/decisions/0006-phase-2-universe-and-source-boundaries.md` 至 `0010-versioned-facts-conflicts-and-claims.md`。
- `.trellis/tasks/08-11-phase-2-universe-source-truth/{prd,design,implement}.md`。
- `docs/acceptance/runs/task-2.1/` 至 `task-2.7/` 的结论和精简证据。
- `fixtures/recorded/phase-2-lineage/nct02912468-minimal.json`，摘要 `f497d57cb1d4dacf9f52ce015d12ff33d7c9dc43b0b788d3792d03e4ca38b1b1`；来源为 ClinicalTrials.gov 官方 API，2026-08-12 录制。
- Phase 2 全部政策、领域模型、连接器、摄取、事实/声明能力和正式测试；当前工作树是验收对象，不采信构建者自评。

## Scope

- In scope: 独立只读否证 Phase 2 创新药纳排、实体完整性、来源权限/恢复/cutoff、国内外连接器、精确定位、事实/冲突/声明链，以及录制官方来源跨层 fixture。
- Out of scope: 禁止修改文件；不提前验收 Phase 3 GateSpec、报告生成、真实全量竞品检索质量、用户界面或任何安全测试。

## Success Criteria

- 正式 Phase 2 命令 61 项、全库 188 项、Ruff、strict mypy、包校验和差异检查真实通过。
- 录制 fixture 必须从官方原文重建产品/试验/组别、精确片段、候选/已接受事实和可追溯声明；糠酸莫米松等传统背景治疗必须保留审计但不进入创新药宇宙。
- ClinicalTrials.gov、CDE、中国药物临床试验登记平台和五个指定行业公众号的来源角色/声明域可追溯；技术状态不混成科学缺失。
- 核对当前官方 API 的 NCT、组别、样本量、主要结果、披露日期和 PMID 与录制 fixture 一致；平台 holder 日期变化不得制造科学版本漂移。
- 仅当机械检查真实通过且 P0/P1=0 时建议 Phase 2 accepted；任何假链路、伪来源、日期/cutoff 泄漏或传统药误纳均否决。

## Risk Boundaries

- 本轮只读；Codex native subAgent 不写产品或报告文件，父 Codex 持久化最终交接。
- 官方 live 查询只用于核对录制 fixture，不刷新或改写 fixture；网络失败必须与科学不一致分开报告。
- 不进行安全测试，不把一个录制试验冒充全量竞品检索或真实报告验收。
- The delegated agent is not final authority; Codex owns verification and acceptance.

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, or malformed probe output must be recorded and followed by one real route attempt. Only a missing executable or explicit invalid/retired/unlisted model may stop before that attempt.

## Loop Log

- 2026-08-12 01:19:55: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- 2026-08-12 01:20: Codex 从 ClinicalTrials.gov 官方 API 录制 NCT02912468 最小科学片段；首次组合测试发现中国登记链接协议假设仍为 http，核实实现为 https 后修正，来源到声明链通过。
- 2026-08-12 01:39：原生 Luna 能力探测明确返回不支持，按全局规则切换到 `codex exec -m gpt-5.6-luna` 兼容路线；不是因等待时间或普通预检异常降级。CLI 会话 `019ff1d8-8ee4-79e1-b5fe-2aebb063e0be`，Luna/max、只读。
- 2026-08-12 01:39–02:19：独立验收首轮和两次同会话复核分别发现 9、8、6 个 P1；构建者逐项补充失败用例，再修复回执绑定、恢复穷尽、公众号定位、中国自然日时区、声明注册表和项目真源重开。
- 2026-08-12 02:38：同一 Luna 会话最终窄复核通过，P0=0、P1=0、P2=0；报告摘要 `48cf68a2d350ff51d07a2c1175a61f9799ac51127b4f92b3d8bf76f4ff75af9a`。
- 最终本地 Phase 2 正式套件 61 项、全库 188 项、Ruff、strict mypy（45 个源文件）、包校验 `phase-2-accepted` 和差异检查全部通过。
