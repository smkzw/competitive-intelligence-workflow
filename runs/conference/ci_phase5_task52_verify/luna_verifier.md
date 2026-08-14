Verdict: REVISE

只读审查完成，未修改仓库或报告路径。

P0

- 证据血统未绑定当前快照。`ClinicalTrialRegionRecord`、`RegulatoryEventVersionRecord`、AV06/AV07/AV08 全部记录仅校验 `fact_version_id` 和 `source_location` 非空；各 `_assert_*_records_closed` 未验证版本属于当前 `evidence_snapshot_id`。  
  精确位置：[pages.py:870-899](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/pages.py:870)、[pages.py:1206-1243](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/pages.py:1206)、[pages.py:1568-1632](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/pages.py:1568)、[pages.py:2012-2110](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/pages.py:2012)、[pages.py:2374-2412](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/pages.py:2374)。  
  反例结果：伪造版本/定位在 AV04–AV08 均 `ACCEPTED`；同一临床记录在变更后的 `evidence_snapshot_id=snap-ev-other` 下仍被接受。  
  最小修复：所有扩展记录改为引用带快照 ID、对象作用域、审查状态和精确定位的强类型证据引用；builder 必须校验当前快照证据索引。

- builder 只校验分析结果的产品 ID 顺序，未验证分析结果确实由当前合同和快照生成。`model_copy(update=...)` 可伪造全部产品为“已有临床结果公开/上市”，随后产品总览正常输出。  
  精确位置：[pages.py:127-150](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/pages.py:127)、[pages.py:730-783](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/pages.py:730)、[analysis.py:276-294](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/analysis.py:276)。  
  最小修复：分析结果携带快照摘要/版本并在 builder 重验；或 builder 重新消费 Task 5.1 的强证据输入，禁止接受仅按 ID 对齐的手工 `UniverseAnalysisResult`。

P1

- AV03 产品档案不完整。`ProductDossier` 未包含临床地域/阶段明细、关键疗效/安全结果与风险、组织关系、交易/公开条款、专利保护及历史状态；`build_product_dossier_view` 也没有扩展记录输入。  
  精确位置：[pages.py:549-664](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/pages.py:549)、[pages.py:786-864](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/pages.py:786)。  
  最小修复：档案 builder 接收并组合 AV04–AV08 的同快照强类型投影，补齐设计书要求的完整详情责任。

- AV04 非核心试验角色没有独立科学来源约束。只要试验属于快照，未出现在产品核心试验合同中的试验即可携带任意核心角色和非空伪造定位。  
  精确位置：[pages.py:1001-1039](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/pages.py:1001)。  
  最小修复：非核心试验角色必须绑定当前快照中已接受的科学来源和明确角色证据。

- AV05 监管事件的一一对应可被重复合同事件绕过。`Counter` 只比较事件类型、地域和日期；同一合同事件重复两次、版本和来源不同，仍可通过。  
  精确位置：[pages.py:1191-1235](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/pages.py:1191)。  
  最小修复：为合同事件引入不可变 `event_id`，版本记录按 `event_id` 精确一一对应，并拒绝重复合同事件。

- AV08 历史状态未与 Task 5.1 监管/开发状态闭合。对当前仍为临床状态、且合同没有撤回事件的产品，伪造“撤回”历史记录仍被接受。  
  精确位置：[pages.py:2235-2262](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/pages.py:2235)、[pages.py:2374-2435](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/pages.py:2374)。  
  最小修复：历史状态必须引用同快照对应监管事件或已接受历史状态证据，并校验地域、日期、状态映射一致。

- 用户可见事实字段未限制为中文临床/竞争情报标签。`_display_label` 对确定值原样透传；`prompt`、`log`、`backend_enum` 等文本可进入产品总览。  
  精确位置：[pages.py:99-115](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/pages.py:99)、[pages.py:762-783](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/pages.py:762)。  
  最小修复：使用受控中文标签类型/映射，并增加 prompt、log、后端枚举泄露测试。

- 权威 model/builder 边界可绕过。直接构造 `ClinicalPortfolioView` 可省略全部试验行；`ProductOverviewView.model_copy(update={"products": ()})` 可生成空视图；`AProjectContract.model_copy(update=...)` 注入伪造锚定版本后，产品档案 builder 仍接受。`__init__.py` 还公开导出了这些模型。  
  精确位置：[pages.py:951-968](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/pages.py:951)、[pages.py:400-420](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/pages.py:400)、[__init__.py:53-119](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/__init__.py:53)。  
  最小修复：将页面模型视为非权威 DTO；入口统一重新验证序列化内容并执行快照闭合/证据校验，避免直接接受可被 `model_copy` 篡改的模型实例。

P2

- 暂未发现独立 P2 问题。

验证命令与结果：

- `uv run pytest tests/unit/reports/a -q`：90 passed
- `uv run pytest tests/reports/a -q`：91 passed
- AV01–AV08 精确节点：8 passed，82 deselected
- 自建反例：产品缺失/多余/重复/重排均拒绝；临床前空组合保留；但伪造证据、重复监管事件、状态矛盾、直接构造和 `model_copy(update=...)` 均被接受。

因此现有测试通过不能支持 PASS；至少 P0/P1 问题修复并补充反例测试后才能重新验收。