# Execution Context: ci-r23-publication-manual-product-gate-20260905

Created: 2026-09-05 17:40:32 CST
Objective: 独立审查 Publication 分类、人工补件状态机与产品运行接线，为 Codex 提供最小重构和负向验收证据
Task type: `long_horizon_code`
Risk: `high`
Execution module trigger: Codex assigned 3 bounded work item(s). Each item must identify its inputs, allowed paths, deliverable and acceptance check.
Route schedule: `peak`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `cursor/default -> openai-codex/gpt-5.6-luna:max -> openai-codex/gpt-6-astra:low`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `long_horizon_code_executor` -> `pi` / `cursor` / `default`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.3.md`（必须从工作区完整读取）
- `.trellis/tasks/09-05-r23-publication-manual-product-gate/{prd,design,implement}.md`
- `src/ci_workflow/ingestion/publication_gate.py`
- `src/ci_workflow/ingestion/manual_inbox.py`
- `src/ci_workflow/domain/research_package.py`
- `src/ci_workflow/application/research_package_submission.py`
- `src/ci_workflow/application/run_service.py`
- `src/ci_workflow/sources/connectors/{clinicaltrials_gov,pubmed}.py`
- 对应 `tests/integration`、`tests/contract` 与 schema；旧 Skill 仅为历史输入，不具权威性。

## Risk Boundaries

- No production writes.
- 三个 worker 全部只读；不得修改产品代码、测试、任务或治理文件。
- 只允许读取当前工作区；不得访问、探测或声明其他工程状态。
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.

## Work Items

1. 只读审计 publication_gate、ResearchPackage 和来源连接器：分类权威、登记绑定、自动获取尝试与独立复核缺口
2. 只读审计 manual_inbox、download request 和 run_service：唯一 gate、一次响应、原地重命名、恢复与多报告局部阻断插入点
3. 只读设计最小负向矩阵：综述/ad hoc、自审、网络解析权限、错文件/扫描 PDF/碰撞/登记号漂移、重复询问、篡改恢复

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
