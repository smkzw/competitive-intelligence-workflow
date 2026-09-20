两个授权文件已创建并通过全部授权检查；git 状态确认 `__init__.py`/`guards.py`/`transitions.py`/`new_report.py` 的修改均为本会话开始前已存在的未提交变更（见会话初始 gitStatus 快照），本会话未改动任何既有文件。

# Execution Output: ci-phase9-task92-incremental-refresh - worker_01

## Boundary And Context Check

- 初始读取集：`context/ci-phase9-task92-incremental-refresh_execution_context.md`、`plans/codex_execution_ci-phase9-task92-incremental-refresh.md`。按授权仅实现工作项 1 的两个新文件：`src/ci_workflow/graph/impact.py`、`src/ci_workflow/graph/definitions/refresh.py`。
- 追加读取的源码/文档（均在上下文声明的真源内）：Task 9.2 `prd.md`/`design.md`/`implement.md`；`docs/specs/competitive-intelligence-workflow-design-v1.2.md` §17.2；`graph/{types,state,definitions/new_report,definitions/correction,definitions/__init__}.py`；`gates/{coverage,models}.py`（GateSpec/GateOverride/结果键）；`domain/{contracts,ids,evidence}.py`；两个回归测试文件清单；`correction_service.py`（服务消费模式）；`pyproject.toml`（ruff line-length 100 / mypy strict / py312）。
- 零共享文件修改：`refresh.py` 未注册进 `definitions/__init__.py`（它自带失败关闭的 `refresh_node_contract()` 查询，服务可直接 `from ci_workflow.graph.definitions.refresh import ...`），因此本次会话只新增两个文件，无最小差异之外的动作。git status 中 `graph/__init__.py`、`guards.py`、`transitions.py`、`new_report.py` 的修改与 `correction.py`/`visual_finalization.py` 的未跟踪状态均为会话开始前已存在（对照会话初始 gitStatus 快照核实）。

## Work Performed

**`src/ci_workflow/graph/impact.py`（新建，确定性影响传播图）**
- 封闭层词表 `ImpactLayer`：source → fact → claim → page → format，变化只能沿声明顺序向前传播；节点 `ImpactNode`（层 + 稳定对象标识，仅页面层可声明所属报告类型集合，词表复用 `graph.state.REPORT_KINDS`，不复制）；边 `ImpactEdge(upstream, downstream)` 强制层序严格向前。
- `ImpactGraph`：不可变图，构造期失败关闭（对象标识跨层重复、边端点未登记、重复边/节点规范化去重并排序）。
- `impact_closure(seeds)`：由变化种子做确定性反向依赖闭包；种子未登记、种子为空均失败关闭；输出 `ImpactPlan` = 排序稳定、去重的影响集合（含种子及其全部下游）+ 复用集合（其余登记对象）。调用方只能声明种子，无法扩大或缩小结果集合。
- `impact_for_report_kinds(report_kinds)`：门槛收紧的报告级影响入口——受影响报告的页面进入同一闭包，下游格式随之受影响；声明集合为空、超出封闭词表、或声明的报告类型在图中没有页面时失败关闭（不允许静默缩小影响范围）。报告回覆盖/科学质控，事实与声明内容未变化按摘要复用。
- `ImpactPlan.plan_digest` 绑定图内容摘要（`graph_digest`）、种子、影响与复用集合，可直接作为刷新计划/重建动作的稳定幂等键（对应设计“刷新计划和每个重建动作使用稳定幂等键”）。
- 未复制任何 GateSpec 规则：模块不 import `gates.*`，docstring 明确受影响报告集合的唯一真源是 `gates.coverage` 的确定性计算。

**`src/ci_workflow/graph/definitions/refresh.py`（新建，刷新节点合同与再基线分支）**
- 分支合同：`RefreshBaselineIdentity`（contract_schema_version / ontology_version / evidence_contract_version 三维基线身份；GateSpec 单元级收紧明确不属于基线身份，由 `gates.coverage` 在局部刷新分支内处理）+ `classify_refresh_branch(parent, child)` → `RefreshBranchDecision(branch, changed_dimensions, reason_zh)`。任一维度变化即 `rebaseline_required`，理由常量 `REBASELINE_REQUIRED_MESSAGE_ZH = "重大合同变化：需要重新建立基线，不能局部刷新"`，不产出局部刷新计划。
- `REFRESH_NODES`：与 design.md 枚举一一对应的 7 个完整 `NodeContract`（读取父版本 `refresh_parent`、筛选新适格候选 `refresh_candidates`、重评事实/声明 `refresh_reevaluate`、重算受影响门槛 `refresh_gate`、局部重建 `refresh_rebuild`、质控 `refresh_qc`、建立新版本 `refresh_accept_version`），声明类型化输入/输出（输出均在 `validate_typed_outputs` 封闭词表内）、完成谓词、读写集、重试策略、声明错误（含 `RebaselineRequiredError`、`GateDeclarationError`、`GateBlockedError`、`IncompleteRebuildError`）、幂等材料（project/run/node/input_digest）与副作用类。
- 两个批准节点：`refresh_qc`（独立质控只能接受或否决）与 `refresh_accept_version`（`side_effect_class="move"`，建立并接受新的不可变版本；质控或重建未完成不得登记）。
- 导入期失败关闭：节点标识去重校验、与 `NEW_REPORT_NODES` 标识冲突校验；`refresh_node_contract()` 未知节点失败关闭。

