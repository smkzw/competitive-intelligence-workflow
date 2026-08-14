REVISE

P0

- `[analysis.py:595](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/analysis.py:595)` `_minimum_binding_matches` 未校验 `source_role`。`PROTOCOL_SAP` 事实可满足疗效或安全性最低记录；实测两种组合均 `result_bearing=True, blocked=False`。  
  最小修复：最低记录增加允许来源角色校验。补测 `PROTOCOL_SAP` 疗效/安全性分别应阻断。

- `[models.py:616](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/gates/models.py:616)` `numeric_value`、`denominator` 使用非严格 Pydantic 类型。`numeric_value=False, denominator=True` 被归一化为 `0/1`，最终 `result_bearing=True, blocked=False`。  
  最小修复：严格拒绝布尔值及非真实数值。补测布尔疗效值、布尔分母必须构造失败。

- `[analysis.py:635](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/analysis.py:635)` 只检查安全 `unit_id`，未检查测量单位。`unit_id=a_safety_event_teae, unit="teae"` 可完整放行；应阻断。  
  最小修复：测量单位使用封闭测量单位规则，拒绝 `teae/sae` 事件类别文本。补测 `%` 保留且通过、`unit="teae"` 阻断。

- `[analysis.py:797](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/analysis.py:797)` 单项目入口只校验 snapshot 闭合，未校验 `project.project_id ∈ snapshot.product_ids`。  
  复现：`evaluate_maturity_gate(_complete_project(project_id="not-in-snapshot"), _snapshot(), ())` 返回 `all_projects, blocked=False`。  
  最小修复：单项目评估开始时强制项目 ID 属于闭合产品集合。补测不匹配项目必须 `GateEvaluationError`。

P1

- `[analysis.py:543](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/analysis.py:543)` `_anchor_evidence_versions` 只接受产品级或试验级 `object_id`，会拒绝合法终点级绑定。  
  复现：同一产品、同一试验的 `object_id=endpoint_id, endpoint_id=endpoint_id`，锚定事实 ID 指向该绑定时抛出 `GateEvaluationError`。  
  最小修复：按已闭合作用域允许同试验的终点/时间点/组别绑定进入锚定证据索引。补测终点级绑定可通过，跨产品终点级绑定仍失败关闭。

- `[evaluator.py:147](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/gates/evaluator.py:147)` 与 A 评估入口未校验 `NOT_APPLICABLE` 谓词是否在 snapshot 声明。接受的监管不适用事实只要填入任意 `applicability_predicate_id`，即可推导为暂停/终止项目并放行开发者/原研方不适用。  
  复现：`invented-rule` + 开发者/原研方均 NA 返回 `blocked=False`。  
  最小修复：不适用绑定必须匹配 snapshot 的条件谓词，并核对对应监管事件类型。补测未知谓词、事件类型不匹配均失败关闭。

P2

- `[analysis.py:496](/Users/smkzw/Documents/AI%20Products/competitive-intelligence-workflow/src/ci_workflow/reports/a/analysis.py:496)` 核心/锚定试验作用域只在对应成熟度层激活时校验。临床前项目携带外部产品核心试验或锚定试验时，当前可返回 `blocked=False, level=all_projects`。  
  最小修复：单项目评估前 eagerly 校验所有已提供的核心/锚定记录。补测低成熟度项目携带未知或跨产品试验必须失败关闭。

通过的反例清单

- A 测试专项全量：`84 passed`。
- 手工填写 `development_maturity/result_bearing/basis` 被拒绝。
- Results posted 无匹配 accepted registry binding、未知试验、跨产品试验均失败关闭；匹配的试验级绑定可触发结果层。
- 无数值、无分母、候选事实、计划/目标/方案假设、错误事实域、非锚定试验事实均不能满足最低记录。
- `0` 作为真实报告数值可通过；`0/-1` 分母构造失败。
- 试验级绑定不会被产品筛选器误删；跨产品产品级绑定失败关闭。
- 比较试验缺对照组阻断，单臂试验缺对照组可通过。
- TEAE/SAE 封闭 `unit_id`、AESI/任意 unit ID 均按预期处理；但反向把 `teae` 放进 `unit` 的漏洞未覆盖。
- 重复项目、空项目集、项目集与 snapshot 不匹配、空 snapshot 均失败关闭；40 项目全量保留，无 Top-N。
- 监管地域和日期不能跨事件拼接；不适用字段的现有正反例通过。
- 生成阻断说明为中文，未出现“门槛、竞品宇宙、基础层、blocked、missing、result_bearing”等词，并明确缺什么及“补齐上述信息后可继续生成”。

仍需主代理确认的边界

- `aliases=()` 当前可构造且身份字段自动满足；需确认“无别名”是否允许作为真实状态，还是必须显式记录未找到/不适用。
- `determine_maturity_level()` 可被外部直接传入成熟度和布尔值，但正式 `evaluate_maturity_gate()` 没有这些输入；需确认是否应将该辅助函数收窄为内部接口。
- `BlockingExplanation` 公共模型只要求含中文，调用方手工构造仍可混入后端词；当前生成路径本身已通过中文文案检查。

