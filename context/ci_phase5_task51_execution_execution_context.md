# Execution Context: ci_phase5_task51_execution

Created: 2026-08-14 14:52:19
Objective: 以 TDD 实现 A 类范围、成熟度与 result-bearing 证据模型
Task type: `finite_code_task`
Risk: `high`
Execution module trigger: Codex identified 3 independent work items, which is greater than two.

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `finite_code_executor_cms` -> `pi` / `cms-smk` / `deepseek-v4-flash`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md` §2、§3.2、§12.1–12.2。
- `../.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` Task 5.1。
- `policies/ontology/innovation-therapy-v1.yaml`；本任务消费 Phase 2 已接受资格，不重写创新药政策。
- `context/ci_phase5_task51_context.md` 项目合同与当前仓库 `1816e67`。
- Allowed implementation: `src/ci_workflow/reports/a/contracts.py`、`analysis.py`、必要 `__init__.py`；tests only in `tests/reports/a/test_maturity_gate.py`、`test_result_bearing_gate.py`、`test_no_top_n.py`。
- 三个 worker 顺序运行，共享文件上的后序改动必须保留前序已通过合同；不得并行写同一文件。

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.
- 不生成 HTML/PDF/PPT 或草稿，不读取真实患者/公司秘密数据，不做安全测试。
- 不得通过删除成熟项目、降级 `result_bearing`、默认零、空字符串或 Top-N 让报告通过。
- 用户可见阻断原因使用简洁中文医学/临床开发语言，不暴露工程状态。

## Work Items

1. 先写成熟度递增字段失败测试，再实现 A 项目合同与逐层必需字段判定
2. 先写 result-bearing 确定性触发及疗效/TEAE-SAE 缺失阻断失败测试，再实现证据判定
3. 先写全宇宙无 Top-N、不得删除缺证项目的失败测试，再实现整批分析结果与中文阻断说明

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
