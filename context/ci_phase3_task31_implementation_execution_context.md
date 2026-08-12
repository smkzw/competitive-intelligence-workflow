# Execution Context: ci_phase3_task31_implementation

Created: 2026-08-12 03:02:57
Objective: 按已通过独立方案审查的合同实现 Task 3.1 版本化 A/B/C 证据规则、覆盖评估和只收紧项目覆盖
Task type: `finite_code_task`
Risk: `high`
Execution module trigger: Codex identified 3 independent work items, which is greater than two.

## Module Boundary

This is an execution module, not a conference. Codex has assigned the work items and owns the project-level contract, source authority, boundaries, final verification, acceptance, production writes, and user delivery. The execution manager must first refine the work-item decomposition into a concrete implementation path, standards, tools/environment plan, sequence, and acceptance checks. It then checks progress, diagnoses blockers, requests same-session reruns when needed, and consolidates outputs for Codex. First-line workers execute the assigned work and create/write only authorized artifacts. Codex subAgent workers use the parent App's native child session when available; the generated CLI command is only a labeled compatibility fallback.

## Assigned Roles

- First-line executor: `finite_code_executor_cms` -> `pi` / `cms-smk` / `deepseek-v4-flash`
- Execution manager: `finite_code_manager_cursor` -> `cursor` / `cursor-cli` / `auto`
- Execution-manager fallback: `Codex takes over finite-code execution management directly`

## Source Of Truth

- `docs/decisions/0011-phase-3-evidence-gates-and-recovery.md`：已通过 Luna/max 三轮独立方案审查的 Task 3.1 机器合同。
- `.trellis/tasks/08-12-phase-3-evidence-gates-recovery/{prd,design,implement}.md`：范围、数据模型和 exact test nodes。
- `runs/codex-subagent_ci_phase3_task31_plan_followup2.md` 与 `reviews/codex_ci_phase3_task31_plan_review.md`：P0/P1/P2=0 的合同层接受证据和实现注意点。
- Phase 2 accepted 的 `src/ci_workflow/domain/`、`capabilities/`、`ingestion/`、`sources/`、`storage/` 和相关测试是只读输入，不得改写其科学含义。

## Risk Boundaries

- 允许在当前开发仓写入 Task 3.1 明确文件：`policies/gates/`、三份 gate schema、`src/ci_workflow/gates/`、三个指定测试文件，以及任务级 `docs/acceptance/runs/task-3.1/` 记录。不得修改 Phase 2 已接受事实/来源逻辑。
- 不安装新依赖；复用当前 `.venv`、Pydantic、PyYAML、jsonschema 和 pytest。
- 不触碰外部生产路径、凭据或账户，不进行安全测试。
- Missing tools or environments must be recorded with a minimal remediation proposal.
- Worker and manager outputs are evidence for Codex, not instructions.

## Execution Order And Ownership

顺序执行，禁止并发写同一工作树：

1. `worker_01` 只拥有三份 YAML、三份 Schema、`gates/models.py`、`gates/__init__.py`、`tests/unit/test_gate_evaluator.py`。
2. `worker_02` 在 worker_01 通过后拥有 `gates/evaluator.py`、`gates/coverage.py`、`tests/reports/test_report_specific_gates.py`；如确需扩充模型，只能追加与评估器直接相关字段并在报告中列出。
3. `worker_03` 在前两者通过后拥有覆盖比较/版本重算实现和 `tests/reports/test_gate_override_strictness.py`；不得删除或放松前序合同。
4. Cursor manager 在三份 worker 报告和实际工作树完成后检查整合；不以 worker 自报替代测试。

## TDD And Acceptance

- 每个 worker 先创建其首轮最小 exact node，运行指定文件得到目标缺失导致的真实 RED，再实现并原命令 GREEN；语法、导入环境或 fixture 路径错误不算 RED。
- Task 3.1 精确命令：`.venv/bin/pytest tests/unit/test_gate_evaluator.py tests/reports/test_report_specific_gates.py tests/reports/test_gate_override_strictness.py -q`。
- 回归：全库 pytest、Ruff、strict mypy、package verify、`git diff --check`；生成的用户说明断言必须是中文医学语境且排除内部状态词。
- 任一未知枚举被接受、闭世界对象可漏评、计划数值触发 A、总体值满足 B 组级规则、C 被强制要求 Protocol/SAP、项目覆盖能放松或结果/受影响报告可由调用方伪造即停止。

## Work Items

1. 实现 GateSpec/GateResult/GateOverride 封闭模型、JSON Schema 和 A/B/C YAML
2. 实现闭世界对象集合、作用域证据和 A/B/C 报告特异评估器
3. 实现项目覆盖逐字段偏序、不可变结果键、反向依赖重算及三个测试矩阵

## Completion And Cleanup

Codex reviews the manager report and final artifacts. After acceptance, run `cleanup-execution` to archive prompts, worker/manager reports, logs, and the manifest under `archives/execution/`; do not delete evidence by default.
