继续同一 Worker 02 会话。Codex 对当前 GREEN 做了独立反例复核，发现以下均为 Task 4.4 阻断性假绿。请在原授权文件内修复测试与实现，不能只解释。

## Hard boundaries

- 只在 `/Users/smkzw/Documents/AI Products/competitive-intelligence-workflow` 工作。
- 只修改 `src/ci_workflow/reports/common/chart_specs.py`、必要的 `src/ci_workflow/reports/common/__init__.py` 与 `tests/unit/reports/test_chart_compatibility.py`。
- 不修改浏览器层、已接受 Task 4.3 文件、设计合同、计划或生产路径；不提交。
- runner 管理输出 `runs/execution/ci_phase4_task44_execution/worker_02_followup.md`，不得用工具写该文件。

Read these files only:

- `AGENTS.md`
- `context/ci_phase4_task44_execution_execution_context.md`
- `context/ci_phase4_task44_context.md`
- `src/ci_workflow/reports/common/chart_specs.py`
- `src/ci_workflow/reports/common/view_state.py`
- `tests/unit/reports/test_chart_compatibility.py`
- `tests/unit/reports/test_view_model.py`

## Repair requirements

1. 当前 `COMPARABILITY_DIMS` 把 `control_role` 和 `denominator` 作为拆图维度。这会把同一试验治疗组与安慰剂/活性对照拆到不同图，也会因各试验样本量不同把跨试验对比拆散，直接违反用户“治疗组与对照效应同列、样本量/分母要展示”的要求。把二者改为组内展示语境，不得触发拆图；新增精确测试证明治疗/对照角色不同且分母不同仍在同一兼容图组。真正影响共轴可比性的维度保持为单位、量表、统计形式、方向、时间窗/其规范化桶、分析人群；不要凭空新增综合分数。
2. `ChartSpec.required_fields` 目前只是登记文本，`resolve_chart_type` 不验证任何必需字段，空行也可被标为可画。新增逐图精确测试：已披露数值行缺必需字段必须失败关闭；缺失/未公开行保留但明确 `renderable=False`，不得生成数值点；完整行 `renderable=True`。森林图上下限次序、气泡 size>0、雷达 dimensions/scores 等长度一致至少做最小类型/范围校验。
3. 当前接口接受任意 raw dict，未证明同一锁定快照。新增统一入口校验：row_id 非空且唯一、report_snapshot_id 非空且全部一致、disclosure_state 属已知集合；缺字段、混合快照、重复 row_id 失败关闭。保留 Task 4.1 `FilteredRowSet` 不扩围语义；若引入类型模型，必须是严格 `extra=forbid` 或明确分离科学行与图形字段，不能把任意前端字典当真源。
4. `validate_all_rows_covered` 目前允许原始行本身重复 row_id，只比较 Counter。新增反例：原始重复 row_id 也必须失败关闭；组内内容不得改写原始行（至少规范摘要/模型级相等），不能仅对上 row_id。
5. 修复 Worker 01 测试文件本身的 B905，最终对两个源文件和测试文件 Ruff clean、strict mypy clean；重跑 Task 4.1+4.4 精确套件与全单元回归。

先让新增反例 RED，再修到 GREEN。不要进入浏览器层，不要修改 Task 4.3 文件，不要提交。最终报告给出新增精确 node、RED 原因、GREEN 计数、文件边界和仍未覆盖的真实数据绑定边界。

## Output

Runner-managed output path: `runs/execution/ci_phase4_task44_execution/worker_02_followup.md`. Never invoke a write/edit tool on this report path. 返回完整修复报告，由 runner 持久化。
