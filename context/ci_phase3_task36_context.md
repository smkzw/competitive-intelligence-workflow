# Task Context: ci_phase3_task36

Created: 2026-08-13 05:41:21
Objective: 按批准计划实现 Task 3.6：项目 run 与 fixture run 共用真实类型化图执行器、唯一 fixture catalog、规范产物路径和当前 run/manifest 摘要绑定
Task type: `finite_code_task`
Risk: `high`
Selected agent route: `opencode-go` / `deepseek-v4-flash` / `max`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- `../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` Task 3.6（EX01–EX02、FX01–FX06、正式命令与退出语义）。
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §10、§18.2、§19.1–19.4：确定性控制图、持久运行摘要、无草稿、真实执行与验收责任。
- `docs/decisions/0011-phase-3-evidence-gates-and-recovery.md`：Phase 3 无损合同。
- 已接受 Task 3.2 `gates/{exhaustion,blocker_audit}.py` 与无草稿测试：A 空创新药宇宙只能生成证据不足说明。
- 已接受 Task 3.4 `graph/` 与 Task 3.5 `graph/recovery.py`：唯一类型化图执行器、规范事件/检查点、部分交付与恢复。
- 已接受项目合同、项目目录、产物路径和 manifest 实现：`domain/contracts.py`、`application/project_service.py`、`storage/{paths,manifest_store}.py`、`cli.py`。
- `.trellis/tasks/08-12-phase-3-evidence-gates-recovery/`：Phase 3 当前状态和下一项。

## Scope

- In scope: 新增 `application/run_service.py`、`application/fixture_runner.py`、`schemas/fixture-case.schema.json`、`fixtures/catalog.yaml`、`fixtures/synthetic/no-draft-a-empty/` 和四份计划集成测试；更新 `cli.py` 真实接线。
- In scope: 如模块导出确有必要，可最小更新 `application/__init__.py`；既有 CLI stub 测试必须最小改成真实 handler 断言，不能保留必然失败的旧预期。
- In scope: `project run` 与 `fixture run` 必须调用同一默认执行服务；fixture 只能经唯一 catalog 注册、schema 校验、逐输入 SHA-256 校验后运行。
- In scope: EX01 正常最小项目真实启动类型化图；EX02 `--resume` 只重排中断/失败节点及下游，不重跑成功节点。
- In scope: `no-draft-a-empty` 必须有真实输入和预期合同；运行真实 graph/gate/blocker 路径，生成中文证据不足说明，以稳定的“证据不足”非零退出码结束，不创建报告快照、coverage projection、格式任务、manifest artifact 或假 HTML。
- In scope: 每次运行生成新的 `run_id`，run event 和本次 run manifest 绑定 project/contract/case digest/input hashes/真实输出 SHA-256；旧 run/mtime/摘要不能冒充当前运行。
- In scope: 所有持久路径为项目相对 POSIX 路径；报告产物若存在只能来自 `ArtifactPathService` 的 `reports/<TYPE>/<version>/...`。本案例没有报告产物，但 blocker audit 和运行摘要必须进入 manifest 并与真实文件一致。
- In scope: CLI 用户文字用自然中文医学工作场景；机器 token 可留在 stderr/事件/JSON，不得把内部状态词当成面向用户的说明正文。
- Out of scope: Task 3.7 科学质控、A/B/C 完整报告数据、HTML/PDF/HTML-PPT/PPTX 渲染、PPT Master、浏览器/视觉、安全测试、真实联网检索。

## Success Criteria

- EX01、EX02、FX01–FX06 每个 exact node 先在测试存在后取得真实 RED，再最小实现到 GREEN；不得只以文件缺失/导入失败充当全部 RED。
- `uv run pytest tests/integration/test_project_run_cli.py tests/integration/test_fixture_run_cli.py tests/integration/test_fixture_artifact_paths.py tests/integration/test_fixture_case_contracts.py -q` 全绿。
- `uv run ci-workflow fixture run --case no-draft-a-empty --reports A --outputs html --project .artifacts/no-draft-a-empty` 真实运行并以定义的 evidence-blocked 非零码结束；产物只含 blocker audit/运行记录，无 `reports/A/<version>/` 正式、草稿或占位文件。
- 既有 CLI、项目目录、无草稿、图回归和全库测试继续通过；Ruff、strict mypy、schema、wheel 内容和差异检查通过。
- 独立审查 P0/P1=0 后才接受。

## Risk Boundaries

- 只写本任务明确的工程文件、系统临时测试目录和项目内 `.artifacts/no-draft-a-empty` 验收目录；不得写真实用户项目或旧工程。
- `.artifacts/no-draft-a-empty` 是可再生验收目录；正式接受前由 Codex检查并清理，不提交运行产物。
- 不做系统安全测试；非法 catalog、摘要漂移、当前 run 绑定和恢复正确性属于用户功能，不是安全扩项。
- The delegated agent is not final authority; Codex owns verification and acceptance.

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, or malformed probe output must be recorded and followed by one real route attempt. Only a missing executable or explicit invalid/retired/unlisted model may stop before that attempt.

## Loop Log

- 2026-08-13 05:41:21: Task initialized by `tools/hermes_workflow_guard.py init-task`.
- 2026-08-13 05:42: 读取 Task 3.6 精确计划、v1.2 控制图/无草稿/持久运行合同和现有 CLI/项目/图/阻断/路径实现；不重复外部选型，不增加编排框架。
- 2026-08-13 06:42: 原 Pi/OpenCode-Go 会话 `019ff7ef-7c3d-7000-8327-bcc835409cc7` 同会话修复返回 `resumed session continuation failed`；runner 检出运行中模型从 `opencode-go/deepseek-v4-flash` 漂移到 `opencode-go/mimo-v2.5`，故拒绝执行报告。工作树确有部分修改，八个 exact tests 当前通过，但独立检查确认清单事件绑定、mtime 精确校验、规范产物路径、确定性 fixture 合同和真实恢复成功路径仍未实现，不能接受。按既定 finite-code 路由进入下一 Pi/DeepSeek 候选，不因延迟切换。
- 2026-08-13 07:31: Codex 重跑 exact 9 passed/full 454 passed/真实 fixture exit 4 后，隔离 Pi/OpenCode-Go 与 Cursor/Grok 会商均判定 FAIL：`project run --resume` 不会重绑项目内已归档 universe 输入，复用逻辑也未受 `resume` 开关约束；已阻断项目再次恢复可从旧 report events 推导新 `evidence_blocked`，却产生 `event_count=0`、`checkpoint_id=None`、无当前证据/阻断包引用的幽灵清单。Grok Build 主会场两次同会话恢复仍 cancelled，后按声明 fallback 到 Cursor。Task 3.6 必须修复 CLI/API 真实恢复、当前运行复用事件/检查点/证据引用和相应 exact tests。完整 wheel 数据资源打包按计划 Task 9.5 验收，不在 Task 3.6 提前重构全工程资源根。
