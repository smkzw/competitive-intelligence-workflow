# Task Context: ci_phase2_task22_identity

Created: 2026-08-11 22:37:21
Objective: 独立验收 Task 2.2 稳定实体身份、别名/标识符冲突与完整竞品宇宙
Task type: `finite_code_task`
Risk: `medium`
Selected agent route: `opencode-go` / `deepseek-v4-flash` / `max`

## Trigger Reason

This task was initialized through the Codex x Hermes complex-task entrypoint because it is expected to involve more than three execution steps, research/writing/report/code/report-visual work, or source-grounded verification.

## Source Of Truth

- `docs/specs/competitive-intelligence-workflow-design-v1.2.md`，仅核对实体身份、竞品宇宙与创新药边界条款。
- `docs/decisions/0006-phase-2-universe-and-source-boundaries.md`。
- `.trellis/tasks/08-11-phase-2-universe-source-truth/{prd,design,implement}.md`。
- `src/ci_workflow/domain/entities.py`、`src/ci_workflow/ingestion/identity.py`。
- `src/ci_workflow/capabilities/ontology_universe.py` 与 `policies/ontology/innovation-therapy-v1.yaml`，只作为已接受 Task 2.1 的接口边界。
- `tests/unit/test_entity_identity.py`、`tests/integration/test_competitor_universe.py`。
- `docs/acceptance/runs/task-2.2/{red,green}.txt`。
- 当前工作树与实际命令输出；不把构建者的通过声明当作验收事实。

## Scope

- In scope: 只读攻击 Task 2.2 的稳定内部身份、产品/项目/方案/企业/试验/队列/组别关系、NCT/CTR 外部标识符、别名与标识符冲突、完整适格宇宙及 Top-N 风险；重跑机械检查。
- Out of scope: 不修改文件；不验收 Task 2.3 之后的来源连接器、证据声明链、报告、PDF/PPT/HTML 或生产安装；不扩大安全测试。

## Success Criteria

- 独立读取实现和测试，不能沿用构建者推理。
- 真实运行 Task 2.2 的 7 项测试、全库测试、Ruff、strict mypy、包校验与 `git diff --check`。
- 专门检查：名称/NCT/CTR 是否可能成为全局主键；别名或标识符冲突是否先到先得；同一内部 ID 是否静默覆盖；实体类型碰撞；未登记适格项；重复实体；Top-N 或顺序截断；待审查项是否可绕过宇宙闭合。
- 返回明确 `PASS` 或 `FAIL`，列出 P0/P1；P0/P1 为零才可建议接受。

## Risk Boundaries

- 本轮只读，不得写入或修改项目文件；runner 仅负责持久化最终报告。
- 不得把 Task 2.1 的已接受行为、构建者记录或已有测试通过误当作 Task 2.2 完成证明。
- The delegated agent is not final authority; Codex owns verification and acceptance.

## Timeout Policy

- Do not mark the delegated agent failed for slow response alone.
- For complex or artifact-heavy work, wait and poll generously; use conference mode when multiple independent model perspectives are needed.
- Failure requires terminal error, provider exhaustion/rate limit after controlled retry, empty/truncated retry output, or no progress after hard wait plus one retry.
- A provider catalog/auth/transport preflight is diagnostic, not a live capability verdict: timeout, auth refresh failure, or malformed probe output must be recorded and followed by one real route attempt. Only a missing executable or explicit invalid/retired/unlisted model may stop before that attempt.

## Loop Log

- 2026-08-11 22:37:21: Task initialized by `tools/hermes_workflow_guard.py init-task`.
