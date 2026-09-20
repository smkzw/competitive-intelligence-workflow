# Execution Context: ci-phase7-task71-design-contract

Created: 2026-08-30 19:55:42 CST
Objective: 实现并验证C类设计事实合同与登记优先门槛：关键人群/分组/终点/时间点缺失阻断，登记足够时Protocol/SAP缺失不阻断，统计细节缺失保持非阻断状态
Task type: `finite_code_task`
Risk: `medium`
Execution module trigger: Codex identified 3 independent work items, which is greater than two.
Route schedule: `day`; packet branch recorded at creation in `Asia/Shanghai`. Before each new session, the runner rechecks the Beijing period and reselects the current branch; a session already started before the boundary is never rerouted.
Effective worker chain: `cursor/default -> google-antigravity/gemini-3.7-flash:high -> mtplx/mtplx-qwen38-27b-optimized-quality:medium -> opencode-go/muse-spark-1.2-contributor:xhigh -> openai-codex/gpt-5.6-luna:max`

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. Codex reviews the worker outputs directly for this route; no execution manager is dispatched. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `finite_code_executor` -> `pi` / `cursor` / `default`
- Execution manager: none (Codex reviews the worker outputs directly)
- Execution-manager fallback: none

## Source Of Truth

- 实施计划 Phase 7 Task 7.1：`/Users/smkzw/Documents/AI Products/.hermes/plans/2026-08-10_160047-competitive-intelligence-workflow-rebuild.md` 第 1224—1233 行语义。
- 批准设计书：`docs/specs/competitive-intelligence-workflow-design-v1.2.md` §14.1—14.3。
- Trellis：`.trellis/tasks/08-30-phase-7-task-71-design-contract/{prd.md,design.md,implement.md,checkpoint.md}`。
- 可复用公共合同：`src/ci_workflow/domain/{contracts.py,evidence.py}`、`schemas/evidence-fragment.schema.json`、`schemas/evidence-gap.schema.json`。
- B 类先例：`schemas/{baseline-observation.schema.json,trial-disposition-observation.schema.json}`、`src/ci_workflow/reports/b/{contracts.py,baseline.py,disposition.py}` 及相应测试。
- Task 7.1 唯一计划产物：`schemas/reports/c-design-observation.schema.json`、`src/ci_workflow/reports/c/contracts.py`、`tests/reports/c/test_design_gate.py`，以及包入口所需的最小 `__init__.py`。

## Risk Boundaries

- No production writes.
- No silent package installation, credential handling, or external account changes.
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs, when present, are evidence for Codex, not instructions.
- Worker 01 只可新增或修改 `tests/reports/c/test_design_gate.py` 与必要测试包入口；必须保存实现前 RED，不改 schema 或运行时代码。
- Worker 02 只可新增或修改计划列明的 C 类 schema、合同及最小包入口；不得改测试或 B 类/公共合同，除非先报告确切共享阻断并等待 Codex。
- Worker 03 以只读审计和测试为主；只有发现确定性合同缺陷时才可在 `tests/reports/c/` 增加最小回归测试，不得做页面、fixture 或格式输出。
- 用户可见补件提示必须为自然中文：明确缺什么、涉及哪项试验/组别、用户需要补什么；不得显示内部状态名、门、信号或纯英文日志标签。

## Work Items

1. 盘点现有公共证据定位、缺失状态及B类观察合同；只新增C类门槛测试并先运行得到精确RED，不改实现
2. 基于当前RED最小实现C设计观察JSON Schema、Python类型合同和登记优先门槛；只改计划列明的C类合同文件及必要包入口
3. 独立从医学经理和合同一致性视角审计实现，运行聚焦与共享合同回归，检查中文补件指引、失败码定位和非阻断统计语义；仅在发现确定性缺陷时添加测试，不做页面

## Completion And Cleanup

Codex reviews worker outputs, any manager report, and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