## Artifacts And Evidence

| 文件 | 状态 | 说明 |
|---|---|---|
| `src/ci_workflow/graph/impact.py` | 新建（本会话唯一改动之一） | 稳定影响闭包、复用集合、计划摘要幂等键、报告级影响入口 |
| `src/ci_workflow/graph/definitions/refresh.py` | 新建（本会话唯一改动之一） | 7 个刷新节点合同、两个批准节点、重大合同变化再基线分支 |

证据锚点：ruff 与 mypy(strict) 对两文件零告警；37 个授权回归测试全部通过；冒烟脚本验证闭包/复用/摘要幂等/失败关闭/分支裁定/节点合同行为（详见下节）。

## Commands And Observations

- `uv run ruff check src/ci_workflow/graph/impact.py src/ci_workflow/graph/definitions/refresh.py` → 首次报 1 处 E501（refresh.py:222 中文描述超 100 列），改为多行 `_field(...)` 后 `All checks passed!`。
- `uv run mypy src/ci_workflow/graph/impact.py src/ci_workflow/graph/definitions/refresh.py`（strict）→ `Success: no issues found in 2 source files`。
- `uv run python -c "..."` 冒烟验证（观察，非测试文件）：来源种子闭包正确落到 fact/claim/page/format 四层且 `fact_2`/B 页留在复用集合；同输入 `plan_digest` 稳定、重复种子去重；`impact_for_report_kinds(['A'])` 使 A 页与站点格式受影响而 claim/fact 复用；未登记种子、空报告集合、未知报告类型 `D`、无页面报告 `C` 四条路径均失败关闭；基线一致 → `local_refresh`，本体变化 → `rebaseline_required` 且理由与中文常量一致；7 个节点标识与 design.md 枚举一致。首次冒烟报 `AssertionError: 应失败关闭`，定位为**测试脚本自身缺陷**（`lambda: X if False else None` 的条件表达式优先级使元组末项成为恒返回 None 的 lambda 而非应跳过的 None），修正脚本后全部通过——模块行为无缺陷。
- `uv run python -c "import ci_workflow.graph; ..."` → 包导入正常，无循环依赖（impact.py 仅依赖 `domain.ids` + `graph.state`；refresh.py 仅依赖 `graph.types` + `definitions.new_report`）。
- `uv run pytest tests/integration/test_historical_cutoff.py tests/reports/test_gate_override_strictness.py -q`（implement.md 授权的回归项）→ `37 passed in 0.48s`。

## Blockers Or Missing Environment

- 无阻塞。环境（uv、pytest、ruff、mypy）齐备，未安装任何包。
- 需 Codex 知悉的一个解释性判断（非阻塞）：implement.md/worker_03 条目中的“两个批准节点”，我按 Task 9.1 发布守卫（新快照 + 受影响产物重建 + 独立质控）与 §17.2“每次接受的刷新”模式，落实为 `refresh_qc` 与 `refresh_accept_version` 两个批准语义节点，已在模块 docstring 中声明。若 Codex 对“批准节点”另有所指（例如需要用户显式批准状态），worker_02/03 集成前请裁定。

## Rerun Requests Or Next Step

- 建议下一步：worker_02 实现 `application/refresh_service.py` 时直接消费 `impact_closure`/`impact_for_report_kinds`（受影响报告集合必须来自 `gates.coverage.compute_affected_report_kinds`，禁止自行推导）与 `classify_refresh_branch`（`rebaseline_required` 分支返回中文理由并拒绝生成局部刷新计划）；重建回执可用 `plan_digest` 作为计划幂等键材料。
- worker_03 编写 `tests/integration/test_incremental_refresh.py` 时，影响范围断言可用 `ImpactPlan.affected_ids/reused_ids`；本模块冒烟场景（闭包四层、复用集合、摘要幂等、四条失败关闭路径、再基线分支）可作为用例蓝本。
- 剩余验证（非本工人职责）：worker_03 的集成测试 GREEN、Ruff/mypy 全量目标运行、以及 Codex 对影响范围边界与再基线分支语义的最终审查。
