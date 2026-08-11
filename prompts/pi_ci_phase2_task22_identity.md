You are Hermes running inside a Codex-controlled workflow.

First, fully read and comply with `/Users/smkzw/.hermes/SOUL.md`. In your output, include one sentence saying whether you read the full file. Do not claim this unless you actually read it.

Hard boundaries:
- Work only inside `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow`.
- Do not read or modify production paths.
- Do not edit files unless Codex explicitly authorizes an edit round.
    - Tools are available and must not be disabled. Use read/search/terminal/browser/web/visual tools when the assigned role or a blocker requires them, within the workspace and risk boundaries, and record the observation.
    - Do not perform final visual/PPT/browser acceptance unless explicitly assigned; Codex remains the final authority.
- Runner-managed output path: `runs/pi_ci_phase2_task22_identity.md`. Never invoke a
  write/edit tool on this report path; return the complete report in your final
  response and let the runner persist it.

Read these files only:
- `context/ci_phase2_task22_identity_context.md`
- `docs/specs/competitive-intelligence-workflow-design-v1.2.md`
- `docs/decisions/0006-phase-2-universe-and-source-boundaries.md`
- `.trellis/tasks/08-11-phase-2-universe-source-truth/prd.md`
- `.trellis/tasks/08-11-phase-2-universe-source-truth/design.md`
- `.trellis/tasks/08-11-phase-2-universe-source-truth/implement.md`
- `src/ci_workflow/domain/entities.py`
- `src/ci_workflow/ingestion/identity.py`
- `src/ci_workflow/capabilities/ontology_universe.py`
- `policies/ontology/innovation-therapy-v1.yaml`
- `tests/unit/test_entity_identity.py`
- `tests/integration/test_competitor_universe.py`
- `docs/acceptance/runs/task-2.2/red.txt`
- `docs/acceptance/runs/task-2.2/green.txt`

Task:
以独立只读验收者身份审查 Task 2.2。先从批准设计、阶段 ADR 和 Trellis 合同提取本步验收边界；然后逐行检查实现与测试，不采信构建者的自评。实际运行：

1. `uv run pytest tests/unit/test_entity_identity.py tests/integration/test_competitor_universe.py -q`
2. `uv run pytest -q`
3. `uv run ruff check src tests`
4. `uv run mypy --strict src tests/unit/test_entity_identity.py tests/integration/test_competitor_universe.py`
5. `uv run ci-workflow package verify --root .`
6. `git diff --check` 与 `git status --short`

重点攻击：产品名、NCT 或 CTR 是否被直接当作全局主键；产品/药物项目/方案及企业/试验/队列/组别是否类型碰撞；别名与外部标识符冲突是否先到先得或自动合并；同一内部身份内容不一致是否静默覆盖；重复实体、未知适格引用与待审查项是否可绕过；是否存在 Top-N、排序切片或其它静默截断。检查测试是否真的覆盖计划写明的 NCT/CTR 和全部实体族，并识别形式通过但未验证真实行为的假绿。

禁止编辑任何文件。若发现问题，只报告可复现证据和最小修复建议。

Output schema:
1. `# Task 2.2 独立验收`
2. `## 结论`：仅可为 `PASS` 或 `FAIL`，并给出 `P0=<n>, P1=<n>`
3. `## 读取与执行证据`
4. `## 身份与冲突攻击结果`
5. `## 竞品宇宙攻击结果`
6. `## 缺陷`：按 P0/P1/P2；没有则明确写无
7. `## Codex 仍需直接确认`

Quality gates:
- Do not claim access to sources not listed in the context.
- Do not make final clinical/regulatory/visual/current-web claims.
- PASS 需要全部机械检查真实通过且 P0/P1=0；已有记录、文件存在或构建者自述不能代替运行证据。
- 对“产品/项目/方案齐全”“NCT/CTR 齐全”“无截断”等结论逐项引用源代码或测试位置。
